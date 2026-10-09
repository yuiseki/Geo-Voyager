### tag_top3_cuisine (最大 8 step)
Goal: Taginfo で cuisine キーの値を使用数の多い順に並べ、上位3つの値を示す。

stop: done / Goal の Critic: 失敗（上位3つの値がソート順で提示されていないため、要求された調査結果が満たされていない。） / oracle との一致: False

step 1: Taginfo で cuisine キーの値を使用数の多い順に並べ、上位3つの値を示す。
- 対象: なし / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: 実行失敗（実行 3 回）、失敗: ValueError: No values found for cuisine key
- Critic: Generated Python execution failed

step 2: Taginfo API で cuisine キーの値を使用数順に上位3件取得
- 対象: 対象: 飲食店タグの値上位3件 / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: 実行失敗（実行 3 回）、失敗: RuntimeError: Service taginfo HTTP 502: <!DOCTYPE HTML>
- Critic: Generated Python execution failed

step 3: Taginfo API の /api/4/key/tags エンドポイントで tag=cuisine, mode=frequency, count=3 を指定して、cuisine キーの値を使用数順に上位3件取得
- 対象: なし / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: 実行失敗（実行 3 回）、失敗: AssertionError: Expected 3 results
- Critic: Generated Python execution failed

step 4: Taginfo API で cuisine キーの値を count 順に上位10件取得
- 対象: 飲食 / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: Critic 失敗（実行 1 回）
- Critic: cuisine キーの値ではなく name キーの値が取得されており、Intentの要求を満たしていないため。
- Observation: {"results": [{"key": "name", "value": "Cuisine communautaire", "count": 131}, {"key": "name", "value": "Cuisine", "count": 104}, {"key": "fixme", "value": "Freeform tag `cuisine` used, to be doublechecked", "count": 98}, {"key": "name", "value": "Cuisine centrale", "count": 54}, {"key": "name", "val

step 5: Taginfo API で cuisine キーの値を使用数順に上位3件取得
- 対象: 飲食店タグの値上位3件 / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: 成功（実行 1 回）
- Critic: 指定された上位3件のcuisineキーの値と使用数が取得されているため。
- Observation: [{"name": "name=Cuisine communautaire", "relation_id": "name=Cuisine communautaire", "count": 131}, {"name": "name=Cuisine", "relation_id": "name=Cuisine", "count": 104}, {"name": "fixme=Freeform tag `cuisine` used, to be doublechecked", "relation_id": "fixme=Freeform tag `cuisine` used, to be doubl
- この step で初めて判明した対象: [{'name': 'name=Cuisine communautaire', 'relation_id': 'name=Cuisine communautaire'}, {'name': 'name=Cuisine', 'relation_id': 'name=Cuisine'}, {'name': 'fixme=Freeform tag `cuisine` used, to be doublechecked', 'relation_id': 'fixme=Freeform tag `cuisine` used, to be doublechecked'}]
- 学習した Skill: cea0b79f