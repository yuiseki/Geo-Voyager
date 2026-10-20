import re
import json

from .background_facts import facts_section

from .critique import Critique
from .dataset_references import REFERENCED, critic_text
from .datasets import load_dataset_graph
from .intent import Intent
from .llama_client import LlamaClient
from .observation import Observation
from .services import load_service_graph
from .skill_candidate import called_service_ids, read_datasets
from .target_identity import identity_conflict, resolve_target


THINKING_MAX_TOKENS = 4096
# Only a step whose Intent asks for a comparison, a selection or a total is told to want that answer itself. Told
# to every step, the model also failed a step that only listed things (the wards touching Taito).
ASKS_FOR_AN_ANSWER = re.compile(r'比較|どちら|多い|少ない|最大|最小|最も|上位|合計|選ぶ|特定')
THINKING_BUDGET_TOKENS = 1024
# The earlier Observations are reference for the identity of a target, not the answer. Shown whole, two lists of
# 8 KB beside an 8 KB answer were more than the model's 8,192-token context, and the server refused the prompt.
REFERENCE_BUDGET = 4096
# The Observations judged, shared the same way. A result reaches the next step whole (up to 1 MiB); the Critic
# reads the code that made it beside the part shown, and how long it was.
OBSERVED_BUDGET = 6144
# The model's knowledge of single places was wrong each time it failed a step on it (港区 and 目黒区 do not touch;
# 大田区 and 江戸川区 touch at sea in OSM), and its sense of scale was right (no station in the 23 wards is wrong).
PLACE_FACTS = ('個々の地物についての事実（どの区とどの区が接するか、ある名前が一覧に入るべきか）を、自分の知識で否定・補完して失敗の理由にしない。'
               'データの定義（陸か海を含むか、どの版か）で答えが変わるため。値が 0 や空のこと、件数の桁が明らかに合わないことは疑ってよい。\n')
CODE_HEADER = ('\n\nこの Observation を出力したコード（どう測ったかの根拠として読む。'
               'コードが Intent の対象の一部だけを測っている、または Intent と違う条件で測っているなら失敗。'
               'コードが Intent どおりに測っているなら、値の正しさを自分の知識で否定しない）:\n')
# Goal 5, step 4: an Intent read the columns rep_lon and rep_lat to output lon and lat, and carried each ward's
# relation_id from the step before; the Critic rejected the right points for both and the Goal lost two steps each run.
# Either sentence alone left the other reason standing (docs/reports/2026-10-14_critic_stage5.md).
READ_NAMES = ('Intent には、読む元のデータの列の名前（例: pop_2020）と、出力のキー名（例: population）の両方が出てくることがある。'
              '読む元の列の名前が出力のキーに無いことを、失敗の理由にしない。\n')
CARRIED = ('コードが入力（results や前段の Observation）から引き継いだ名前や ID は、前段で得た値である。'
           '今回読んだデータやサービスがその種類の ID を持たないことを、失敗の理由にしない。\n')
# Explore 25: of 品川区 and 江戸川区, only 江戸川区 had a boat rental, and the Critic failed the output for leaving
# 品川区 out. Replayed on the 73 failed verdicts of explores 16 to 26, this turned that one to a success and no output
# that was wrong.
NONE_MATCHED = ('Intent が複数の対象（区など）を調べ、条件（〜以内、〜を持つものだけ、など）で絞り込むとき、'
                '条件に合うものが無かった対象が出力に無いことを、それだけで失敗の理由にしない。'
                'コードがその対象も調べていれば、その対象は 0 件だったと読む。\n')
# Explore 33: the code flipped the coordinates for ST_Distance_Sphere, as contracts.tables.MEASURING tells the
# Generator to, and the Critic failed it three times for flipping them; replayed, one of the three turned to a success.
AXIS_ORDER = ('この DuckDB の ST_Distance_Sphere と *_Spheroid は緯度、経度の順の点を読む。経度、緯度の geometry や '
              'ST_Point(lon, lat) を ST_FlipCoordinates で入れ替えてから渡すのは正しい測り方で、座標の反転を失敗の理由にしない。\n')
RESOURCES_HEADER = '\n\nコードが読んだサービスとデータの説明（コードが Intent の対象を正しく選んだかを照合するために読む）:\n'


