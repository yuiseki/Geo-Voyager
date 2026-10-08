from dataclasses import dataclass


@dataclass(frozen=True)
class Critique:
    success: bool
    reason: str

    @classmethod
    def from_text(cls, text: str) -> 'Critique':
        lines = text.strip().splitlines()
        if (len(lines) != 2 or lines[0] not in ('判定: 成功', '判定: 失敗')
                or not lines[1].startswith('理由:')):
            raise ValueError('Critique must contain 判定: 成功/失敗 and 理由: on two lines')
        reason = lines[1].removeprefix('理由:').strip()
        if not reason:
            raise ValueError('Critique reason must not be empty')
        return cls(success=lines[0] == '判定: 成功', reason=reason)
