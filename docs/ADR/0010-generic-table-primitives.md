# 0010 Dataset の読み込みを、データセットの reference から組み立てる汎用の Primitive にする

- 日付: 2026-10-13
- 状態: 採用（実装はこれから）

## 背景

`geo_voyager/control_primitives/` は、Dataset ごとに手で書いた関数で読み込んでいる。新しい表を 1 つ使えるようにするたびに、次の 5 か所以上を手で書き足す必要がある。

1. Dataset ごとの専用の関数（`load_admin_units`、`load_stations`）。読む列と名前の付け替えは `COLUMNS` に手書きしている。
2. 読める Dataset の一覧（`dataset_url.py` が 3 つの id 以外を拒む）。
3. Gateway の中継先（`Dataset.data_url` の 1 ファイルだけ）。そのため、1 つの Dataset から 1 つの表しか読めない。駅データの路線（line）や隣り合う駅（join）、行政区域の都道府県の表は、sandbox から読めない。
4. 地域の知識（`load_admin_units.py` の `AREAS = {'東京都23区': "code5 BETWEEN '13101' AND '13123'"}`）。対応している地域はこれだけで、ほかの地域は関数を直さないと使えない。
5. Generator、repair、`contracts.py`（2026-10-14 から `contracts/prompt.py`）のプロンプトに書き写した Primitive の契約。Primitive の外から名前で参照している箇所が 22 ある。

一方、GeoAI-skills（How-to Graph）の dataset-discovery の reference には、YAML frontmatter で、各表の読み先（`tables[].read`）、1 行が何か（grain）、ID、結合キー、持たないキー、列の意味が、実測して書いてある。これはすでに、固定したコミットで `geo_voyager/dataset_references.json` に写し、Planner への説明に使っている（f76eef4）。

## 決定

frontmatter を、sandbox で読める表の正本にする。

1. 読める表は `dataset_references.json` の `tables` で決める。
   - Parquet の表は、どれでも読める。
   - Gateway は、表の読み先を、その Dataset の `card_revision` に固定した Hugging Face の URL に直して中継する（`hf://datasets/<repo>/<path>` を `https://huggingface.co/datasets/<repo>/resolve/<card_revision>/<path>` に）。
   - `resolve/main` のように版を固定していない読み先は、同期のときに固定するか、同期を止める。
   - Gateway の API は `GET/HEAD /datasets/<dataset_id>/<table>`。登録した表の名前以外は 404。任意のパスは受け付けない。
2. 汎用の Primitive は `read_table(connection, dataset_id, table)` とし、表のすべての列を DuckDB の relation で返す。
   - 列の名前は付け替えない。コードは、reference と同じ列の名前で読む。
   - 経度と緯度の地理座標系（EPSG:4612、EPSG:4326、OGC:CRS84）の geometry は、`OGC:CRS84` に名前をそろえて返す。DuckDB は名前の違う CRS どうしの空間結合を拒むためで、これらの違いは駅の位置の精度より小さい（GeoAI-skills の jp-admin の reference に実測がある）。そろえたことは docstring とプロンプトに書く。
3. 地域の絞り込みは、関数に埋め込まず、データの列の条件で書く。
   - 例えば、東京23区は `pref_code = '13' AND name LIKE '%区'`。これはコードや Intent の側で書く。
   - 名前のついた地域とその条件は、Geo-Voyager の 1 か所に、データとして置く。プロンプトはそこから組み立てる。
4. SQL では書けない操作だけを、汎用の Primitive として残す。
   - 例えば、ラスタの画素を区域ごとに足す `sum_population_grid` や、登録サービスへの問い合わせの `call_service`。
5. Generator と repair に見せる契約は、手で書き写さない。
   - Intent が宣言した Dataset の表について、frontmatter（grain、ID、結合キー、持たないキー、列の意味）と、Primitive の docstring から組み立てる。
   - 文脈が 8,192 トークンなので、見せるのは Intent が宣言した Dataset の表だけにする。
6. 移行
   - `load_admin_units` と `load_stations` は、保存済みの Skill（seed を含む）が呼んでいる。そのため、`read_table` の上の薄い包みとして残し、プロンプトには出さない。
   - seed の Skill は `read_table` で書き直す。
   - 2026-10-14: seed の Skill もベンチの正解のコードも `read_table` に移ったので、`load_admin_units` と `load_stations` を削除した。ベンチの正解のうち `ward_pop_max` は、`load_admin_units` の列が 4 つに増えたあと 3 つで受けていて、すでに壊れていた。

## 結果

- 新しい Parquet の表を使うのに要るのは、GeoAI-skills に reference を書き、同期することだけになる。Geo-Voyager のコードは変わらない。
- 列の名前が reference と同じになるので、Planner、Generator、reference のあいだで名前を付け替える層がなくなる。
- 地域の知識が関数から出て、コードと Intent に現れる。条件を誤れば、結果の件数（例: 23 区なら 23 行）で見えるようにする。
- osm-japan（PBF と大きな GeoParquet）は、範囲を読むだけでも大きいので、この決定の範囲外とする。読めるようにするかは、別に決める。
- 作り直したら、段階 1（Planner の最初の一手）から測り直す。生成のプロンプトが変わるので、段階 2 以降は新しい Primitive で測る。