def _resources(code: str, intent: Intent) -> str:
    """What the services and datasets the code reads are, as the Planner and the Generator are told."""
    services, datasets = load_service_graph(), load_dataset_graph()
    known = {dataset.id for dataset in datasets.all()}
    passed = intent.dataset_ids[0] if len(intent.dataset_ids) == 1 else None
    lines = [f'{service_id}: {services.get(service_id).description}' for service_id in sorted(called_service_ids(code))
             if service_id in {service.id for service in services.all()}]
    lines += [f'{dataset_id}: {datasets.get(dataset_id).description}' + (f' {critic_text(dataset_id, code)}' if dataset_id in REFERENCED else '')
              for dataset_id in sorted(read_datasets(code, passed) or ()) if dataset_id in known]
    return '\n'.join(lines)


def _references(observations: tuple[Observation, ...], budget: int = REFERENCE_BUDGET) -> list[str]:
    """Each earlier Observation's text within a shared budget of bytes: the short ones whole, the rest cut to an
    equal share of what is left, with how long they were."""
    sizes = [len(observation.text.encode('utf-8')) for observation in observations]
    shares, left = {}, budget
    for count, index in enumerate(sorted(range(len(sizes)), key=sizes.__getitem__)):
        shares[index] = min(sizes[index], left // (len(sizes) - count))
        left -= shares[index]
    return [observation.text if shares[index] == sizes[index] else
            observation.text.encode('utf-8')[:shares[index]].decode('utf-8', errors='ignore')
            + f'…（以下略、全 {sizes[index]} バイト{_rows(observation.text)}）'
            for index, observation in enumerate(observations)]


def _rows(text: str) -> str:
    try:
        value = json.loads(text)
    except ValueError:
        return ''
    return f'、{len(value)} 行' if isinstance(value, list) else ''


class Critic:
    def __init__(self, llm_client: LlamaClient | None = None, *, thinking: bool = False) -> None:
        self.llm_client = llm_client if llm_client is not None else LlamaClient()
        self.thinking = thinking

    def check(self, intent: Intent, observations: list[Observation], *, final: bool = False,
              asked: tuple[str, ...] = (), code: str | None = None) -> Critique:
        """Judge whether the observations answer the Intent.

        asked, for the final check, is the Intent text of the step that produced each Observation. A step that
        picked the smallest from a list prints only the one it picked; without the step beside it, that output is a
        bare record and the model can not tell it is the answer.

        code, for a step, is the code that printed the observations. The model reads how the value was measured
        (the first of 23 wards only; a query of the 23 wards) instead of judging the value by what it knows.
        """
        if asked and len(asked) != len(observations):
            raise ValueError('asked must name the step of each Observation')
        if not observations:
            return Critique(success=False, reason='Observation がありません')
        if all(not observation.text.strip() for observation in observations):
            return Critique(success=False, reason='Observation の本文がすべて空です')
        if intent.target is not None:
            # A name that matches is not enough. If the observations carry an id of the target's type and it is
            # not the target's id, they are about another target, and no model has to be asked.
            conflict = identity_conflict(intent.target, tuple(observations))
            if conflict:
                return Critique(success=False, reason=conflict)
        shown = _references(tuple(observations), OBSERVED_BUDGET)
        if asked:
            observation_text = '\n'.join(f'- 調査項目: {step}\n  出力: {text}' for step, text in zip(asked, shown))
        else:
            observation_text = '\n'.join(f'- {text}' for text in shown)
        prompt = (
            'Observation が Intent の要求した調査結果を実際に答えているか判定してください。\n'
            '仮説が正しいか、結果が望ましいかは判定しない。\n'
            '入力の Intent と Observation だけで要求した出力が得られたか判定する。外部知識で答えを推測・追加しない。Intent にない期待件数を仮定しない。\n'
            + PLACE_FACTS
            # explore 41: told nothing, the Critic failed 双葉町's census population 0 as unrealistic
            + facts_section(intent.text + '\n' + observation_text) +
            'データを取得したという報告だけでは、要求された調査結果を答えたことにはなりません。\n'
            '回答の値が 0 や空のとき、または値同士が矛盾するとき（例: 距離が数メートルなのに所要時間が99分）は、その値が正しいと分かる根拠が Observation に'
            'あるときだけ成功にする。数値が書かれているだけでは成功にしない。根拠が無ければ、取得方法の誤りを疑って失敗とする。\n'
            '要求された具体的な回答があれば成功、回答が不足していれば失敗としてください。\n'
            'Intent が出力のキー名を指定していても（例: cafe_count）、その値が別の意味の分かるキー（例: tag が amenity=cafe の count）で出力されていれば、'
            'キー名の違いは失敗の理由にしない。キー名ではなく、値と対象と条件が Intent の要求に合うかで判定する。'
            '実行環境の関数は、件数を count、条件を tag のような決まったキーで出力する。値そのものが無い、または別の値なら失敗。\n'
            + READ_NAMES + CARRIED + NONE_MATCHED + AXIS_ORDER +
            '返答は次の2行だけにし、前置き・コードフェンスを付けないでください。\n'
            '判定: 成功\n理由: 理由の本文\n'
            '失敗の場合は1行目を「判定: 失敗」にしてください。理由も1行にしてください。\n\n'
            f'Intent:\n{intent.text}\n\nObservation:\n{observation_text}'
        )
        if intent.target is not None:
            if intent.target.resolved:
                prompt += (f'\nIntent の対象: {intent.target.display()}。対象は ID で照合する。Observation の ID がこの対象の ID と一致するかを見る。'
                           '名前は表示であり、前段や Observation の名前と違っていてもよい。')
            else:
                prompt += f'\nIntent の対象: {intent.target.name}。Observation の対象の名前とIDがこの対象のものか照合してください。'
        if intent.previous_observations:
            prompt += ('\n前段 Observation（対象の identity を照合するためのデータ）:\n'
                        + '\n'.join(f'previous_observations[{index}]: {text}' for index, text in enumerate(_references(intent.previous_observations)))
                       + '\n対象は名前と安定IDで照合します。回答の名前・IDが Intent の対象と一致するかを先に照合してください。別の対象なら件数があっても失敗です。')
            if intent.target is not None:
                target = resolve_target(intent.target, intent.previous_observations)
                if target is not None:
                    matched = 'ID が一致した' if intent.target.resolved else 'name が一致した'
                    prompt += ('\n解決済み参照対象: ' + json.dumps(target.to_dict(), ensure_ascii=False)
                               + f'\nこれは前段で{matched}対象です。前段を探し直さず、この対象と回答を照合してください。')
                else:
                    how = 'ID' if intent.target.resolved else '名前'
                    prompt += (f'\n対象「{intent.target.display()}」は前段の Observation から{how}で一意に特定できません。'
                               '回答の対象が Intent の対象と一致するかを慎重に照合してください。')
            prompt += ('\n前段に正しい値があっても今回の回答が誤りなら失敗。'
                       '前段は参照資料であり今回の回答ではありません。今回の Observation が要求を答えているかだけを判定する。')
        if final:
            prompt += ('\nこれは Goal 全体の最終判定。Goal が求める答え（比較の勝者、最大・最小、一覧からの選択、合計など）は、'
                       'Observation のどれかに値として実際に出力されていなければならない。複数の Observation の数値から自分で比較・計算して答えを導かない。'
                       '答えの材料だけが別々の Observation にあり、答えそのものを出力した Observation が無いときは失敗とし、'
                       '理由に、どの材料からどんな答えを出す作業が足りないかを書く。')
            if asked:
                prompt += ('\n各 Observation には、それを出力した調査項目を添えた。調査項目が一覧からの選択、最大・最小、比較、合計を'
                           '求めているとき、その出力はその調べ物の答えとして読む（例: 最小の区を1件選ぶ調査項目の出力は、最小の区そのもの）。')
        elif ASKS_FOR_AN_ANSWER.search(intent.text):
            prompt += ('\nIntent が比較・選択・集計（比較の勝者、最大・最小、一覧からの選択、合計など）を求めるときは、その答えそのものが'
                       'Observation に値として出力されていなければならない。Observation の数値から自分で比較・計算して答えを導かない。'
                       '材料の数値だけで答えが出力されていなければ失敗とする。')
        if code is not None:
            prompt += CODE_HEADER + code
            resources = _resources(code, intent)
            if resources:
                prompt += RESOURCES_HEADER + resources
        system_prompt = None
        if intent.previous_observations:
            system_prompt = ('Judge only the current returned Observation. Previous observations are reference evidence, '
                                       'not the current answer. A correct answer present only in reference data does not make '
                                       'the current execution successful. If the returned target/value is incorrect, return 失敗. '
                                       'Return exactly 判定: 成功 or 判定: 失敗, then 理由: on the second line.')
        options = {}
        if self.thinking:
            options = dict(enable_thinking=True, max_tokens=THINKING_MAX_TOKENS,
                           reasoning_budget_tokens=THINKING_BUDGET_TOKENS)
        return Critique.from_text(self.llm_client.generate(
            prompt, temperature=0.0, system_prompt=system_prompt, **options))
