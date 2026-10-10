# 構想: 3 つのグラフと Skill library

2026-10-10。お嬢様の構想と、それに関わる判断、参考にしている 2 つのエージェント（MineDojo/Voyager と ARTEX）から得た示唆を記録する。設計メモで、まだ実装していない。今の実装との対応は 3 節にある。

## 1. 構想

Geo-Voyager の究極のゴールは、study-geoai-algo-py（Claude Code が台東区と東京 23 区の実データで GeoAI のアルゴリズムを一通り動かした記録）でやっているようなデータ分析、検定、可視化、最適化を、ローカル LLM にやらせることである（[analysis_sandbox_design.md](analysis_sandbox_design.md)）。そのための資産を、3 つのグラフと 1 つのライブラリに分けて持つ。

| 資産 | 中身 | 出どころ | 確からしさ |
|---|---|---|---|
| Dataset Graph | 利用可能なデータ資産（Dataset、Service、固定した分析データ） | 人が登録する | 与えられたもの |
| World Graph | 探索した結果わかった、世界についての知識（対象、その ID、属性、関係） | エージェントの観測と推論 | エージェントが得たもの。出所つき |
| Exploration Graph | 探索の過程（何を試し、何が起き、どこから別の方法に分かれたか） | エージェントの実行の記録 | 起きたことの記録 |
| Skill library | やり方の知識（再利用できるコード） | Critic が成功とした実行 | 実行で確かめたもの |

### How-to Graph（2026-10-10 に追加）

お嬢様の構想に、もう 1 つの資産がある。Autonomous-GeoAI（`/Workspaces/repos/__yuiseki/_research/Autonomous-GeoAI`）の `.agents/skills` で、Knowledge Graph または How-to Graph と呼ぶべきもの。Skill library がモデル自身の獲得したスキルであるのに対して、How-to Graph は、人間が教科書やレシピや作業マニュアルを読むように、モデルが読む与えられた手順の知識である。Agent Skills の形式（name と description、手順、必要なときに読む references、テスト済みの scripts）で、分析の段階ごとに 24 本ある（データを知る、単位を決めてそろえる、予測して評価を疑う、構造を探す、ネットワークと最適化、残す）。study-geoai-algo-py で得た教訓を一般化したもの。

3 つのリポジトリは繋がっている。Geo-Voyager v0.1.0 の Control Primitives は、もともと study-geoai から持ち込んだもの。

資産を、与えられたものと獲得したものに分けると、次の対になる。

| | 与えられたもの | 獲得したもの |
|---|---|---|
| 何があるか（宣言的な知識） | Dataset Graph（データ資産。oracle の YuisekinGeoSPARQL もここ） | World Graph（探索でわかった世界の知識） |
| どうやるか（手続きの知識） | How-to Graph（Autonomous-GeoAI の手順書） | Skill library（成功した関数） |
| 過程 | | Exploration Graph（探索の記録） |

Voyager にも近い仕組みがある。curriculum agent は、次のタスクを決める前に、Minecraft についての質問を自分で立て、その答え（知識）を集めてから決める（`voyager/prompts/curriculum_qa_step1_ask_questions.txt`、`curriculum_qa_step2_answer_questions.txt`）。How-to Graph は、その知識を人が書いた手順として与えるものに当たる。

### 決まっていること

- YuisekinGeoSPARQL は、信頼できるデータセットで構築した oracle である。モデルの観測や推論の結果を、ここに混ぜない。
- World Graph を GeoSPARQL のような形（RDF の地理グラフ）で保管する方向には賛成。ただし、どこまで本当に可能かは、やってみないと分からない。
- Skill library は、3 つのグラフとは別の資産として持つ。世界の知識ではなく、やり方の知識だから。
- Skill library は MineDojo/Voyager の Skill library を強く参考にする。
- Geo-Voyager は study-geoai-algo-py から独立させる（コードもデータも使わない。README の数字を oracle の出典にするだけ）。

## 2. 参考にしているエージェント

### 2.1 MineDojo/Voyager の Skill library

<https://github.com/MineDojo/Voyager>（コミット `55e45a8`、2023-07-27）の `voyager/agents/skill.py`、`voyager/prompts/`、`skill_library/trial1`（57 Skill）を読んだ。

