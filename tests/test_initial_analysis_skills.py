import ast
from unittest.mock import Mock

import pytest

from geo_voyager.skill import SkillLibrary


@pytest.mark.parametrize('skill_id,primitive,operation,result', [
    ('befbc141-baad-41bc-abdf-dc34311c3111', 'load_admin_units', 'sum(population) AS population_total', [(123,)]),
    ('f2d4785a-779a-4927-b75d-65d1e4852ab2', 'load_admin_units', 'population DESC, code5 ASC', [('code-a', '区域A', 30), ('code-b', '区域B', 20), ('code-c', '区域C', 10), ('code-d', '区域D', 5), ('code-e', '区域E', 1)]),
    ('ccd6a22b-d795-4359-a06a-f2ac214e6a28', 'load_stations', 'count(*) AS station_count', [(7,)]),
    ('fb0fb79f-10b3-424f-ae27-4d6292f474c4', 'load_stations', 'latitude DESC, name ASC', [('テスト駅', 50.0, 140.0)]),
])
def test_initial_skill_uses_primitive_and_computes_result(skill_id, primitive, operation, result, monkeypatch, capsys):
    import geo_voyager.control_primitives as primitives
    skill = SkillLibrary().get(skill_id)
    connection = Mock()
    context = Mock()
    context.__enter__ = Mock(return_value=connection)
    context.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(primitives, 'connect_duckdb', Mock(return_value=context))
    loader = Mock()
    monkeypatch.setattr(primitives, primitive, loader)
    relation = loader.return_value
    relation.aggregate.return_value.fetchone.return_value = result[0]
    relation.order.return_value.limit.return_value.fetchall.return_value = result
    relation.order.return_value.limit.return_value.fetchone.return_value = result[0]
    dataset_id = 'yuiseki/jp-admin-2026-09' if primitive == 'load_admin_units' else 'yuiseki/ekidata-jp'
    exec(skill.code, {'dataset_id': dataset_id})
    if primitive == 'load_admin_units':
        loader.assert_called_once_with(dataset_id, connection, area='東京都23区')
    else:
        loader.assert_called_once_with(dataset_id, connection)
    if 'sum(' in operation or 'count(' in operation:
        relation.aggregate.assert_called_once_with(operation)
        assert str(result[0][0]) in capsys.readouterr().out
    else:
        relation.order.assert_called_once_with(operation)
        relation.order.return_value.limit.assert_called_once_with(5 if 'code5' in operation else 1)
        output = capsys.readouterr().out
        assert all(str(row[0] if primitive == 'load_stations' else row[1]) in output for row in result)
    assert skill.description.strip()
    assert 'http://' not in skill.code and 'https://' not in skill.code
    ast.parse(skill.code)


def test_library_has_six_initial_skills():
    assert len(SkillLibrary().all()) == 6
