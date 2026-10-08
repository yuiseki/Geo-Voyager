"""既存ローカル LLM による Critic の明示的な確認。通常 pytest には含めない。"""

import pytest

from geo_voyager.critic import Critic
from geo_voyager.intent import Intent
from geo_voyager.observation import Observation


@pytest.mark.parametrize(('text', 'success'), [
    ('世田谷区、943664人', True),
    ('23区の人口データを取得した', False),
])
def test_local_critic_checks_intent_completion(text, success):
    intent = Intent(
        text='東京都23区で人口が最も多い区と人口を求める',
        dataset_ids=('yuiseki/jp-admin-2026-09',),
    )
    result = Critic().check(intent, [Observation(text)])
    print(f'{text}: {result}', flush=True)
    assert result.success is success
    assert result.reason
