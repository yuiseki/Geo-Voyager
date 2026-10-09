### tag_top3_cuisine (最大 8 step)
Goal: Taginfo で cuisine キーの値を使用数の多い順に並べ、上位3つの値を示す。

stop: planner_failure / Goal の Critic: 失敗（Goal を完了できなかった: planner_failure（ValueError: Intent の調査項目に API の詳細が書かれている: key="cuisine"。何を調べるかだけを書き、API のパスやパラメータは書かない。サービスの呼び方は実行側が決める）） / oracle との一致: False

計画の失敗（step 0 の後）: ValueError: Plan must start with 調査項目:
- Planner の応答: 调查项目: Taginfo API /api/4/key/values で key="cuisine" の値を sortname=count_all, sortorder=desc, rp=3 で取得し、上位3つの値と件数を確認する。 / 利用データセット: [] / 利用サービス: /   - taginfo

計画の失敗（step 0 の後）: ValueError: Intent の調査項目に API の詳細が書かれている: key="cuisine"。何を調べるかだけを書き、API のパスやパラメータは書かない。サービスの呼び方は実行側が決める
- Planner の応答: 調査項目: Taginfo で key="cuisine" の値を使用数の多い順に並べ、上位3つの値を取得する。 / 利用データセット: [] / 利用サービス: /   - taginfo

step 1: Taginfo で cuisine キーの値を使用数の多い順に並べ、上位3つの値を示す。
- 対象: なし / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: Critic 失敗（実行 3 回）
- Critic: 使用数が0で並べ替えられておらず、上位3つの値が示されていないため
- Observation: {"name": "cuisine_values", "relation_id": "cuisine", "count": 3, "values": [{"name": "pizza", "relation_id": "cuisine", "count": 0}, {"name": "burger", "relation_id": "cuisine", "count": 0}, {"name": "coffee_shop", "relation_id": "cuisine", "count": 0}]}

計画の失敗（step 1 の後）: ValueError: Intent の調査項目に API の詳細が書かれている: key="cuisine"。何を調べるかだけを書き、API のパスやパラメータは書かない。サービスの呼び方は実行側が決める
- Planner の応答: 調査項目: Taginfo で key="cuisine" の値を使用数の多い順に並べ、上位3つの値を取得する。 / 利用データセット: [] / 利用サービス: /   - taginfo