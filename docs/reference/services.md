# 登録した地理サービス

## 登録

`Service(id, description, base_url, protocol)` と `ServiceGraph.register/get/all` でサービスを登録する。
`load_service_graph()`（`geo_voyager/services.py`）は、overpass、nominatim、valhalla、taginfo の正確な HTTPS origin と、
検証用の YuisekinGeoSPARQL `http://geosparql:3030` を登録する。未知の ID は `KeyError`。
`*.yuiseki.net` のワイルドカードは許可しない。HTTP の User-Agent は
`Geo-Voyager/0.1.0 (+https://github.com/yuiseki/Geo-Voyager)`。
この登録は探索のためのメタデータで、Worker からの通信の許可は Gateway が別に制御する。

## Service Gateway

Service Gateway（`geo_voyager/service_gateway.py`）は `GET/POST /services/{service_id}/{path}?query` を提供する。

- 登録 origin を service_id から解決し、protocol ごとの read-only な API のパスとメソッドだけを許可する。
  - Nominatim と Taginfo は GET。
  - Overpass の interpreter、Valhalla の route と locate、GeoSPARQL の query は GET と POST。
- 次のものは拒否する。
  - 任意の URL、URL の上書き、パスのトラバーサル。
  - PUT、PATCH、DELETE。
  - 管理用のエンドポイント、SPARQL update のメディアタイプ。
- User-Agent は Gateway 側で固定し、Worker の Host や Authorization などの header は転送しない。
- redirect は追跡せず、Location も転送しない。
- 上限は、upstream の timeout 15 秒、request body 64 KiB、response 4 MiB。
- 既存の Dataset の GET と HEAD も、同じ handler で扱える。
- 登録サービスの upstream が HTTP エラーを返したときは、長さを制限し秘密を伏せた本文（8 KiB まで）だけを Worker に返す。生成コードの repair が、クエリの誤りを読んで直せるようにするため。

## call_service

Worker の image は、汎用の Primitive `call_service(service_id, *, path="", params=None, body=None, content_type=None) -> str` を持つ。

- 登録 ID を確かめて、Gateway にだけ HTTP リクエストを送る。body が無ければ GET、あれば POST。
- GET のパラメータの空白は `%20` で送る（`+` だと Valhalla が JSON を読めない）。
- Overpass、経路、OSM などのクエリの意味は Primitive に埋め込まない。クエリ言語や API のパラメータはモデルが書く。
- `Intent(text, service_ids=(...))` は Dataset なしで実行でき、Dataset と併用もできる。Dataset は複数でも構わない（空間結合のため）。
- Worker は実行だけを行い、Critic と保存は Executor が担当する。

実 Docker で、Gateway 経由の Taginfo への問い合わせが成功し、4 つの公開サービスへの直接の TCP 接続ができないことを確かめた。
GeoSPARQL への直接接続の拒否と、SPARQL `SERVICE` の無効化も、固定したグラフを起動する E2E で確かめた。

## サービスの説明と生成

- `SkillCandidateGenerator` は、Intent が宣言した登録サービスの ID、protocol、説明を、`call_service()` と一緒にプロンプトに書く。
  - Intent がサービスを宣言していなければ、登録した 5 つすべてを見せる。
  - origin の URL は Gateway が解決し、生成コードには見せない。
- サービスの説明には、API とスキーマの情報と、抽象的な構文だけを書く。具体的な地理のクエリは書かない。
  - Taginfo の `data` 配列や、SPARQL の `results/bindings/value` の形も書く。Primitive にサービスごとの解析を足さずに、生の応答をモデルが読めるようにするため。
- 説明には、自前のサービスに実際に問い合わせて確かめたことだけを書く。integration の契約テストで保つ。
  - Taginfo（`key/values` の page と rp、`tag/stats`、`search/by_value` は部分一致）は `integration/test_taginfo_contract.py`。
  - Valhalla（POST、`costing` 必須、`trip.summary.length` と `time`）は `integration/test_valhalla_contract.py`。
- 生成の LLM の設定（`skill_candidate_generator.py`、`skill_candidate_repairer.py`、`critic.py`）。
  - サービスを使う Intent の生成と repair: `temperature=0.2`、`chat_template_kwargs.enable_thinking=true`、`reasoning_budget_tokens=1024`、`max_tokens=3072`。
    - system メッセージで、説明とコードの決まった形を求め、最初の「説明:」だけを assistant の先頭に入れておく。形の違う応答は拒否する。
  - Dataset だけの Intent の生成: サーバーの既定の temperature、`max_tokens=8192`。
  - Critic: `temperature=0`。
  - これらの設定は、生成コードが成功することを保証しない。モデルや Kubernetes の設定は変えない。

## 実行の失敗と repair

