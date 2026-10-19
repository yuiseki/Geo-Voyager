from collections import Counter
import math
import re
from dataclasses import dataclass

from .datasets import load_readable_dataset_graph
from .exploration_graph import outcome
from .intent_text import api_details_in
from .llama_client import LlamaClient
from .planner import Planner
from .services import load_service_graph
from .target_ref import TargetRef

# The prompt has to fit next to the reply in the model's context (8192 tokens), so only the latest are shown.
FINDINGS_SHOWN = 20
ATTEMPTS_SHOWN = 15
ANSWER_SHOWN = 300
# Findings and attempts grow with the exploration. In round 3 the prompt reached 7,608 of the 8,192 tokens by Goal 25
# and every reply came back empty. 6,000 characters of history is about 3,400 tokens, which keeps the whole prompt
# near 5,700 tokens and leaves room to think and answer. A third of it goes to the attempts.
HISTORY_CHARS = 6000
ATTEMPTS_CHARS = HISTORY_CHARS // 3
# Told not to go on with the same kind of question, the model went on: in exploration 11 (2026-10-15) Goals 18 to 31
# asked households per person nine times, reworded. Those rewordings were 0.95 or more alike (cosine, embeddinggemma)
# to a Goal tried before them; a Goal on another subject or by another measure was 0.94 or less. Compared only with
# the 5 tries before, Goals 32 to 61 came back to rewordings 16 and 24 Goals later, so every try is compared.
EMBEDDED_AT_ONCE = 32
# The reward of curiosity (ADR 0014): the findings whose predictions failed most are shown however old they are.
SURPRISING_SHOWN = 5
SURPRISING_CHARS = 1500
SIMILAR_COSINE = 0.95


@dataclass(frozen=True)
class ProposedGoal:
    goal: str
    reason: str
    # The main value of the answer as the curriculum expected it, before the Goal is explored. It is kept for the
    # surprise of the answer (geo_voyager.surprise, ADR 0014) and never shown to the Planner, so as not to steer it.
    prediction: str = ''
    # The drawn ingredients the Goal used, on a Goal of exploration (geo_voyager.ingredients); none on one of digging.
    ingredients: tuple[str, ...] = ()


class CurriculumRejected(ValueError):
    def __init__(self, reason: str, reply: str) -> None:
        super().__init__(reason)
        self.reason, self.reply = reason, reply


