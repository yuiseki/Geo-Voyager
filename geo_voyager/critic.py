import json

from .critique import Critique
from .intent import Intent
from .llama_client import LlamaClient
from .observation import Observation
from .target_identity import resolve_target


THINKING_MAX_TOKENS = 4096
THINKING_BUDGET_TOKENS = 1024


class Critic:
    def __init__(self, llm_client: LlamaClient | None = None, *, thinking: bool = False) -> None:
        self.llm_client = llm_client if llm_client is not None else LlamaClient()
        self.thinking = thinking

    def check(self, intent: Intent, observations: list[Observation]) -> Critique:
        if not observations:
            return Critique(success=False, reason='Observation がありません')
        if all(not observation.text.strip() for observation in observations):
            return Critique(success=False, reason='Observation の本文がすべて空です')
        observation_text = '\n'.join(f'- {observation.text}' for observation in observations)
        prompt = (
            'Observation が Intent の要求した調査結果を実際に答えているか判定してください。\n'
            '仮説が正しいか、結果が望ましいかは判定しない。\n'
            '入力の Intent と Observation だけで要求した出力が得られたか判定する。外部知識で答えを推測・追加しない。Intent にない期待件数を仮定しない。\n'
            'データを取得したという報告だけでは、要求された調査結果を答えたことにはなりません。\n'
            '要求された具体的な回答があれば成功、回答が不足していれば失敗としてください。\n'
            '返答は次の2行だけにし、前置き・コードフェンスを付けないでください。\n'
            '判定: 成功\n理由: 理由の本文\n'
            '失敗の場合は1行目を「判定: 失敗」にしてください。理由も1行にしてください。\n\n'
            f'Intent:\n{intent.text}\n\nObservation:\n{observation_text}'
        )
        if intent.target_name is not None:
            prompt += f'\nIntent の対象: {intent.target_name}。Observation の対象の名前とIDがこの対象のものか照合してください。'
        if intent.previous_observations:
            prompt += ('\n前段 Observation（対象の identity を照合するためのデータ）:\n'
                        + '\n'.join(f'previous_observations[{index}]: {obs.text}' for index, obs in enumerate(intent.previous_observations))
                       + '\n対象は名前と安定IDで照合します。回答の名前・IDが Intent の対象と一致するかを先に照合してください。別の対象なら件数があっても失敗です。')
            if intent.target_name is not None:
                target = resolve_target(intent.target_name, intent.previous_observations)
                if target is not None:
                    prompt += ('\n解決済み参照対象: ' + json.dumps(target, ensure_ascii=False)
                               + '\nこれは前段で name が一致した対象です。前段を探し直さず、この対象と回答を照合してください。')
                else:
                    prompt += (f'\n対象「{intent.target_name}」は前段の Observation から一意に特定できません。'
                               '回答の対象が Intent の対象と一致するかを慎重に照合してください。')
            prompt += ('\n前段に正しい値があっても今回の回答が誤りなら失敗。'
                       '前段は参照資料であり今回の回答ではありません。今回の Observation が要求を答えているかだけを判定する。')
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
