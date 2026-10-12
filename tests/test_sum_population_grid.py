from unittest.mock import Mock

import pytest

from geo_voyager.control_primitives import dataset_url
from geo_voyager.datasets import load_dataset_graph, load_readable_dataset_graph

WORLDPOP = 'yuiseki/worldpop-jp-2026-01'


def test_worldpop_dataset_reads_the_pinned_100m_2020_total_population_cog():
    assert load_dataset_graph().get(WORLDPOP).data_url == (
        'https://huggingface.co/datasets/yuiseki/worldpop-jp-2026-01/resolve/'
        'cb54e5985662c617a235278bc3529cc172e6368c/'
        'cog/GIS/Population/Global_2015_2030/R2025A/2020/JPN/v1/100m/constrained/'
        'jpn_pop_2020_CN_100m_R2025A_v1.tif'
    )
    assert WORLDPOP in {dataset.id for dataset in load_readable_dataset_graph().all()}
    assert dataset_url(WORLDPOP) == f'http://gateway:8000/datasets/{WORLDPOP}'


def test_worldpop_description_says_which_file_is_readable():
    description = load_dataset_graph().get(WORLDPOP).description
    assert '2020' in description and '100m' in description and 'sum_population_grid' in description


def test_the_code_generation_prompts_name_the_primitive():
    from geo_voyager.contracts import PRIMITIVE_CONTRACT
    from geo_voyager.intent import Intent
    from geo_voyager.skill_candidate_generator import SkillCandidateGenerator
    assert 'sum_population_grid(connection, zones)' in PRIMITIVE_CONTRACT
    client = Mock()
    client.generate.return_value = '説明:\nx\n---\nコード:\n```python\ndef f():\n    return 1\n```'
    try:
        SkillCandidateGenerator(client).generate(Intent('東京23区の区ごとの推計人口', dataset_ids=(WORLDPOP,)))
    except Exception:
        pass
    prompt = client.generate.call_args.args[0]
    assert 'sum_population_grid(connection, zones)' in prompt and 'geometry 列を持つ relation' in prompt