- Skill は、名前の付いた関数 1 つ（例: `async function craftIronPickaxe(bot)`）。関数の中から、他の Skill（`mineBlock`、`smeltItem`、`craftItem`）を名前で呼ぶ。
- 実行時には、全 Skill のコードと Control Primitives をまとめて読み込む（`SkillManager.programs`）。どの Skill もどの Skill でも呼べるので、小さな Skill の上に大きな Skill が積み上がる（合成）。
- 保存は、Critic が成功と判定したときだけ。同じ名前を保存し直すと `V2` のように版を分ける。
- 説明文は、コードから LLM が 6 文以内で書く（関数名と補助関数には触れない）。説明文の embedding をベクトル DB に入れる。
- 検索の問い合わせは、タスクの文ではなく、curriculum が作ったタスクの文脈。上位 5 件のコードを、新しいコードを書くプロンプトに「役に立つプログラム」として見せる。
- 書き方の指示: 既存のプログラムをできるだけ再利用する。関数は、後でより複雑な関数の部品になるよう汎用的に書く。状態（持ち物）を仮定せず、足りなければ先に用意する。

### 2.2 ARTEX

piyolog の記事（<https://piyolog.hatenadiary.jp/entry/2026/10/06/121225>、2026-10-06）で知った、中国で開発された自律型のエージェント。用途はセキュリティだが、Geo-Voyager ではセキュリティの用途には一切触れず、自律探索エージェントの作り方としてだけ参考にする。リポジトリは 2026-10-09 の時点で閲覧できないので、記事の記述だけに基づく。

- Planner が次に実行する作業（意図）を生成し、Worker が意図を 1 件ずつ実行して結果を書き戻す。
- 全タスクで共有する資産と、タスクごとの探索の進み具合を、2 つのグラフ（資産グラフ、探索グラフ）で管理する。
- ツールの呼び出しを、規則で許可、拒否、確認のいずれかにする承認ゲート。規則に当てはまらないときはモデルが判定する。
- 通信を記録型のプロキシ経由にし、エージェントがその記録を検索して手がかりを探す。
- 実行中のタスクに、人が対話で介入できる。

## 3. 今の実装との対応

| 構想 | 今あるもの | 足りないもの |
|---|---|---|
| Dataset Graph | `DatasetGraph`（5 Dataset の静的なカタログ、辺なし）、`ServiceGraph`（5 サービス）、`analysis_data.py`（分析用の固定データ 2 ファイル） | 3 つが別々。辺（派生関係、同じ実体を指す列、どの Service がどの Dataset から作られたか）が無い |
| World Graph | 実質的に無い。`TargetRef`（例: 渋谷区 = `relation_id` 1759477）は Goal の履歴（`GoalHistory.targets()`）の中にしかなく、Goal が終わると消える | Goal をまたいで残る知識。各事実の出所（どの Goal のどの step の Observation か、どのデータの版か、Critic の判定） |
| Exploration Graph | `GoalHistory`（Goal ごとの追記型の列。step、計画の失敗、最終判定の失敗）、`bench/run_adaptive.py` の `results.jsonl` と `trace.md` | 枝分かれ。今は 1 本の列なので、失敗した枝と、そこから分かれた別の方法の関係が残らない。Goal をまたいだ探索の記録 |
| Skill library | `SkillLibrary`（UUID ごとのディレクトリにコードと説明）、`SkillRetriever`（embedding で検索）、`SkillSelector`（候補から 1 件を選ぶ） | 合成と版。下の 4.1 |

## 4. 示唆と、試したいこと

### 4.1 Skill library を Voyager の形に近づける

今の Geo-Voyager の Skill は、トップレベルのスクリプトで、検索した候補から Selector が 1 件を選び、丸ごとそのまま実行する。Generator には既存の Skill を見せていない。同じ Intent が来たときのキャッシュに近い。

Voyager との最大の差は合成である。study-geoai のような分析では、「固定データを読む」「町丁目の表を作る」「空間ブロックで交差検証する」といった部品の組み合わせが効くはずなので、次を試したい。

- Skill を、名前と引数を持つ関数にする（今の実行時変数 `intent_target` などは、引数として渡す）。
- 検索した上位の Skill のコードを Generator のプロンプトに見せ、呼んでよいことにする。実行時には、呼ばれた Skill のコードを一緒に読み込む。
- 同じ名前の Skill は版で管理する。

#### 実装（2026-10-10）

