### tag_top3_cuisine (最大 8 step)
Goal: Taginfo で cuisine キーの値を使用数の多い順に並べ、上位3つの値を示す。

stop: max_steps / Goal の Critic: 失敗（Goal を完了できなかった: max_steps） / oracle との一致: False

step 1: Taginfoでcuisineキーの値を使用数の多い順に並べ、上位3つの値を示す。
- 対象: cuisine / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: Critic 失敗（実行 2 回）
- Critic: 上位3つの値が空配列で返されており、要求された調査結果が得られていないため。
- Observation: {"name": "cuisine", "cuisine_values": []}

step 2: Taginfo API /api/4/keys/cuisine/values を使用して、cuisine キーに関連する値を count 順にソートし、上位3件の value と count を取得する。
- 対象: cuisine / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: 実行失敗（実行 3 回）、失敗: RuntimeError: Service taginfo HTTP 404: <!DOCTYPE html>
- Critic: Generated Python execution failed

step 3: taginfo API /api/4/keys/cuisine を使用して、cuisine キーの存在確認と詳細情報を取得する。
- 対象: cuisine / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: 実行失敗（実行 3 回）、失敗: RuntimeError: Service taginfo HTTP 412: {"error":"number of results too large, use paging"}
- Critic: Generated Python execution failed

step 4: taginfo API /api/4/keys/cuisine を limit パラメータ付きで呼び出し、cuisine キーの値を count 順にソートした上位3件の value と count を取得する。
- 対象: cuisine / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: 実行失敗（実行 3 回）、失敗: RuntimeError: Service taginfo HTTP 412: {"error":"number of results too large, use paging"}
- Critic: Generated Python execution failed

step 5: taginfo API /api/4/keys/cuisine に limit=3, sort=count パラメータを指定して、cuisine キーの値を count 順にソートした上位3件の value と count を取得する。
- 対象: cuisine / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: 実行失敗（実行 3 回）、失敗: RuntimeError: Service taginfo HTTP 404: <!DOCTYPE html>
- Critic: Generated Python execution failed

step 6: taginfo API /api/4/keys/cuisine に limit=3, sort=count パラメータを指定して、cuisine キーの値を count 順にソートした上位3件の value と count を取得する。
- 対象: cuisine / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: Critic 失敗（実行 2 回）
- Critic: 上位3件以外の多数のデータが含まれており、limit=3の要件を満たしていないため。
- Observation: [{"value": "Cuisine communautaire", "count": 131}, {"value": "Cuisine", "count": 104}, {"value": "Freeform tag `cuisine` used, to be doublechecked", "count": 98}, {"value": "Cuisine centrale", "count": 54}, {"value": "Cuisine Centrale", "count": 51}, {"value": "Cuisine Plus", "count": 38}, {"value":

step 7: taginfo API /api/4/keys/cuisine/values に limit=3, sort=count パラメータを指定して、cuisine キーの値を count 順にソートした上位3件の value と count を取得する。
- 対象: cuisine / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: Critic 失敗（実行 3 回）
- Critic: 要求されたcuisineキーの値ではなく、nameやrelation_idなどの他のキーの値が取得されているため。
- Observation: [{"name": "name", "relation_id": "Cuisine communautaire", "count": 131}, {"name": "name", "relation_id": "Cuisine", "count": 104}, {"name": "fixme", "relation_id": "Freeform tag `cuisine` used, to be doublechecked", "count": 98}, {"name": "name", "relation_id": "Cuisine centrale", "count": 54}, {"na

step 8: taginfo API /api/4/keys/cuisine/values に limit=3, sort=count パラメータを指定して、cuisine キーの値を count 順にソートした上位3件の value と count を取得する。
- 対象: cuisine / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: 実行失敗（実行 3 回）、失敗: RuntimeError: Service taginfo HTTP 404: <!DOCTYPE html>
- Critic: Generated Python execution failed