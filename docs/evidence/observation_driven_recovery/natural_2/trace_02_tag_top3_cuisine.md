### tag_top3_cuisine (最大 8 step)
Goal: Taginfo で cuisine キーの値を使用数の多い順に並べ、上位3つの値を示す。

stop: repeated_intent / Goal の Critic: 失敗（Goal を完了できなかった: repeated_intent） / oracle との一致: False

step 1: Taginfo で cuisine キーの値を使用数の多い順に並べ、上位3つの値を示す
- 対象: なし / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: 実行失敗（実行 3 回）、失敗: RuntimeError: Service taginfo HTTP 412: {"error":"number of results too large, use paging"}
- Critic: Generated Python execution failed

step 2: cuisine キーの値を使用数の多い順に並べ、上位3つの値を示す
- 対象: cuisine / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: Critic 失敗（実行 2 回）
- Critic: 調査結果が空配列で返されており、cuisine キーの値を使用数の多い順に並べた上位3つが示されていないため。
- Observation: []

step 3: taginfo API /api/4/keys/cuisine/values で limit=3, sort_count=desc を指定し、cuisine キーの値を件数降順で上位3件取得
- 対象: cuisine / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: 実行失敗（実行 3 回）、失敗: ValueError: No cuisine values found
- Critic: Generated Python execution failed

step 4: taginfo API /api/4/keys/cuisine で cuisine キーの詳細情報を取得し、values フィールドから上位3つの値を取得
- 対象: cuisine / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: Critic 失敗（実行 3 回）
- Critic: 上位3つの値という具体的な回答が得られていない
- Observation: []

step 5: taginfo API /api/4/keys/cuisine で cuisine キーの詳細情報を取得し、values フィールドから上位3つの値を取得
- 対象: cuisine / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: 実行失敗（実行 3 回）、失敗: RuntimeError: Service taginfo HTTP 412: {"error":"number of results too large, use paging"}
- Critic: Generated Python execution failed