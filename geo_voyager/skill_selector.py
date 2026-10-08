from uuid import UUID

from .intent import Intent
from .llama_client import LlamaClient
from .skill import Skill


class SkillSelector:
    def __init__(self, llm_client: LlamaClient | None = None) -> None:
        self.llm_client = llm_client if llm_client is not None else LlamaClient()

    def select(self, intent: Intent, skills: list[Skill]) -> Skill | None:
        if not skills:
            return None
        candidates = '\n\n'.join(
            f'UUID: {skill.id}\ndescription: {skill.description}' for skill in skills
        )
        prompt = (
            'Intent をそのまま完遂できる既存 Skill があるか判断してください。\n'
            '類似しているだけでは選ばないでください。\n'
            'コードの変更や追加計算が必要なら「なし」を選んでください。\n'
            '最大/最小、集計方法、対象、出力内容など意味の違いを区別してください。\n'
            '候補の順序は適合性を保証しません。候補が1件でも適合性を判定してください。\n'
            '適切なものがなければ「なし」を選んでください。\n'
            '返答は次の2行だけにし、前置き・コードフェンスを付けないでください。\n'
            '選択: 候補のUUIDまたはなし\n理由: 選択理由の本文\n'
            '理由は空にせず1行で書いてください。\n'
            '該当する候補がない場合の出力例:\n'
            '選択: なし\n理由: Intentをそのまま完遂できるSkillが候補に存在しないため。\n\n'
            f'Intent:\n{intent.text}\n\n候補 Skill:\n{candidates}'
        )
        lines = self.llm_client.generate(prompt).strip().splitlines()
        if (
            len(lines) != 2
            or not lines[0].startswith('選択: ')
            or not lines[1].startswith('理由: ')
            or not lines[1].removeprefix('理由: ').strip()
        ):
            raise ValueError('Selection must contain 選択: and a non-empty 理由: in two lines')
        selection = lines[0].removeprefix('選択: ').strip()
        if selection == 'なし':
            return None
        skill_id = UUID(selection)
        for skill in skills:
            if skill.id == skill_id:
                return skill
        raise ValueError('Selected UUID is not a candidate')
