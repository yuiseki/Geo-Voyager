from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import Mock, patch
from uuid import UUID

import pytest

from geo_voyager.skills import POPULATION_SKILL_ID
from geo_voyager.skill import SkillLibrary


@pytest.mark.parametrize(('skill_id', 'direction'), [
    (POPULATION_SKILL_ID, 'DESC'),
    (UUID('e722f367-1ff1-4796-89a3-48cfd1dfcb68'), 'ASC'),
])
def test_population_skill_uses_primitives_and_computes_result_without_hardcoded_ward(skill_id, direction):
    skill = SkillLibrary().get(skill_id)
    relation = Mock()
    relation.order.return_value.limit.return_value.fetchone.return_value = ('test-code', 'テスト区', 123)
    with patch('geo_voyager.control_primitives.connect_duckdb') as connect, \
         patch('geo_voyager.control_primitives.load_admin_units', return_value=relation) as load:
        output = StringIO()
        with redirect_stdout(output):
            exec(skill.code, {'dataset_id': 'yuiseki/jp-admin-2026-09'})
    load.assert_called_once_with('yuiseki/jp-admin-2026-09', connect.return_value.__enter__.return_value, area='東京都23区')
    relation.filter.assert_not_called()
    relation.order.assert_called_once_with(f'population {direction}')
    relation.order.return_value.limit.assert_called_once_with(1)
    assert 'テスト区' in output.getvalue() and '123' in output.getvalue()
    assert '13101' not in skill.code + skill.description and '13123' not in skill.code + skill.description
    assert '世田谷' not in skill.code and '943664' not in skill.code
