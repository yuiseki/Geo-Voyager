import hashlib
import json
from unittest.mock import Mock
from uuid import uuid4

import pytest

from geo_voyager.skill import Skill, SkillLibrary
from geo_voyager.skill_embedding_cache import SkillEmbeddingCache


def test_cache_creation_and_reuse(tmp_path):
    skill = Skill(uuid4(), '説明\n', 'code')
    SkillLibrary(tmp_path).add(skill)
    client = Mock(model='granite-embedding')
    client.embed.return_value = [[1.0] + [0.0] * 383]
    cache = SkillEmbeddingCache(client, root=tmp_path)
    assert cache.get(skill) == client.embed.return_value[0]
    payload = json.loads((tmp_path / str(skill.id) / 'description_embedding.json').read_text())
    assert payload == dict(format_version=1, model=client.model, dimensions=384,
                           description_sha256=hashlib.sha256(skill.description.encode()).hexdigest(),
                           embedding=client.embed.return_value[0])
    client.embed.assert_called_once_with([skill.description])
    client.reset_mock()
    assert cache.get(skill) == payload['embedding']
    client.embed.assert_not_called()


@pytest.mark.parametrize('damage', ['json', 'version', 'model', 'hash', 'dimensions', 'length', 'nan', 'inf'])
def test_invalid_cache_is_regenerated(tmp_path, damage):
    skill = Skill(uuid4(), '説明', 'code')
    SkillLibrary(tmp_path).add(skill)
    client = Mock(model='granite-embedding')
    client.embed.return_value = [[1.0] + [0.0] * 383]
    cache = SkillEmbeddingCache(client, root=tmp_path)
    cache.get(skill)
    path = tmp_path / str(skill.id) / 'description_embedding.json'
    data = json.loads(path.read_text())
    if damage == 'json':
        path.write_text('{')
    else:
        key, value = {'version': ('format_version', 2), 'model': ('model', 'other'),
                      'hash': ('description_sha256', 'other'), 'dimensions': ('dimensions', 3),
                      'length': ('embedding', [1.0]), 'nan': ('embedding', [float('nan')] * 384),
                      'inf': ('embedding', [float('inf')] * 384)}[damage]
        data[key] = value
        path.write_text(json.dumps(data))
    client.reset_mock()
    cache.get(skill)
    client.embed.assert_called_once_with([skill.description])


def test_description_change_regenerates(tmp_path):
    skill = Skill(uuid4(), 'before', 'code')
    SkillLibrary(tmp_path).add(skill)
    client = Mock(model='granite-embedding')
    client.embed.return_value = [[1.0] * 384]
    cache = SkillEmbeddingCache(client, root=tmp_path)
    cache.get(skill)
    client.reset_mock()
    cache.get(Skill(skill.id, 'after', skill.code))
    client.embed.assert_called_once_with(['after'])


@pytest.mark.parametrize('vector', [[1.0], [float('nan')] * 384, [float('inf')] * 384, [0.0] * 384])
def test_invalid_generated_embedding_is_not_saved(tmp_path, vector):
    skill = Skill(uuid4(), 'description', 'code')
    SkillLibrary(tmp_path).add(skill)
    client = Mock(model='granite-embedding')
    client.embed.return_value = [vector]
    with pytest.raises(ValueError):
        SkillEmbeddingCache(client, root=tmp_path).get(skill)
    assert not (tmp_path / str(skill.id) / 'description_embedding.json').exists()
