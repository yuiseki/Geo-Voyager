from collections import Counter
from dataclasses import dataclass

from .datasets import load_readable_dataset_graph
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


@dataclass(frozen=True)
class ProposedGoal:
    goal: str
    reason: str


class CurriculumRejected(ValueError):
    def __init__(self, reason: str, reply: str) -> None:
        super().__init__(reason)
        self.reason, self.reply = reason, reply


class Curriculum:
    """Decides what to explore next, as Voyager's automatic curriculum does: one Goal at a time, from what is known.

    It sees the resources, the findings so far (the World Graph) and the Goals already tried with their outcome.
    It is not given a list of Goals to reach: what to find out is the model's choice.
    """

    def __init__(self, llm_client: LlamaClient | None = None) -> None:
        self.llm_client = llm_client if llm_client is not None else LlamaClient()

    def propose(self, findings: list[dict], attempts: list[dict], *, note: str | None = None) -> ProposedGoal:
        tried = _newest_within([f'- {attempt["goal"]} → ' + ('答えが出た' if attempt['success'] else
                                                            f'未達（{attempt["stop_reason"]}: {attempt["reason"][:150]}）') + '\n'
                                for attempt in attempts[-ATTEMPTS_SHOWN:]], ATTEMPTS_CHARS) or 'まだ無い。\n'
        budget = HISTORY_CHARS - len('これまでの発見:\nこれまでに試した Goal:\n') - len(tried)
        known = (_newest_within(_render_findings(findings[-FINDINGS_SHOWN:]), budget) or 'まだ何も分かっていない。\n'
                 if findings else 'まだ何も分かっていない。\n')
        prompt = (
            'あなたは、利用可能なデータとサービスを使って東京の世界を自律的に探索するエージェントの curriculum です。'
            '次に調べる Goal を1件だけ決めてください。\n'
            'Goal は、利用可能リソースだけで答えが1つに決まる、具体的で測れる問いにする（件数、距離、時間、比較、最大・最小、合計、割合、一覧など）。\n'
            'まだ分かっていないことを調べる。これまでの発見で答えが出た Goal を繰り返さない。\n'
            'これまでの発見を土台にして、少しずつ難しく、より広い問いへ進む。分かった対象や値を組み合わせ、新しい関係や傾向を明らかにする。'
            'ただし、未達が続いたときは、より小さく確実に答えられる問いに分ける。\n'
            '問いは、場所、人口、施設、移動、土地利用など、世界について何かを教えるものにする。relation_id のような識別子は対象を指す名札で、'
            'その最大値や合計は何も教えないので問いにしない。測る値が世界の何を表すか（例: 駅の数か、線路の区間の数か）を考えて選ぶ。\n'
            '直近の発見と同じ型の問い（同じタグや同じ測り方で、対象だけを変えたもの）を続けない。別の主題、別の測り方へ広げる。'
            'まだ使っていないリソースがあれば、それで何が分かるかを試す。\n'
            '未達の Goal を同じ文で繰り返さない。未達の理由を読んで、問いを変えるか分ける。\n'
            'Goal には何を知りたいかだけを書く。API のパスやパラメータ、コードは書かない。\n'
            + (f'{note}\n' if note else '')
            + '返答は次の2行だけ。前置き、番号、コードフェンス禁止。\nGoal: 問いの本文\n理由: この問いを選んだ理由（これまでの発見とのつながり）\n'
            + f'INPUT: 利用可能リソース:\n{Planner._resource_text(load_readable_dataset_graph(), load_service_graph(), full=True, measured=True)}\n'
            + f'リソースを使った発見の数: {_usage(findings)}\n'
            + f'まだ使っていないリソース: {_unused(findings)}\n'
            + f'これまでの発見:\n{known}'
            + f'これまでに試した Goal:\n{tried}'
            + 'OUTPUT: Goal: と 理由: の2行だけ。'
        )
        text = self.llm_client.generate(
            prompt, temperature=0.7, max_tokens=4096, enable_thinking=True, reasoning_budget_tokens=768,
            system_prompt='You are the curriculum of an exploring agent. Propose exactly one new, concrete, measurable Goal '
                          'that builds on what is known. Reply with the two lines Goal: and 理由: only.')
        return _parse(text, findings)


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
        targets = [TargetRef(**item).display() for item in finding['targets']]
        if targets:
            entry += '  判明した対象: ' + '、'.join(targets) + '\n'
        entries.append(entry)
    return entries


def _parse(text: str, findings: list[dict]) -> ProposedGoal:
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    goals = [line for line in lines if line.startswith('Goal:')]
    reasons = [line for line in lines if line.startswith('理由:')]
    if len(goals) != 1 or len(reasons) != 1:
        raise CurriculumRejected('Goal: の行と 理由: の行を1行ずつ書く', text)
    goal, reason = goals[0].removeprefix('Goal:').strip(), reasons[0].removeprefix('理由:').strip()
    if not goal or not reason:
        raise CurriculumRejected('Goal と理由の本文が空', text)
    if any(goal == finding['goal'] for finding in findings):
        raise CurriculumRejected(f'「{goal}」は既に答えが出ている。まだ分かっていないことを調べる', text)
    details = api_details_in(goal)
    if details:
        raise CurriculumRejected(f'Goal に API の詳細が書かれている: {", ".join(details)}。何を知りたいかだけを書く', text)
    return ProposedGoal(goal, reason)
