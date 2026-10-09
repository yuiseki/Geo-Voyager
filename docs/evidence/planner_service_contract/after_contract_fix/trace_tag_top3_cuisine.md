### tag_top3_cuisine (最大 8 step)
Goal: Taginfo で cuisine キーの値を使用数の多い順に並べ、上位3つの値を示す。

stop: done / Goal の Critic: 成功（Intentで要求されたcuisineキーの値を使用数の多い順に並べた上位3つがObservationで提供されているため。） / oracle との一致: True

step 1: Taginfo で cuisine キーの値を使用数の多い順に並べ、上位3つの値を示す。
- 対象: なし / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: Critic 失敗（実行 1 回）
- Critic: 上位3つの値が提示されておらず、1つの値のみが報告されているため、Intentの要求を満たしていない。
- Observation: {"value": "coffee_shop", "count": 101080}

step 2: cuisine キーの値を使用数の多い順に並べ、上位3つの値を示す。
- 対象: なし / リソース: taginfo
- この step の前に判明していた対象: なし
- 結果: 成功（実行 1 回）
- Critic: 指定された上位3つのcuisine値とその使用数が降順で提示されているため、Intentの要求を満たしている。
- Observation: [{"value": "pizza", "count": 132565}, {"value": "burger", "count": 110797}, {"value": "coffee_shop", "count": 101080}]
- 学習した Skill: 791d431f