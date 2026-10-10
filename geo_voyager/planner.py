import re
from dataclasses import dataclass

from .dataset_graph import DatasetGraph
from .goal_history import GoalHistory, render_history
from .intent_text import api_details_in
from .hypothesis import Hypothesis
from .intent import Intent
from .llama_client import LlamaClient
from .observation import Observation
from .question import Question
from .verdict import Verdict
from .services import load_service_graph
from .target_identity import resolve_reference
from .target_ref import TargetRef
from .datasets import load_dataset_graph


TARGET_PREFIXES = ('対象:', '対象：')


class PlannerRejected(ValueError):
    """The model's reply to Planner.next could not be used. It carries the reason and the reply itself."""

    def __init__(self, reason: str, reply: str) -> None:
        super().__init__(reason)
        self.reason, self.reply = reason, reply


@dataclass(frozen=True, repr=False)
class Done:
    """What Planner.next returns when the history already answers the Goal."""

    def __repr__(self) -> str:
        return 'DONE'


DONE = Done()

SHARED_RULES = (
            '後続では previous_observations（前段 stdout の文字列一覧）を参照できる。\n'
            '既に取得した一覧やタグを再検索せず使う。途中の出力は JSON にすると参照しやすい。\n'
            '既存 Graph に対象型が登録されている場合、対象集合・名称・外部IDの取得にはその Graph の Service を選ぶ。\n'
            '単一の広域の地名検索結果を区域一覧の代わりにしない。対象集合の取得と地物検索を区別する。\n'
            '指定件数の対象一覧は一意な外部ID、件数、名称の言語を調査項目に明記する。多言語名称で対象を重複させない。\n'
            '有限個の対象を比較するとき、対象一覧の取得、任意対象1件の測定、全対象の測定、最大選択を分ける。\n'
            'まず1対象で方法を確立する。\n'
            '対象を測る Intent は、対象の名前で指定する。名前は Goal 文または前段の出力で与えられたものを使い、「対象: 名前」の行に書く。調査項目にも同じ名前を書く。\n'
            '対象の一覧や単一の対象を出力する Intent は、各対象を name と安定ID（relation_id など）を持つ JSON object で出力させる。後続の Intent はこの name と ID で対象を特定する。\n'
            '「対象:」は1つの Intent につき1行だけ書く。対象が複数あるときは Intent を分ける。\n'
            '対象の名前が Goal にも前段にも無い全対象へ同じ測定をするときは、全対象を name と relation_id で識別して測定結果を一覧で返す1つの Intent にする。\n'
            '同じ分析操作で対象だけを変える Intent は、対象の名前以外の文を揃える。最初の測定で確立した Skill を後続で再利用する。\n'
            '各 Intent は登録済み Dataset 0〜1件または Service 1件以上を指定する。前段だけのローカル集計は両方 [] とする。\n'
            '答えを推測しない。サービス固有の実行コードを書かない。前段結果に依存する入力を調査項目に明記。\n'
            '外部アクセスの Intent では両方を [] にしない。前段データだけのローカル集計は両方 [] にしてよい。\n'
)

FORMAT_RULES = (
            '出力は以下の3項目と、対象を測る Intent だけが付ける「対象:」の行。各 Intent を独立行 --- で区切る。前置き、番号、コードフェンス禁止。\n'
            '調査項目: 調査内容\n利用データセット: []\n利用サービス:\n  - 登録済みid\n対象: 名前\n'
            '利用データセットと利用サービスは空なら []、非空なら半角2空白の - id の行を続ける。\n'
)


def _plan_blocks(text: str) -> list[list[str]]:
    """The Intent blocks of a plan, as lists of non-blank lines.

    Blocks are separated by lines that are only ---. A separator at either end is harmless.
    When a separator was left out between two 調査項目 blocks, the block is still split before
    the second 調査項目 line. A 対象 line before that line then stays with the block above it.
    """
    chunks, current = [], []
    for line in (line for line in text.strip().splitlines() if line.strip()):
        if line.strip() == '---':
            if current:
                chunks.append(current)
            current = []
        else:
            current.append(line)
    if current:
        chunks.append(current)
    blocks = []
    for chunk in chunks:
        start = 0
        for index, line in enumerate(chunk):
            if line.startswith('調査項目: ') and any(item.startswith('調査項目: ') for item in chunk[start:index]):
                blocks.append(chunk[start:index])
                start = index
        blocks.append(chunk[start:])
    return blocks


