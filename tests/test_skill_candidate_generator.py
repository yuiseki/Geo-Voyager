from unittest.mock import Mock

import pytest

from geo_voyager.intent import Intent
from geo_voyager.skill_candidate import SkillCandidate
from geo_voyager.skill_candidate_generator import SkillCandidateGenerator

VALID = '''説明:
行政区域から人口最小の区域を求める
---
コード:
```python
from geo_voyager.control_primitives import connect_duckdb, load_admin_units
print("result")
```'''


@pytest.mark.parametrize('reply', [VALID, VALID.replace('---\nコード:\n', '---\n\nコード:\n\n')])
def test_generator_passes_intent_and_primitive_contracts_and_parses_candidate(reply):
    client = Mock()
    client.generate.return_value = reply
    intent = Intent('東京都23区で人口が最も少ない区と人口を求める', ('yuiseki/jp-admin-2026-09',))
    candidate = SkillCandidateGenerator(client).generate(intent)
    assert candidate == SkillCandidate(
        code='from geo_voyager.control_primitives import connect_duckdb, load_admin_units\nprint("result")',
        description='行政区域から人口最小の区域を求める',
    )
    client.generate.assert_called_once()
    prompt = client.generate.call_args.args[0]
    for text in (intent.text, intent.dataset_ids[0], 'connect_duckdb()',
                 'dataset_url(dataset_id)', 'load_admin_units(dataset_id, connection, area=None)',
                 'load_admin_units(dataset_id, connection, area="東京都23区")',
                 '外部URLを直接使わない', 'stdout', 'dataset_id は実行環境から与えられる',
                 '再利用可能',
                 'from geo_voyager.control_primitives import connect_duckdb, load_admin_units',
                 'pandas DataFrame ではない', 'order(expression)', 'fetchone()', 'dataset_id = ... という代入を書かない', 'stdout に選択・集計の意味', 'トップレベル'):
        assert text in prompt
    assert "13101" not in prompt and "13123" not in prompt


@pytest.mark.parametrize('reply', [
    '', 'print("ok")', VALID.replace('説明:', '解説:', 1),
    VALID.replace('\n---\n', '\n', 1), VALID.replace('コード:', 'Python:', 1),
    VALID.replace('```python', '```json', 1), VALID + '\n追記',
    '説明:\n\n---\nコード:\n```python\nprint("ok")\n```',
    '説明:\n説明本文\n---\nコード:\n```python\n   \n```',
])
def test_generator_rejects_invalid_or_empty_sections(reply):
    client = Mock()
    client.generate.return_value = reply
    with pytest.raises(ValueError):
        SkillCandidateGenerator(client).generate(Intent('調査', ('yuiseki/jp-admin-2026-09',)))