class Curriculum:
    """Decides what to explore next, as Voyager's automatic curriculum does: one Goal at a time, from what is known.

    It sees the resources, the findings so far (the World Graph) and the Goals already tried with their outcome.
    It is not given a list of Goals to reach: what to find out is the model's choice.
    """

    def __init__(self, llm_client: LlamaClient | None = None, embedding=None) -> None:
        self.llm_client = llm_client if llm_client is not None else LlamaClient()
        self.embedding = embedding

    def propose(self, findings: list[dict], attempts: list[dict], *, note: str | None = None,
                ingredients=None) -> ProposedGoal:
        """The next Goal. ingredients, drawn at random, make it a Goal of exploration: it must use one or more of them."""
        # Each try is shown by what was checked without a model only, not by a Critic's reason (ADR 0011).
        tried = _newest_within([f'- {attempt["goal"]} → {outcome(attempt)}\n' for attempt in attempts[-ATTEMPTS_SHOWN:]],
                               ATTEMPTS_CHARS) or 'まだ無い。\n'
        budget = HISTORY_CHARS - len('これまでの発見:\nこれまでに試した Goal:\n') - len(tried)
        known = (_newest_within(_render_findings(findings[-FINDINGS_SHOWN:]), budget) or 'まだ何も分かっていない。\n'
                 if findings else 'まだ何も分かっていない。\n')
        surprising = _surprising(findings)
        prompt = (
            'あなたは、利用可能なデータとサービスを使って日本と世界を自律的に探索するエージェントの curriculum です。'
            '次に調べる Goal を1件だけ決めてください。\n'
            'Goal は、利用可能リソースだけで答えが1つに決まる、具体的で測れる問いにする（件数、距離、時間、比較、最大・最小、合計、割合、一覧など）。\n'
            'まだ分かっていないことを調べる。これまでの発見で答えが出た Goal を繰り返さない。\n'
            'これまでの発見を土台にして、少しずつ難しく、より広い問いへ進む。分かった対象や値を組み合わせ、新しい関係や傾向を明らかにする。'
            'ただし、未達が続いたときは、より小さく確実に答えられる問いに分ける。\n'
            '問いは、場所、人口、施設、移動、土地利用など、世界について何かを教えるものにする。relation_id のような識別子は対象を指す名札で、'
            'その最大値や合計は何も教えないので問いにしない。測る値が世界の何を表すか（例: 駅の数か、線路の区間の数か）を考えて選ぶ。\n'
            '直近の発見と同じ型の問い（同じタグや同じ測り方で、対象だけを変えたもの）を続けない。別の主題、別の測り方へ広げる。'
            'まだ使っていないリソースがあれば、それで何が分かるかを試す。\n'
            '未達の Goal を同じ文で繰り返さない。問いを変えるか分ける。確かめた失敗が書かれていれば、その手を避けられる問いにする。\n'
            'Goal には何を知りたいかだけを書く。API のパスやパラメータ、コードは書かない。\n'
            'Goal と一緒に、その答えの主な値（数か名前を1つ）を、調べる前に予想する。予想は、当てにいく本気の見積もりを書く。\n'
            '発見の「外れ度」は、そのときの予想と実際の答えの食い違い（0 は的中、1 は 10 倍以上の外れか、違う名前）。'
            '外れ度が大きい発見は、世界が予想と違っていた所で、まだ学べることが多い。なぜ外れたのかを確かめる、'
            '似た対象でも同じことが起きるかを見る、別の尺度で測る、などして掘り下げる。外れ度が小さい主題は、もう分かっているので離れる。\n'
            + (_exploring(ingredients) if ingredients is not None else '')
            + (f'{note}\n' if note else '')
            + f'返答は次の{"4" if ingredients is not None else "3"}行だけ。前置き、番号、コードフェンス禁止。\nGoal: 問いの本文\n'
            '理由: この問いを選んだ理由（これまでの発見、特に予想が外れた発見とのつながり）\n'
            '予想: 答えの主な値の予想（数か名前を1つだけ。例: 約 370 万人、横浜市）\n'
            + ('材料: 使った今回の材料を、書かれた名前のまま「、」で区切って書く\n' if ingredients is not None else '')
            + f'INPUT: 利用可能リソース:\n{Planner._resource_text(load_readable_dataset_graph(), load_service_graph(), full=True, measured=True)}\n'
            + f'リソースを使った発見の数: {_usage(findings)}\n'
            + f'まだ使っていないリソース: {_unused(findings)}\n'
            + f'予想が大きく外れた発見（外れ度の大きい順）:\n{surprising}'
            + f'これまでの発見:\n{known}'
            + f'これまでに試した Goal:\n{tried}'
            + ('OUTPUT: Goal: と 理由: と 予想: と 材料: の4行だけ。' if ingredients is not None
               else 'OUTPUT: Goal: と 理由: と 予想: の3行だけ。')
        )
        text = self.llm_client.generate(
            prompt, temperature=0.7, max_tokens=4096, enable_thinking=True, reasoning_budget_tokens=768,
            system_prompt='You are the curriculum of an exploring agent. Propose exactly one new, concrete, measurable Goal '
                          'that builds on what is known, and predict its answer. Reply with the three lines Goal:, 理由: '
                          'and 予想: only.')
        proposed = _parse(text, findings)
        if ingredients is not None:
            proposed = ProposedGoal(proposed.goal, proposed.reason, proposed.prediction, _used(text, ingredients))
            missing = ingredients.without_areas(proposed.goal)
            if missing:
                raise CurriculumRejected(f'{"。".join(missing)}で、面を問うと答えは調べる前から 0 になる。'
                                         '点の件数を問うか、面のある区やタグの問いにする', text)
        if self.embedding is not None:
            _refuse_a_repeat(proposed.goal, [attempt['goal'] for attempt in attempts], self.embedding, text)
        return proposed


def _refuse_a_repeat(goal: str, tried_goals: list[str], embedding, reply: str) -> None:
    """Refuse a Goal that asks again, reworded, what one of the Goals tried asked."""
    if not tried_goals:
        return
    asked = embedding.embed([goal])[0]
    vectors = [vector for begin in range(0, len(tried_goals), EMBEDDED_AT_ONCE)
               for vector in embedding.embed(tried_goals[begin:begin + EMBEDDED_AT_ONCE])]
    similar = [tried for tried, vector in zip(tried_goals, vectors) if _cosine(asked, vector) >= SIMILAR_COSINE]
    if similar:
        raise CurriculumRejected(f'「{goal}」は、前に試した「{similar[-1]}」と同じ型の問いの言い換え。'
                                 '別の主題、別の測り方、まだ使っていないリソースの問いにする', reply)


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b)) / math.sqrt(sum(x * x for x in a) * sum(y * y for y in b))


def _resource_ids() -> list[str]:
    return [item.id for item in load_readable_dataset_graph().all()] + [item.id for item in load_service_graph().all()]


