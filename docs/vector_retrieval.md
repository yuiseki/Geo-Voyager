# Skill 検索の派生 cache / DuckDB vss 検証

DuckDB 1.5.6、granite-embedding 384次元。初期6 Skill を一時 Library にコピーし、実 embedding / LLM / Docker / Gateway / Dataset を使いました。code.py / description.txt が原本で、cache と DB は Git 管理しません。

| sync | embedding した description 件数 |
|---|---:|
| 初回 | 6 |
| 2回目 | 0 |
| DB なしから既存 cache で再構築 | 0 |

一時ファイルを削除しないため旧DBを別名に退避し、同じパスで空のDBから再構築しました。再構築前後の検索UUID順は一致しました。永続DBの EXPLAIN で `HNSW_INDEX_SCAN` / `skill_embedding_hnsw` を確認しました。

## Cache の実例

以下は実 cache の metadata と先頭6要素です。全384要素の embedding cache をこのドキュメントへ複製していません。

```json
{
  "format_version": 1,
  "model": "granite-embedding",
  "dimensions": 384,
  "description_sha256": "2e4fd6dac6c33f433694b69dadbf856293dabc69ae67406e0a26920980a98022",
  "embedding": [
    0.011706363409757614,
    -0.017932021990418434,
    0.013552563264966011,
    0.003877760376781225,
    0.05887620896100998,
    -0.022782795131206512
  ]
}
```

## 既存6 Intent の評価

初回実行の Retriever recall@4 は6/6、変更していない Selector の正答は5/6でした。人口最大 Intent で上位5区 Skill を選ぶ誤選択が1件ありました。Selector の精度をテストで隠さず、[全順位・similarity・選択結果](vector_retrieval_evaluation.json)に保存しました。今回の変更では Retriever recall@4 を必須とし、Selector の完全正答を要件に加えていません。

| Intent | 正解 Skill の順位 | 正解top-4 | 初回Selector正答 |
|---|---:|---|---|
| 東京都23区で人口が最も多い区と人口を求める | 4 | True | False |
| 東京都23区で人口が最も少ない区と人口を求める | 1 | True | True |
| 東京都23区の人口合計を求める | 1 | True | True |
| 東京都23区で人口が多い上位5区を求める | 1 | True | True |
| 駅データに収録されている駅の総数を求める | 1 | True | True |
| 駅データに収録されている最北端の駅を求める | 1 | True | True |

## 学習 → sync → 再利用

- initial_learning: 東京都23区の平均人口を求める。selected=None、learned=c6e40a0a-1ff4-42af-b098-b1e0cb3f02dc、Critic=True、Library=7。
- learned_skill_reuse: 東京都23区の平均人口を求める。selected=c6e40a0a-1ff4-42af-b098-b1e0cb3f02dc、learned=None、Critic=True、Library=7。
- learned_skill_reuse: 東京都23区について、1区あたりの平均人口を計算して。selected=c6e40a0a-1ff4-42af-b098-b1e0cb3f02dc、learned=None、Critic=True、Library=7。

同一・言い換え Intent で学習 UUID はtop-4に入り、Generator / 保存回数は1回のままでした。新規 Skill は次回 retrieval の sync で index に追加されました。平均人口は423185.9130434783人。リポジトリの初期 Skill は6件のままです。

## テスト結果

unit は222件成功。integration 初回は15件成功し、6 Intent 評価だけが追加した Selector 完全正答の assertion で失敗しました。今回対象の Retriever recall@4=6/6 を必須にし、変更対象外の Selector 精度は従来どおり報告するテストへ修正。その評価テストの再実行は成功し、Retriever=6/6、Selector=6/6でした。これにより現コードの全16 integration の成功を確認しました。初回の Selector 誤選択は上記記録に残しています。
