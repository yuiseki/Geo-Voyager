from pathlib import Path
import re

SOURCE = Path(__file__).resolve().parents[1] / 'geo_voyager'
# Anything that selects a target by its position in an earlier list.
ORDINAL_REFERENCES = (r'一覧の\s*[0-9N]+\s*番目', r'一覧の番号', r'\(\[0-9\]\+\)番', r'N-1 番目', r'by runtime list position')


def test_no_component_selects_a_target_by_list_position():
    for path in sorted(SOURCE.glob('*.py')):
        text = path.read_text()
        for pattern in ORDINAL_REFERENCES:
            assert not re.search(pattern, text), f'{path.name} still refers to list positions: {pattern}'


def test_planner_generator_and_critic_share_one_target_contract():
    # The same words in all three: the target is named, found by name, and carries a stable id.
    for name, markers in {'planner.py': ('対象: 名前', 'name と安定ID'),
                          'skill_candidate_generator.py': ('intent_target', 'relation_id'),
                          'critic.py': ('resolve_target', '名前と安定ID')}.items():
        text = (SOURCE / name).read_text()
        for marker in markers:
            assert marker in text, f'{name} lacks {marker}'
