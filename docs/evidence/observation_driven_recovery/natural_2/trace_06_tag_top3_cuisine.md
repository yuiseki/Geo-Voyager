### tag_top3_cuisine (最大 8 step)
Goal: Taginfo で cuisine キーの値を使用数の多い順に並べ、上位3つの値を示す。

stop: done / Goal の Critic: 成功（cuisine キーの使用数上位3つの値（pizza, burger, coffee_shop）が提示されているため。） / oracle との一致: True

step 1: Taginfoサービスでcuisineキーの値を使用数の多い順に並べ、上位3つの値を取得
- 対象: なし / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: 成功（実行 2 回）
- Critic: cuisineキーの使用数上位3つの値（pizza, burger, coffee_shop）が取得されているため
- Observation: [{"name": "pizza", "relation_id": 132565}, {"name": "burger", "relation_id": 110797}, {"name": "coffee_shop", "relation_id": 101080}]
- この step で初めて判明した対象: [{'name': 'pizza', 'relation_id': 132565}, {'name': 'burger', 'relation_id': 110797}, {'name': 'coffee_shop', 'relation_id': 101080}]
- 学習した Skill: bbf48570