def _usage(findings: list[dict]) -> str:
    counts = Counter(resource for finding in findings for resource in finding['resources'])
    return '、'.join(f'{resource}: {count} 件' for resource, count in counts.most_common()) or 'まだ無い'


def _unused(findings: list[dict]) -> str:
    used = {resource for finding in findings for resource in finding['resources']}
    return '、'.join(resource for resource in _resource_ids() if resource not in used) or '無い'


def _newest_within(entries: list[str], budget: int) -> str:
    """The newest entries whose total length fits the budget, in their original order."""
    kept, used = [], 0
    for entry in reversed(entries):
        if used + len(entry) > budget:
            break
        kept.append(entry)
        used += len(entry)
    return ''.join(reversed(kept))


def _render_findings(findings: list[dict]) -> list[str]:
    entries = []
    for finding in findings:
        entry = f'- {finding["goal"]}\n  答え: {finding["answer"][:ANSWER_SHOWN]}\n'
        if finding.get('prediction') and finding.get('surprise') is not None:
            entry += f'  予想: {finding["prediction"]} → 外れ度 {finding["surprise"]:.2f}\n'
        targets = [TargetRef(**item).display() for item in finding['targets']]
        if targets:
            entry += '  判明した対象: ' + '、'.join(targets) + '\n'
        entries.append(entry)
    return entries


def _exploring(ingredients) -> str:
    return ('今回は探検の回。下の今回の材料から 1 つ以上を使い、まだ聞いていない組み合わせの問いを立てる。'
            '最大・最小を問うものでもよい（例: 足立区で、周りの推計人口が最も多い神社はどこか）。'
            '材料は、利用可能リソースで測れる形にして使う。\n今回の材料:\n' + ingredients.text())


def _used(text: str, ingredients) -> tuple[str, ...]:
    """The ingredients the reply names on its line 材料:, each one drawn; refused when it names none or one not drawn."""
    lines = [line.strip() for line in text.strip().splitlines() if line.strip().startswith('材料:')]
    if len(lines) != 1:
        raise CurriculumRejected('探検の回は、材料: の行を1行書き、使った今回の材料を名前のまま並べる', text)
    # The description an ingredient is listed with, copied after its name (explore 31), is not its name.
    line = lines[0].removeprefix('材料:')
    while re.search(r'（[^（）]*）|\([^()]*\)', line):
        line = re.sub(r'（[^（）]*）|\([^()]*\)', '', line)
    named = tuple(name.strip() for name in re.split('[、,，]', line) if name.strip())
    if not named:
        raise CurriculumRejected('材料: の行に、使った今回の材料を1つ以上書く', text)
    undrawn = [name for name in named if name not in ingredients.names()]
    if undrawn:
        raise CurriculumRejected(f'材料: の {"、".join(undrawn)} は今回の材料に無い。今回の材料: {"、".join(ingredients.names())}', text)
    return named


def _surprising(findings: list[dict]) -> str:
    """The findings whose predictions failed most, most surprising first, within their budget."""
    scored = sorted((finding for finding in findings if finding.get('prediction') and (finding.get('surprise') or 0) > 0),
                    key=lambda finding: finding['surprise'], reverse=True)[:SURPRISING_SHOWN]
    kept, used = [], 0
    for entry in _render_findings(scored):
        if used + len(entry) > SURPRISING_CHARS:
            break
        kept.append(entry)
        used += len(entry)
    return ''.join(kept) or 'まだ無い。\n'


def _parse(text: str, findings: list[dict]) -> ProposedGoal:
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    goals = [line for line in lines if line.startswith('Goal:')]
    reasons = [line for line in lines if line.startswith('理由:')]
    predictions = [line for line in lines if line.startswith('予想:')]
    if len(goals) != 1 or len(reasons) != 1 or len(predictions) != 1:
        raise CurriculumRejected('Goal: の行と 理由: の行と 予想: の行を1行ずつ書く', text)
    goal, reason = goals[0].removeprefix('Goal:').strip(), reasons[0].removeprefix('理由:').strip()
    prediction = predictions[0].removeprefix('予想:').strip()
    if not goal or not reason or not prediction:
        raise CurriculumRejected('Goal と理由と予想の本文が空', text)
    if any(goal == finding['goal'] for finding in findings):
        raise CurriculumRejected(f'「{goal}」は既に答えが出ている。まだ分かっていないことを調べる', text)
    details = api_details_in(goal)
    if details:
        raise CurriculumRejected(f'Goal に API の詳細が書かれている: {", ".join(details)}。何を知りたいかだけを書く', text)
    return ProposedGoal(goal, reason, prediction)
