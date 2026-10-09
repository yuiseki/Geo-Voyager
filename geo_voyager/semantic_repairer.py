"""Repair a candidate whose run succeeded but whose answer the Critic rejected.

This is not the runtime repair. A runtime repair answers an execution failure and sees a traceback.
A semantic repair answers a Critic reason and sees the observation that was judged, so it can
change what the code selects, filters or computes. It must not change the Intent, the target or
the output keys, and must not write observed values into the code.
"""
from dataclasses import dataclass
from typing import Sequence

from .contracts import PRIMITIVE_CONTRACT, dataset_contract, service_contract
from .execution_attempt import ExecutionAttempt
from .hardcoding import hardcoded_literals
from .intent import Intent
from .llama_client import LlamaClient
from .observation import Observation
from .observation_context import describe_observations
from .skill_candidate import SkillCandidate
from .skill_candidate_generator import _parse_candidate

SHOWN_OBSERVATION_LIMIT = 1500


@dataclass(frozen=True)
class SemanticRepair:
    candidate: SkillCandidate | None
    # proposed | unchanged | vibration | hardcoded | invalid. Only 'proposed' is worth running.
    status: str
    hardcoded: tuple[str, ...] = ()


def _normalized(code: str) -> str:
    lines = (line.rstrip() for line in code.splitlines())
    return '\n'.join(line for line in lines if line.strip() and not line.lstrip().startswith('#'))


def _bounded(text: str, limit: int = SHOWN_OBSERVATION_LIMIT) -> str:
    return text if len(text) <= limit else text[:limit] + f'…（以下 {len(text) - limit} 文字省略）'


class SemanticRepairer:
    def __init__(self, llm_client: LlamaClient | None = None) -> None:
        self.llm_client = llm_client if llm_client is not None else LlamaClient()

    def repair(self, intent: Intent, candidate: SkillCandidate, observations: Sequence[Observation],
               reason: str, history: Sequence[ExecutionAttempt] = ()) -> SemanticRepair:
        current = [observation.text for observation in observations]
        previous = [observation.text for observation in intent.previous_observations]
        try:
            proposed = _parse_candidate(self.llm_client.generate(
                self._prompt(intent, candidate, current, previous, reason), temperature=0.2, enable_thinking=True,
                max_tokens=3072, reasoning_budget_tokens=1024, assistant_prefix='説明:\n',
                system_prompt=(
                    'You repair Python code whose run succeeded but whose answer was judged wrong. '
                    'Change only what makes the result miss the Intent. Keep the Intent, the target and the output keys. '
                    'Never write values from the observations or from the reason into the code. '
                    'Return the complete code in the exact format, with no comments and no discussion. '
                    'Exact format:\n説明:\n<one sentence>\n---\nコード:\n```python\n<complete code>\n```'
                )))
        except ValueError:
            return SemanticRepair(None, 'invalid')
        code = _normalized(proposed.code)
        if code == _normalized(candidate.code):
            return SemanticRepair(proposed, 'unchanged')
        if any(code == _normalized(attempt.code) for attempt in history):
            return SemanticRepair(proposed, 'vibration')
        copied = hardcoded_literals(proposed.code, candidate.code, current + previous + [reason])
        if copied:
            return SemanticRepair(proposed, 'hardcoded', tuple(sorted(copied)))
        return SemanticRepair(proposed, 'proposed')

    @staticmethod
    def _prompt(intent: Intent, candidate: SkillCandidate, current: list[str], previous: list[str], reason: str) -> str:
        sections = [
            '実行は成功したが、Critic が回答を Intent の要求に足りないと判定した。元の Candidate を直接修正し、'
            '完全な Candidate を再出力する。説明やチャットは不要。',
            '修正してよいのは、結果の意味（対象の選び方、条件、集計、出力する項目）が Intent を満たさない原因の箇所だけ。\n'
            'Intent を変更・言い換えしない。対象を変えない。stdout は JSON のみで、元の出力のキーを保つ。\n'
            '答え・件数・ID・名前をコードへ固定しない。Observation や Critic の理由に出た値を貼り込まない（hardcoded 禁止）。'
            '値は実行時に previous_observations、intent_target、サービスの応答から取る。\n'
            'Critic の理由は不足の指摘であり、答えではない。API や Primitive を勝手に追加せず、外部 URL へ直接アクセスしない。',
            PRIMITIVE_CONTRACT,
        ]
        if intent.service_ids:
            sections.append(f'Services:\n{service_contract(intent)}')
        if intent.dataset_ids:
            sections.append(f'Datasets:\n{dataset_contract(intent)}')
        sections.append(f'Intent:\n{intent.text}')
        if intent.target_name is not None:
            sections.append(f'対象: {intent.target_name}（実行時変数 intent_target["name"]）')
        sections.append(f'元 description:\n{candidate.description}\n元 code:\n{candidate.code}')
        sections.append('現在の Observation（Critic が判定した出力）:\n' + '\n'.join(_bounded(text) for text in current))
        sections.append(f'Critic の理由:\n{reason}')
        if intent.previous_observations:
            sections.append('前段 Observation の形:\n' + describe_observations(intent.previous_observations)
                            + '\n前段 Observation（実行時は previous_observations、list[str]）:\n'
                            + '\n'.join(f'previous_observations[{i}]: {_bounded(text)}' for i, text in enumerate(previous)))
        sections.append('出力形式のみ:\n説明:\n<description>\n---\nコード:\n```python\n<complete code>\n```')
        return '\n\n'.join(sections)