def _extract_target(block: list[str]) -> tuple[list[str], str | None]:
    """The block without its 対象 line, and the target name. The line may be anywhere in the block."""
    names = [line[len(TARGET_PREFIXES[0]):].strip() for line in block if line.startswith(TARGET_PREFIXES)]
    if len(names) > 1:
        raise ValueError('An Intent has more than one 対象 line, but names one target')
    return [line for line in block if not line.startswith(TARGET_PREFIXES)], (names[0] if names else None)


def _parse_intent(block: list[str], datasets, services, *, allow_local: bool, known: tuple[TargetRef, ...] = ()) -> Intent:
    """One Intent from its block of lines. A step that only works on earlier output needs allow_local."""
    lines, reference = _extract_target(block)
    if not lines or not lines[0].startswith('調査項目: '):
        raise ValueError('Plan must start with 調査項目:')
    ids = {'利用データセット': [], '利用サービス': []}
    position = 1
    for label in ids:
        if position >= len(lines) or lines[position] not in (label + ':', label + ': []'):
            raise ValueError('Plan must contain dataset and service lists')
        empty = lines[position].endswith(' []')
        position += 1
        if not empty:
            while position < len(lines) and lines[position].startswith('  - '):
                ids[label].append(lines[position][4:])
                position += 1
    if position != len(lines):
        raise ValueError('Unexpected plan fields')
    local = not ids['利用データセット'] and not ids['利用サービス']
    if local and not allow_local:
        raise ValueError('First step requires an external resource')
    intent = Intent(lines[0][len('調査項目: '):], tuple(ids['利用データセット']), tuple(ids['利用サービス']),
                    requires_context=local,
                    target=resolve_reference(reference, known) if reference is not None else None)
    if len(intent.dataset_ids) > 1:
        raise ValueError('Only one dataset per execution is supported')
    for id in intent.dataset_ids:
        datasets.get(id)
    for id in intent.service_ids:
        services.get(id)
    return intent


# A set of targets, not one: '東京23区', '23区', '全23区', '各区'.
_A_SET = re.compile(r'(?:^|[^0-9])[0-9０-９]+[区市町村]$|^[全各]')


def _not_an_entity(name: str, goal: str) -> bool:
    """A tag ('cuisine=sushi'), the key or value of a tag in the Goal, two targets in one name, or a set of places."""
    if '=' in name or _A_SET.search(name):
        return True
    parts = [part.strip() for part in re.split(r'と|、|,|・', name) if part.strip()]
    if len(parts) > 1 and all(part in goal for part in parts):
        return True                                    # two targets in one line: '渋谷区と新宿区'
    word = re.escape(name)
    return bool(re.search(rf'[A-Za-z_:]+=\s*{word}(?![A-Za-z0-9_])', goal)          # the value of a tag
                or re.search(rf'(?<![A-Za-z0-9_]){word}\s*(?:=|キー)', goal))      # the key of a tag


def _require_an_entity(target: TargetRef | None, goal: str, known: tuple[TargetRef, ...]) -> None:
    """A 対象 line names an entity: one an earlier step identified by id, or one the Goal itself names.

    A name that is neither ('ID 最小の区', '各 23 区', '地点 A') is a description of a target, not a target.
    """
    if target is None or target.resolved:
        return
    name = target.name.split(',')[0].strip()
    if _not_an_entity(name, goal):
        raise ValueError(f'「対象: {target.name}」は 1 つの実体ではない（タグ、タグのキーや値、複数の対象、対象の集合）。'
                         '「対象:」は 1 つの場所や地物の名前だけに付ける。タグの使用数や集合全体の測定には「対象:」を付けない。'
                         '対象が複数あるときは Intent を分ける。')
    if target.name in goal or name in goal:
        return
    options = '; '.join(ref.display() for ref in known if ref.resolved) or 'なし'
    raise ValueError(f'「対象: {target.name}」は Goal にも履歴にもある対象の名前ではない。対象は、Goal が名指しした名前か、'
                     f'履歴で判明した対象（名前または ID）だけを書く。対象を決める調べ物には「対象:」を付けない。判明した対象: {options}')


