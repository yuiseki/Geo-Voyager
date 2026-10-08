from geo_voyager.intent import Intent
from geo_voyager.skill import SkillLibrary
from geo_voyager.skill_selector import SkillSelector


def test_select_population_skills_and_reject_unrelated_intent():
    skills = SkillLibrary().all()
    selector = SkillSelector()
    for text, expected in (
        ('東京都23区で人口が最も多い区と人口を求める', '72c549dd-e449-4bef-97f1-e3a2eab27d64'),
        ('東京都23区で人口が最も少ない区と人口を求める', 'e722f367-1ff1-4796-89a3-48cfd1dfcb68'),
        ('東京都23区ごとの鉄道駅数を集計する', None),
    ):
        # Similarity order previously put the minimum-population Skill first.
        candidates = sorted(skills, key=lambda skill: str(skill.id), reverse=True)
        selected = selector.select(Intent(text, ('yuiseki/jp-admin-2026-09',)), candidates)
        selected_id = str(selected.id) if selected else None
        print(f'{text} -> {selected_id}')
        assert selected_id == expected
