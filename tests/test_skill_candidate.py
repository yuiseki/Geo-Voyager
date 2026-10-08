from dataclasses import fields
from uuid import UUID

from geo_voyager.skill_candidate import SkillCandidate, promote


def test_candidate_has_only_code_and_description():
    candidate = SkillCandidate(code='print("ok")', description='調査コード')
    assert candidate.code == 'print("ok")' and candidate.description == '調査コード'
    assert {field.name for field in fields(candidate)} == {'code', 'description'}


def test_promote_creates_fresh_uuid_and_preserves_candidate_content():
    candidate = SkillCandidate(code='print("ok")', description='成功した調査')
    first, second = promote(candidate), promote(candidate)
    assert isinstance(first.id, UUID) and first.id.version == 4
    assert first.id != second.id
    assert first.code == candidate.code and first.description == candidate.description
