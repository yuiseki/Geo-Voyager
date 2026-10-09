### tag_top3_cuisine (最大 8 step)
Goal: Taginfo で cuisine キーの値を使用数の多い順に並べ、上位3つの値を示す。

stop: repeated_intent / Goal の Critic: 失敗（Goal を完了できなかった: repeated_intent） / oracle との一致: False

step 1: cuisine キーの値を使用数の多い順に並べ、上位3つ
- 対象: cuisine / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: Critic 失敗（実行 2 回）
- Critic: 調査結果が空配列で返されており、cuisine キーの値を使用数の多い順に並べた上位3つという具体的な回答が得られていないため。
- Observation: []

step 2: taginfo API /api/4/search/by_value で cuisine キーの値を count_all でソートし上位3件を取得
- 対象: cuisine / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: Critic 失敗（実行 2 回）
- Critic: 調査結果が空配列で返されており、上位3件の具体的な回答が得られていないため。
- Observation: []

step 3: taginfo API /api/4/search/by_key で key=cuisine を指定し、count_all でソートした上位3件の value を取得
- 対象: cuisine / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: 実行失敗（実行 3 回）、失敗: RuntimeError: Service taginfo HTTP 412: {"error":"number of results too large, use paging"}
- Critic: Generated Python execution failed

step 4: taginfo API /api/4/search/by_key で key=cuisine を指定し、limit=3 を指定して上位3件の value を取得
- 対象: cuisine / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: Critic 失敗（実行 3 回）
- Critic: 要求されたkey=cuisineのvalue（例: "japanese", "chinese"など）ではなく、nameやfixmeなどの別のkeyの値が返されているため、指定されたkeyのvalueが取得されていない。
- Observation: [{"name": "name", "relation_id": "Cuisine communautaire", "count": 131}, {"name": "name", "relation_id": "Cuisine", "count": 104}, {"name": "fixme", "relation_id": "Freeform tag `cuisine` used, to be doublechecked", "count": 98}, {"name": "name", "relation_id": "Cuisine centrale", "count": 54}, {"na

step 5: taginfo API /api/4/search/by_key で key=cuisine を指定し、limit=3 を指定して上位3件の value を取得
- 対象: cuisine / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: Critic 失敗（実行 2 回）
- Critic: 要求されたkey=cuisineのvalue（例: "japanese", "chinese"など）ではなく、nameやfixmeなどの無関係なタグの値が返されているため。
- Observation: [{"name": "name", "relation_id": "Cuisine communautaire", "count": 131}, {"name": "name", "relation_id": "Cuisine", "count": 104}, {"name": "fixme", "relation_id": "Freeform tag `cuisine` used, to be doublechecked", "count": 98}, {"name": "name", "relation_id": "Cuisine centrale", "count": 54}, {"na