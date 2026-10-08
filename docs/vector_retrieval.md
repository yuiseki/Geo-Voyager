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

## 現在の同期タイミング

上記は sync-per-query 時点の検証記録です。現在は SkillRetriever constructor で startup full sync を1回行い、通常 retrieval は query embedding → HNSW search → SkillLibrary.get だけです。学習成功後は SkillLibrary.add → retriever.upsert → description cache 取得/生成 → store.upsert で1件だけ反映します。

既存vectorの更新後に永続HNSWの古い行が候補に残り検索結果が不足するケースを回帰テストで確認したため、既存UUIDの更新・削除がある場合だけindexを再作成します。新UUIDの学習はincremental INSERTのみです。

## startup sync + incremental upsert の実検証

unit 227件、integration全16件成功。最後のschema初期化変更後にも実persistent DBのintegrationを再確認し成功しました。

起動時の full sync は1回、初期6 Skill のdescription embeddingは6件。その後の正常再利用2件・未知平均人口の学習・同一Intent再利用・言い換え再利用の5 queryでは、query embedding 5件と学習description 1件だけを呼びました。full syncは1回のまま、upsertは1回。

平均人口Skill `2759d3cd-f0a4-416b-99d0-0e29c6234dd9` は保存直後にindexへ入り、次の同一・言い換えIntentで選択されました。平均人口423185.9130434783人、Critic成功、生成・保存回数は1回のままです。意図的な誤選択からのfallback学習ではfull syncは1回のまま、upsertだけ2回になりました。

通常 retrieval で Library.all / sync / cache.get / schema作成を呼ばないことと、Critic失敗・正常既存Skill再利用ではupsertを呼ばないこともunit testで確認しました。
