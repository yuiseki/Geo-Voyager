# Skill library: 名前付き関数と合成（Voyager 型）

2026-10-10 に Skill library を作り直した。お嬢様の判断は「趣旨だけ維持して捨てて書き直す」。趣旨は、成功したコードを Skill として貯め、似た Intent で再利用すること。参考は MineDojo/Voyager の Skill library（[architecture_vision.md](architecture_vision.md) の 2.1）。

## 捨てたもの

- UUID ごとのディレクトリに置いた、トップレベルのスクリプトの Skill（`geo_voyager/skill.py`、`skills.py`、リポジトリの 6 本）。呼ぶことも組み合わせることもできなかった。
- Skill を 1 件選んで丸ごと再実行する Selector（`skill_selector.py`）。同じ Intent が来たときのキャッシュに近かった。
- DuckDB vss の index と embedding cache（`skill_vector_store.py`、`skill_embedding_cache.py`）。
- それらの単体テストと integration テスト（Selector、vector store、retriever、検索の評価、初期 Skill、生成した Skill の保存、Worker の Skill 実行、IntentExecutor の 3 経路）。過去の測定の文書（`skill_evaluation.md`、`skill_growth.md`、`vector_retrieval.md` など）は、当時の記録として残している。

## 新しい形

| 部品 | 場所 | 中身 |
|---|---|---|
| Skill | `geo_voyager/skill_function.py` | import とトップレベルの関数 1 つ（docstring つき）だけのコード。`parse_skill` が、名前、引数、説明（docstring）、中で呼んでいる名前を返す。トップレベルで何かを実行するコード、async、class、関数 2 つ、docstring の無い関数、`_` で始まる名前は拒否する |
| Library | `geo_voyager/skill_library.py` の `SkillLibrary` | 名前で保存し、同じ名前を保存し直すと前の版を残す（`<名前>/v1/code.py`、`description.txt`）。同じコードは新しい版にしない。保存されていない Skill や import していない名前を呼ぶ Skill は拒否する（呼ばれる側を先に保存する） |
| リンク | `link(program, library)`、`linked_skills` | プログラムが呼ぶ Skill を、呼び先の呼び先までたどり、呼ばれる側を先に、それぞれ 1 回だけ前に並べる。プログラムが同じ名前の関数を定義していればそちらを使う。循環は失敗、自分自身の再帰は可 |
| 検索 | `geo_voyager/skill_retriever.py` の `SkillRetriever` | 説明の embedding を版ごとに `embedding.json`（model と説明の SHA-256 つき）に保存し、Intent の文との cosine で上位 k 件を返す。新しい版や別のモデルのときだけ embedding し直す |
| 候補 | `geo_voyager/skill_candidate.py` | 生成コードは短いプログラムで、保存済みの Skill を名前で呼んでよく、新しい関数を 1 つまで定義してよい。`new_skill_code` は、そのうち import と関数だけを取り出す（保存する Skill）。`skill_shape_problems` は、関数が 2 つ以上、docstring が無い、関数が実行時変数（`intent_target`、`previous_observations`、`dataset_id`、`intent_text`）を引数でなく直接読む、を見つける |
| 生成 | `SkillCandidateGenerator.generate(intent, skills)` | 検索した Skill のコードを見せ、呼んでよいこと、定義をコピーしないこと、新しい処理は名前と引数と docstring を持つ関数 1 つにまとめること、実行時変数は呼ぶ行で引数として渡すことを指示する。`skill_shape_problems` に当たれば、理由を添えて最大 2 回作り直させ、残れば拒否する（id_type とローカル集計の検査と同じ仕組み） |
| 実行 | `Worker.execute_candidate(intent, candidate, library)` | 実行の前にリンクする。実行時変数とリンクした Skill のぶん行番号がずれるので、失敗の行番号は書かれたプログラムの行に直して返す |
| 流れ | `IntentExecutor` | 検索、生成（Skill を渡す）、リンクして実行、失敗なら最大 2 回 repair、Critic、（任意で semantic repair）、Critic が成功なら新しい関数を保存。`IntentExecution` は `retrieved_skills`、`called_skills`、`learned_skill`（`名前@v版`）、保存できなかった理由（`note`）を持つ |