- 生成した Python の構文エラーや実行時エラーは、Worker が `ExecutionFailure` として返す。
  - コンテナの wrapper は、このエラーのために終了コード 73 を予約している。
  - Docker の起動やデーモンの失敗は、例外のまま外へ出る。
  - stdout と stderr は、それぞれ 8 KiB まで。コンテナの環境変数の値は伏せ、診断から秘密や環境変数のダンプの行を除く。
- `IntentExecutor` は、生成コードの失敗を `SkillCandidateRepairer` で最大 2 回直す（実行は合わせて 3 回まで）。
  - repair が受け取るのは、元の Intent、登録リソースと Primitive の契約、Candidate、制限した診断。
  - repair は、元の再利用できる操作の説明を保ち、失敗の原因を直す。答えの定数や新しいリソースは持ち込まない。
  - Critic は、実行できた Observation だけを判定する。
  - 回数が尽きたら `failure` と失敗の critique を返し、Candidate を Skill として保存しない。
  - インフラの例外は例外のまま外へ出る。
- `IntentExecution.attempts` は、すべての実行（選んだ Skill、最初の Candidate、repair した Candidate）を順に、元のコード、Observation、失敗とともに残す。
  - `critique` は、採用した最終の結果についての判定。失敗した実行には Critic の判定が無い。

## 実サービスを使う integration

サービスの学習と再利用（`integration/test_service_learning.py`）:

```bash
docker build -t geo-voyager-geosparql:jena-6.2.0 ../YuisekinGeoSPARQL/fuseki
GEO_VOYAGER_EMBEDDING_BASE_URL=http://localhost:30194 \
GEO_VOYAGER_EMBEDDING_MODEL=embeddinggemma \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  integration/test_service_learning.py -q -s -W error --import-mode=importlib \
  --basetemp=/tmp/geo-service-learning-$(cat /proc/sys/kernel/random/uuid)
```

- シナリオごとに、空の一時 Library を使う。Critic が成功としたら、新しい関数を名前付きの Skill として保存する。
  - 同じ Intent をもう一度検索し、生成コードが保存した Skill を書き直さずに呼ぶことを期待する。
  - 2026-10-10 に名前付き関数の Skill に合わせて書き換えたが、その後は実行していない。
- 生成するリクエストは登録サービスだけを使う。タグの答えや対象の ID はプロンプトに渡さない。
- Critic は Intent が答えられたかだけを判定する。足りない答えを外部の知識で補うことは、プロンプトで禁じている。
- GeoSPARQL のテストは、隣のリポジトリにある、manifest に載っていて SHA-256 を確かめた固定の TTL ファイルだけを読む。
  - サーバーは、Gateway とだけ共有する隔離した internal network で動く。Gateway は、Worker の internal network と external network にもつながる。
  - GeoSPARQL から Internet へは出られず、SPARQL `SERVICE` は Fuseki の context 設定で無効にしている。
  - データの bind mount は読み取り専用で、テスト用の origin server だけが持つ。Worker と Gateway には host のマウントが無い。
  - 作ったコンテナと network は `finally` で削除する。
- 記録: [2026-10-08_service_learning.md](../reports/2026-10-08_service_learning.md)（3 本の実サービスの学習と再利用の結果、生成した Skill のコードと説明）。

複合 Goal（ハンバーガー、`integration/test_burger_goal.py`）:

```bash
GEO_VOYAGER_EMBEDDING_BASE_URL=http://localhost:30194 \
GEO_VOYAGER_EMBEDDING_MODEL=embeddinggemma \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest \
  integration/test_burger_goal.py -q -s -W error --import-mode=importlib \
  --basetemp=/tmp/geo-burger-goal-$(cat /proc/sys/kernel/random/uuid)
```

- 空の一時 Library を使い、最初の Candidate にわざと構文エラーを入れる。そのうえで、実 LLM の repair、実サービスへのリクエスト、Critic を通す。
- 学習した測定のコードを、後の対象で再利用する。
- Goal が終わったあと、23 区の測定を区ごとに Overpass へ問い合わせ直して、独立に確かめる。この確かめのコードは、生成や repair のプロンプトにも Skill Library にも入らない。テストに決まった答えは書かない。
- 1 本の順番の計画で、生成した Candidate ごとに repair は最大 2 回。Critic は答えられたかを判定するだけで、数値の独立の確かめの代わりにはならない。LLM の生成がいつも成功する保証は無い。
- 記録: [2026-10-09_burger_goal_learning.md](../reports/2026-10-09_burger_goal_learning.md)（全 25 Intent、失敗したコードと stderr、repair の差分、再利用、23 区の集計）。

## 参考

[Taginfo API](https://taginfo.openstreetmap.org/taginfo/apidoc)、
[Overpass QL](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL)、
[Fuseki context](https://jena.apache.org/documentation/fuseki2/fuseki-configuration.html)、
[SPARQL JSON results](https://www.w3.org/TR/sparql11-results-json/)、
[llama.cpp request options](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)、
[reasoning-budget request handling](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/server-common.cpp)