同じ日に、今の部品を捨てて名前付き関数の形に作り直し、IntentExecutor までつないだ。詳細は [skill_library.md](skill_library.md)。以下は、その前に作った土台の記録。

#### 土台の実装（2026-10-10）

Skill を名前付きの関数にする土台を、今の部品を変えずに横に作った（単体テスト 870 件）。Generator、IntentExecutor、Worker にはまだつないでいない。

- `geo_voyager/skill_function.py`: `parse_skill(code)` は、コードが import とトップレベルの関数 1 つだけでできているか、名前が公開の識別子か、docstring（Skill の説明）があるかを確かめ、名前、引数、説明、中で呼んでいる名前（組み込みと自分の変数を除く）を返す。トップレベルで何かを実行するコードは拒否する（読み込むだけで副作用が起きないように）。
- `geo_voyager/function_skill_library.py`:
  - `FunctionSkillLibrary`: Skill を名前で保存する。同じ名前を保存し直すと、古いコードを前の版として残す（`<名前>/v1/code.py`、`v2/` ...）。同じコードは新しい版にしない。保存されていない Skill や import していない名前を呼ぶ Skill は拒否する（呼ばれる側を先に保存する）。
  - `link(program, library)`: プログラムが呼んでいる Skill を、呼び先の呼び先までたどり、呼ばれる側を先に、それぞれ 1 回だけ、プログラムの前に並べる。プログラム自身が同じ名前の関数を定義していれば、そちらを使う。循環（後の版で作られうる）は失敗にする。自分自身の再帰は循環ではない。

懸念: ローカル LLM は、前段の結果を正しく選ぶことや出力の形式を守ることでも揺れていた（[adaptive_round_2.md](adaptive_round_2.md)）。既存の Skill を関数として呼ばせる形がどこまで機能するかは、試してみないと分からない。

### 4.2 World Graph

- 節点の主キーは、TargetRef の stable ID（`relation_id` など）。名前は揺れるが ID は揺れない、という TargetRef の結論（[target_ref.md](target_ref.md)）がそのまま使える。
- 各事実に出所（Goal、step、Observation、データの版、Critic の判定）を付ける。oracle（YuisekinGeoSPARQL）とは別の場所に置き、混ぜない。
- 形式は GeoSPARQL に近い RDF を候補にする。どこまで可能かは、小さく試して確かめる（例えば、今の 22 Goal の実行で判明した区の ID と件数を、出所つきで書き出してみる）。
- Planner は World Graph を読み、既に分かっていることを調べ直さない。ただし、World Graph の事実は oracle ではないので、使うときは出所を Planner と Critic に見せる。

### 4.3 Exploration Graph

- 今の `GoalHistory` を、枝分かれを持てる形にする。失敗した Intent と、それを受けて Planner が選んだ別の方法を、親子の辺で結ぶ。
- 今日の実行で、同じ失敗を繰り返して上限で止まる例（拒否された `対象: 東京23区` の繰り返し、同じ比較の Intent の繰り返し）が多かった。どの枝が既に失敗したかを Planner がグラフとして見られれば、繰り返しを減らせる可能性がある（仮説）。

### 4.4 ARTEX から取り入れたいもの

- 記録型の Gateway: Geo-Voyager の Service Gateway は、すでにすべての外部呼び出しが通る場所である。そこで要求と応答を記録し、エージェント（repair、Planner）が検索できるようにする。今日の Valhalla の `+` の問題や、Taginfo の `count_all` と `count` の取り違えは、記録を見れば分かる種類の誤りだった。
- 承認ゲートの考え方: 規則で決まるものは決定的に処理し、規則に無いものだけモデルに判定させる。今の Planner と Generator の決定的な検査と、LLM の Critic の分担と同じ方向。
- 人の介入: 実行中の Goal に人が口を挟める仕組み。ローカル LLM が詰まる場所を人が見て、1 手だけ直す使い方ができる。

## 5. 順番の案（決めていない）

1. 分析の Goal（G1）をローカル LLM で解かせる経路を作り、どこで詰まるかを見る（[analysis_sandbox.md](analysis_sandbox.md) の「まだやっていないこと」）。
2. 詰まり方を見てから、Skill の合成（4.1）、World Graph（4.2）、Exploration Graph（4.3）、記録型の Gateway（4.4）のどれから手を付けるかを決める。