class Planner:
    def __init__(self, llm_client: LlamaClient | None = None) -> None:
        self.llm_client = llm_client if llm_client is not None else LlamaClient()

    def plan(self, question: Question | str) -> list[Hypothesis] | list[Intent]:
        if isinstance(question, str):
            return self.plan_goal(question)
        prompt = (
            "次の疑問に対して、データを使って検証可能な仮説を1つ提案してください。\n"
            "仮説本文だけを返してください。\n\n"
            f"疑問:\n{question.text}"
        )
        return [Hypothesis(self.llm_client.generate(prompt).strip())]

    def plan_intents(
        self, hypothesis: Hypothesis, dataset_graph: DatasetGraph
    ) -> list[Intent]:
        datasets = dataset_graph.all()
        if not datasets:
            raise ValueError("Dataset Graph must not be empty")
        dataset_text = "\n".join(
            f"- {dataset.id}: {dataset.description}" for dataset in datasets
        )
        prompt = (
            "次の仮説を検証するために必要な調査を、具体的な実行単位に分解してください。\n\n"
            "Intent は、1回の Worker 実行で1つの明確な Observation を得るための最小調査単位です。\n"
            "- 1 Intent = 1 measurable output（1つの測定値・集計値だけを得る）\n"
            "- 必要なら複数 Dataset を使ってよい。ただし1 Intent は1 measurable output\n"
            "- spatial join / zonal aggregation / attribute join などの結合・集計を許可する\n"
            "- 複数の異なる測定値を1 Intent にまとめない\n"
            "- 最終的な相関分析や仮説判定は Intent にしない\n"
            "- 測定する指標が複数なら、指標ごとに別の Intent に分ける\n"
            "- 各 Intent は簡易 YAML にし、利用データセットは1件以上の配列にする\n"
            "- 調査項目は1行の文字列、Dataset の id は半角空白2つと - に続けて書く\n"
            "- Intent 同士は、単独行の --- で区切る\n"
            "- Dataset 配列以外の箇条書き、番号、コードフェンス、前置きは付けない\n"
            "- 調査内容だけを書く\n"
            "- 3〜5件程度\n"
            "- 結論は書かない\n"
            "- 利用可能な Dataset の範囲内で Intent を作る\n"
            "- 登録外のデータセットを仮定しない\n"
            "- 各調査で参照する Dataset の id を明記する\n\n"
            "出力形式の例:\n"
            "調査項目: 23区ごとの推計人口を算出する\n"
            "利用データセット:\n"
            "  - yuiseki/jp-admin-2026-09\n"
            "  - yuiseki/worldpop-jp-2026-01\n\n"
            f"利用可能な Dataset:\n{dataset_text}\n\n"
            f"仮説:\n{hypothesis.text}"
        )
        blocks = self.llm_client.generate(prompt).split("---")
        intents = []
        for block in blocks:
            if not block.strip():
                continue
            intent = Intent.from_block(block)
            for dataset_id in intent.dataset_ids:
                dataset_graph.get(dataset_id)
            intents.append(intent)
        if not intents:
            raise ValueError("LLM returned no intents")
        return intents

    def judge(
        self, hypothesis: Hypothesis, observations: list[Observation]
    ) -> Verdict:
        return Verdict("仮説はまだ十分に検証されていない")

    @staticmethod
    def _resource_text(datasets, services, *, full: bool = False) -> str:
        """The resources as the prompt lists them. The first-plan prompt shows the first two sentences of a service.

        With full the whole description is shown, so the Planner knows what each service can do. It does not need the
        endpoint or the parameters to write an Intent, but a model that sees only a piece of the description makes the
        rest up.
        """
        resources = '\n'.join(f'Dataset {item.id}: {item.description}' for item in datasets.all())
        resources += '\n' + '\n'.join(
            f'Service {item.id}: {item.protocol}: ' + (item.description if full else '。'.join(item.description.split('。')[:2]))
            for item in services.all())
        return resources

    def next(self, goal: str, history: GoalHistory) -> Intent | Done:
        """Decide the next Intent from what has happened so far, or say the Goal is answered.

        One model call, one Intent. The Planner sees the whole history, so a name and a stable id that an
        earlier Observation made known can be used by the next Intent, and a failure can change the plan.
        """
        if not goal.strip():
            raise ValueError('Goal must not be empty')
        datasets, services = load_dataset_graph(), load_service_graph()
        prompt = (
            'Goal を達成するために、次に実行する Intent を1件だけ決めてください。1 Intent = 1 measurable output。\n'
            '履歴は、これまでに実行した Intent と、その Observation、Critic の判定、失敗、判明した対象です。履歴を読んで次の1件を決める。\n'
            'Goal の答えが履歴の成功した Observation で揃っているときは、Intent の代わりに DONE とだけ返す。まだ足りないときに DONE を返さない。\n'
            '履歴で成功した Intent を繰り返さない。失敗した Intent は、同じ内容で繰り返さず、失敗の理由を読んで方法・対象・使うサービスを変える。\n'
            '履歴に「計画の失敗」があるときは、前回のあなたの応答がその理由で使えなかったということ。理由が示す契約を守った Intent を返し、同じ誤りを繰り返さない。'
            '対象が複数あるときは、対象ごとに Intent を分ける。1つの Intent に「対象:」は1行だけ書く。\n'
            '履歴に「Goal の最終判定が未達」があるときは、DONE を返したが Critic が不足を指摘したということ。その理由が示す不足を埋める Intent を返し、同じ DONE を繰り返さない。\n'
            'Service の説明は、そのサービスで何ができるかを知るためのものです。Intent の調査項目には、何を調べるか（調べる対象、条件、得たい値）だけを書く。'
            'API のパス（/api/... など）やパラメータ（limit=3 など）は書かない。サービスの呼び方は実行側が決める。書いた Intent は拒否される。\n'
            '測定の出力のキーは、件数なら count、条件なら tag（例: "amenity=cafe"）のように一般の名前にする。cafe_count のように条件や対象をキー名に入れない。保存済みの関数はこの決まったキーで出力する。\n'
            '「判明した対象」は、前段の Observation で分かった名前と安定IDです。対象は ID で区別する。その対象を測る Intent は、「対象:」に判明した対象の名前、または ID（例: 対象: relation_id=1761717）を書く。同じ名前の対象が複数あるときは ID で書く。調査項目には対象の名前を書く。IDをコードに書き写さなくてよい。\n'
            + SHARED_RULES
            + 'DONE とだけ返すか、次の Intent を以下の形式で1件だけ返す。複数返さない。前置き、番号、コードフェンス禁止。\n'
            + '調査項目: 調査内容\n利用データセット: []\n利用サービス:\n  - 登録済みid\n対象: 名前\n'
            + '利用データセットと利用サービスは空なら []、非空なら半角2空白の - id の行を続ける。「対象:」は対象を測る Intent だけが付ける。\n'
            + f'INPUT: 利用可能リソース:\n{self._resource_text(datasets, services, full=True)}\nGoal:\n{goal}\n履歴:\n{render_history(history)}\n'
            + 'OUTPUT: DONE、または調査項目、利用データセット、利用サービス、必要なら対象の行だけ。INPUT のメタデータを繰り返さない。'
        )
        text = self.llm_client.generate(
            prompt, temperature=0.0, max_tokens=4096, enable_thinking=True, reasoning_budget_tokens=768,
            system_prompt='You are a sequential task planner that decides one step at a time. Reply with exactly DONE when the history answers the Goal, '
                          'otherwise with one Intent in the exact text format. Name a target by its name on a 対象: line. '
                          'Never repeat a step that succeeded, and change the approach after a failure. Never return code.',
        )
        lines = [line for line in text.strip().splitlines() if line.strip()]
        if lines and lines[0].strip() == 'DONE':
            return DONE
        try:
            blocks = _plan_blocks(text)
            if not blocks:
                raise ValueError('Plan must start with 調査項目:')
            intent = _parse_intent(blocks[0], datasets, services, allow_local=bool(history.observations()), known=history.targets())
            _require_an_entity(intent.target, goal, history.targets())
            details = api_details_in(intent.text)
            if details:
                raise ValueError(f'Intent の調査項目に API の詳細が書かれている: {", ".join(details)}。'
                                 '何を調べるかだけを書き、API のパスやパラメータは書かない。サービスの呼び方は実行側が決める')
            return intent
        except (ValueError, KeyError) as problem:
            raise PlannerRejected(f'{type(problem).__name__}: {problem}', text) from problem

    def plan_goal(self, goal: str) -> list[Intent]:
        if not goal.strip():
            raise ValueError('Goal must not be empty')
        datasets, services = load_dataset_graph(), load_service_graph()
        resources = self._resource_text(datasets, services)
        prompt = (
            'Goal を小さい調査 Intent に分解してください。1 Intent = 1 measurable output。\n'
            '依存関係のある順に並べ、取得した情報を後続で使う。巨大なループコードを最初から作らない。\n'
            + SHARED_RULES
            + FORMAT_RULES
            + f'INPUT: 利用可能リソース:\n{resources}\nGoal:\n{goal}\n'
            'OUTPUT: 調査項目、利用データセット、利用サービス、必要なら対象の行だけ。INPUT のメタデータを繰り返さない。'
        )
        text = self.llm_client.generate(
            prompt, temperature=0.0, max_tokens=4096, enable_thinking=True,
            reasoning_budget_tokens=768,
            system_prompt='You are a sequential task planner. Follow the exact text format. Name the target of an Intent by its name on a 対象: line. Declare registered resources for external reads. Local aggregation of previous outputs needs no resource. Return only the three requested fields in each block, plus the optional 対象: line for an Intent about one target. Resource metadata is INPUT, never copy it into the output. Never return code.',
        )
        result = []
        blocks = _plan_blocks(text)
        if not blocks:
            raise ValueError('Plan must start with 調査項目:')
        for block in blocks:
            result.append(_parse_intent(block, datasets, services, allow_local=bool(result)))
        return result
