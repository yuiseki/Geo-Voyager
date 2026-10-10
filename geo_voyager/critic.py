import re
import json

from .critique import Critique
from .intent import Intent
from .llama_client import LlamaClient
from .observation import Observation
from .target_identity import identity_conflict, resolve_target


THINKING_MAX_TOKENS = 4096
# Only a step whose Intent asks for a comparison, a selection or a total is told to want that answer itself. Told
# to every step, the model also failed a step that only listed things (the wards touching Taito).
ASKS_FOR_AN_ANSWER = re.compile(r'比較|どちら|多い|少ない|最大|最小|最も|上位|合計|選ぶ|特定')
THINKING_BUDGET_TOKENS = 1024


class Critic:
    def __init__(self, llm_client: LlamaClient | None = None, *, thinking: bool = False) -> None:
        self.llm_client = llm_client if llm_client is not None else LlamaClient()
        self.thinking = thinking

    def check(self, intent: Intent, observations: list[Observation], *, final: bool = False) -> Critique:
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
        observation_text = '\n'.join(f'- {observation.text}' for observation in observations)
        prompt = (
            'Observation が Intent の要求した調査結果を実際に答えているか判定してください。\n'
            '仮説が正しいか、結果が望ましいかは判定しない。\n'
            '入力の Intent と Observation だけで要求した出力が得られたか判定する。外部知識で答えを推測・追加しない。Intent にない期待件数を仮定しない。\n'
            'データを取得したという報告だけでは、要求された調査結果を答えたことにはなりません。\n'
            '回答の値が 0 や空のとき、または値同士が矛盾するとき（例: 距離が数メートルなのに所要時間が99分）は、その値が正しいと分かる根拠が Observation に'
            'あるときだけ成功にする。数値が書かれているだけでは成功にしない。根拠が無ければ、取得方法の誤りを疑って失敗とする。\n'
            '要求された具体的な回答があれば成功、回答が不足していれば失敗としてください。\n'
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
                        + '\n'.join(f'previous_observations[{index}]: {obs.text}' for index, obs in enumerate(intent.previous_observations))
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
        elif ASKS_FOR_AN_ANSWER.search(intent.text):
            prompt += ('\nIntent が比較・選択・集計（比較の勝者、最大・最小、一覧からの選択、合計など）を求めるときは、その答えそのものが'
                       'Observation に値として出力されていなければならない。Observation の数値から自分で比較・計算して答えを導かない。'
                       '材料の数値だけで答えが出力されていなければ失敗とする。')
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