リポジトリの `skill_library/` には、v0.1.0 の最初の 6 Skill と同じ目的の関数を、引数を取り値を返す形で書き直して置いた: `most_populous_area`、`least_populous_area`、`top_areas_by_population`、`total_population`、`count_station_records`、`northernmost_station`。

## 確かめたこと

- 単体テスト 821 件（Skill の検査、Library の版と拒否、リンクの順と重複と循環、検索の順位とキャッシュ、候補の取り出しと形の検査、Generator の作り直し、IntentExecutor の保存と repair、6 Skill の動作）。
- 実 Docker（`integration/test_skill_linking.py`）: `most_populous_area(dataset_id, area="東京都23区")` を呼ぶプログラムが、Skill をリンクされて実 Worker で動き、世田谷区と 943,664 を返す。プログラムの 2 行目で起きた失敗は、`<candidate>` の 2 行目として返る。

## まだ確かめていないこと

- ローカル LLM が、見せた Skill を実際に呼ぶか、関数 1 つの形で書けるか。`integration/test_service_learning.py`（1 回目で関数を保存し、2 回目でそれを呼ぶ）は書き換えたが、まだ流していない。
- runtime repair のプロンプトには、呼んでいる Skill の定義を見せていない。repair が Skill の中の失敗を直そうとして、Skill を作り直す可能性がある。
- Goal をまたいで Skill を持ち越す測り方（今の `bench/run_adaptive.py` と `bench/run_goals.py` は、実行ごとに空の Library から始める）。

## 実 LLM での 1 回目（2026-10-10）

`integration/test_service_learning.py` の 3 ケース（Taginfo と Overpass で火山、Nominatim で上野駅、YuisekinGeoSPARQL で台東区に接する区）を 1 回ずつ流した。各ケースは、空の Library で同じ Intent を 2 回実行し、1 回目で関数を Skill として保存し、2 回目でそれを呼ぶことを期待する。3 ケースとも失敗した。記録は [evidence/skill_library_llm1/](evidence/skill_library_llm1/)。

| ケース | 1 回目 | 2 回目 |
|---|---|---|
| taginfo_overpass | 成功。関数 `discover_volcanoes_in_japan` を Skill として保存 | 検索でその Skill が上位に来て Generator に見せたが、呼ばずに、関数の無いトップレベルのコードを書き直した。実行と Critic は成功 |
| nominatim | 成功。ただし関数を書かず、トップレベルのコードだけだったので、保存する Skill が無い | （1 回目で失敗の判定のため実行せず） |
| geosparql | 成功。関数 `query_touching_wards` を保存（結果を返さず中で print する関数） | 説明には「query_touching_wards 関数を用いて」と書いたが、コードでは関数の定義をそのまま書き写した。さらに「コード:」のコロンを落とし、形式の検査で失敗した |

分かったこと:

- ローカル LLM は、見せた Skill を呼ばない。書き写すか、無視して書き直す。3 ケースのどれでも、保存した Skill を呼んだ実行は無かった。
- 関数にまとめるかどうかを LLM に任せる（今の指示は「必要なら」）と、関数を書かないことがある（nominatim）。そのとき何も保存されない。
- 保存された関数が、値を返さず中で print する形になることがある（geosparql）。呼ぶ側が結果を受け取れないので、部品として使いにくい。

次に試すこと（決定的にできるもの）:

1. 保存済みの Skill と同じ名前の関数を定義し、中身が保存済みの版と同じなら、その定義を取り除いて保存済みの Skill を呼ばせる（書き写しを呼び出しに戻す）。中身が違えば、Voyager と同じく新しい版として扱う。
2. 保存済みの Skill を呼ばないコードには、新しい関数を 1 つ必ず定義させる（Voyager は毎回関数を書かせる）。トップレベルだけのコードは、理由を添えて作り直させる。
3. 関数は値を返すこと（print だけで終わらない）を、指示と検査に入れる。
