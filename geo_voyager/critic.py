from .critique import Critique
from .intent import Intent
from .llama_client import LlamaClient
from .observation import Observation


class Critic:
    def __init__(self, llm_client: LlamaClient | None = None) -> None:
        self.llm_client = llm_client if llm_client is not None else LlamaClient()

    def check(self, intent: Intent, observations: list[Observation]) -> Critique:
        if not observations:
            return Critique(success=False, reason='Observation がありません')
        if all(not observation.text.strip() for observation in observations):
            return Critique(success=False, reason='Observation の本文がすべて空です')
        observation_text = '\n'.join(f'- {observation.text}' for observation in observations)
        prompt = (
            'Observation が Intent の要求した調査結果を実際に答えているか判定してください。\n'
            '仮説が正しいか、結果が望ましいかは判定しない。\n'
            'データを取得したという報告だけでは、要求された調査結果を答えたことにはなりません。\n'
            '要求された具体的な回答があれば成功、回答が不足していれば失敗としてください。\n'
            '返答は次の2行だけにし、前置き・コードフェンスを付けないでください。\n'
            '判定: 成功\n理由: 理由の本文\n'
            '失敗の場合は1行目を「判定: 失敗」にしてください。理由も1行にしてください。\n\n'
            f'Intent:\n{intent.text}\n\nObservation:\n{observation_text}'
        )
        return Critique.from_text(self.llm_client.generate(prompt))
