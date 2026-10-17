"""公開 Dataset Card と Files を2026-10-08に確認した静的メタデータ。

コメントの SHA は調査した Hugging Face リビジョン。
Card: {dataset.url}/blob/{sha}/README.md
Files: {dataset.url}/tree/{sha}
実行時のネットワークアクセスや実データの読み込みは行わない。
"""

from .dataset import Dataset
from .dataset_graph import DatasetGraph


CATALOG = (
    # 9a9b4a77e89e28a66bf15781644a16b63501f622
    Dataset(
        id="yuiseki/osm-japan-src-2026-08",
        description="OpenStreetMap の2026-08-31 planet から切り出した日本の固定スナップショット。",
        url="https://huggingface.co/datasets/yuiseki/osm-japan-src-2026-08",
        license="ODbL-1.0",
        formats=("OSM PBF", "GeoParquet 1.1", "GeoJSON"),
        spatial_coverage="日本全国（complete_ways により境界外へ延びる地物も含む）",
        temporal_coverage="2026-08-31",
        contents=("OSM の地点", "線", "ポリゴン", "道路", "切り出し境界"),
    ),
    # 39fdb22f42b7619b753b5389bc107aaadf8ba614
    Dataset(
        id="yuiseki/mlit-toshi-keikaku-jp",
        description="国土交通省の都市計画決定GISデータを層別に再形式化。参考情報で、決定範囲は概略。",
        url="https://huggingface.co/datasets/yuiseki/mlit-toshi-keikaku-jp",
        license="PDL1.0（CC BY 4.0互換。Card に旧原典の自治体別条件に関する未確認事項あり）",
        formats=("GeoParquet 1.0", "Shapefile (ZIP)", "GeoJSON (ZIP)", "CityGML (ZIP)"),
        spatial_coverage="日本47都道府県の約1,400自治体（層ごとに収録範囲が異なる）",
        temporal_coverage="2025年度版（2026-05公開、2026-07修正。個別データの時点は異なる）",
        contents=("用途地域と容積率・建蔽率", "都市計画道路", "公園", "地区計画", "立地適正化計画等26層"),
    ),
    # e6c87b1d7095c17422147962185071a986e13135
    Dataset(
        id="yuiseki/jp-admin-2026-09",
        description=("デジタル庁のアドレス・ベース・レジストリと e-Stat の2020年国勢調査小地域境界を結合・集約。"
                     "population は2020年国勢調査の人口。東京23区の23区の名前・人口・境界は、この Dataset から1回で読める。区域の ID は行政コード code5 で、OSM の relation_id は持たない。"),
        url="https://huggingface.co/datasets/yuiseki/jp-admin-2026-09",
        license="CC-BY-4.0",
        formats=("GeoParquet 1.1",),
        spatial_coverage="日本47都道府県・1,918市区町村（境界・人口が欠ける自治体あり）",
        temporal_coverage="名称・コード: 2026-09、境界・人口・世帯: 2020年国勢調査",
        contents=("行政区域名・コード", "代表点", "行政区域ポリゴン", "人口", "世帯数"),
        data_url=(
            "https://huggingface.co/datasets/yuiseki/jp-admin-2026-09/resolve/"
            "e6c87b1d7095c17422147962185071a986e13135/municipalities.parquet"
        ),
    ),
    # a33321099406b47338be0d03a4887059473fde0c
    Dataset(
        id="yuiseki/ekidata-jp",
        description="株式会社バリューアンドビジョンの駅データ.jp無料版CSVと、その型付きParquet・駅位置。",
        url="https://huggingface.co/datasets/yuiseki/ekidata-jp",
        license="駅データ.jp利用規約（https://ekidata.jp/agreement.php）。未加工データの第三者提供は無償。",
        formats=("CSV", "Parquet", "GeoParquet 1.0"),
        spatial_coverage="日本全国（無料版の駅データは新幹線駅を含まない）",
        temporal_coverage="取得: 2026-10-05。収録版: 2025-05-23〜2026-09-14、最新駅版: 2026-07-31。都道府県マスタは日付なし。",
        contents=("鉄道事業者", "路線", "駅と座標", "路線上の隣接駅", "都道府県マスタ"),
        data_url=(
            "https://huggingface.co/datasets/yuiseki/ekidata-jp/resolve/"
            "a33321099406b47338be0d03a4887059473fde0c/"
            "parquet/2026-10-05/station.2026-07-31.parquet"
        ),
    ),
    # cb54e5985662c617a235278bc3529cc172e6368c
    Dataset(
        id="yuiseki/worldpop-jp-2026-01",
        description=("WorldPop R2025A の日本人口ラスター原本と、画素値を保持したCOG変換版。国勢調査値ではなく推計・予測。"
                     "実行環境で読めるのは2020年の100m総人口（constrained）だけで、"
                     "sum_population_grid が、渡した区域（read_table で読んだ jp-admin-2026-09 の境界など）ごとに画素を足した推計人口を返す。"
                     "Goal が WorldPop・推計を名指ししない人口は、yuiseki/jp-admin-2026-09 の国勢調査人口を使う。"),
        url="https://huggingface.co/datasets/yuiseki/worldpop-jp-2026-01",
        license="CC-BY-4.0（各製品の DOI による引用）",
        formats=("GeoTIFF", "Cloud Optimized GeoTIFF", "Parquet"),
        spatial_coverage="日本全国",
        temporal_coverage="2015〜2030年の推計・予測、R2025A（原本の更新: 2025-07〜2026-01）",
        contents=("100m・1km総人口", "1km年齢・性別人口", "都市化度", "ラスターのファイルメタデータ表"),
        # The 100 m COG: the 1 km one put Taito at 173,724 against the census's 211,444. The Hub answers a Range
        # request with 206, so the worker reads only the pixels of Tokyo.
        data_url=(
            "https://huggingface.co/datasets/yuiseki/worldpop-jp-2026-01/resolve/"
            "cb54e5985662c617a235278bc3529cc172e6368c/"
            "cog/GIS/Population/Global_2015_2030/R2025A/2020/JPN/v1/100m/constrained/"
            "jpn_pop_2020_CN_100m_R2025A_v1.tif"
        ),
    ),
    # d0b1ad8c98643db75c767c0ff96db800126f4954 (pinned by Geo-Voyager: the reference has no card revision)
    Dataset(
        id="yuiseki/worldbank-wdi",
        description=("世界銀行の世界開発指標。国と年ごとの人口、GDP、保健、教育、環境など約 1,400 指標。座標は無い。"
                     "版 2026-10-01 の data（国 × 指標 × 年の値）、series（指標の定義）、countries（国と集計単位）を読める。"),
        url="https://huggingface.co/datasets/yuiseki/worldbank-wdi",
        license="CC BY 4.0 に世界銀行の紛争解決条項（調停と仲裁）が加わる。指標ごとに出典の表示が要る",
        formats=("Parquet",),
        spatial_coverage="国と集計単位 264（国 217、集計単位 47）。座標なし",
        temporal_coverage="1960〜2025年、版 2026-10-01",
        contents=("指標の値", "指標の定義", "国と集計単位"),
        data_url=("https://huggingface.co/datasets/yuiseki/worldbank-wdi/resolve/"
                  "d0b1ad8c98643db75c767c0ff96db800126f4954/parquet/2026-10-01/data.parquet"),
    ),
    # efdd0668c57c9d42307e12eacbf66d8d151de5b9 (pinned by Geo-Voyager: the reference has no card revision)
    Dataset(
        id="yuiseki/natural-earth",
        description=("全世界の小縮尺ベクター。版 v5.1.2 の 10m の国（属領や係争地を含む）、州・省、都市の点を読める。"),
        url="https://huggingface.co/datasets/yuiseki/natural-earth",
        license="Public domain",
        formats=("GeoParquet",),
        spatial_coverage="全世界",
        temporal_coverage="v5.1.2",
        contents=("国の面", "州・省の面", "都市の点"),
        data_url=("https://huggingface.co/datasets/yuiseki/natural-earth/resolve/"
                  "efdd0668c57c9d42307e12eacbf66d8d151de5b9/parquet/v5.1.2/10m_cultural/ne_10m_admin_0_countries.parquet"),
    ),
    # 7e32fd1266b1eea107d83ebecd6974e94744c3a7 (the card's revision). Read for its latest year, 2026 (Geo-Voyager's choice)
    Dataset(
        id="yuiseki/ksj-l01-land-price",
        description=("地価公示。国土交通省が毎年 1 月 1 日時点で公示する、全国約 2 万 6 千の標準地の価格（円/m²）と対前年変動率、"
                     "所在、地積、用途、経度と緯度。2026 年の表を読める。"),
        url="https://huggingface.co/datasets/yuiseki/ksj-l01-land-price",
        license="CC BY 4.0（国土数値情報の利用約款で PDL1.0）。出典の表示と、加工したことの明記が要る",
        formats=("Parquet",),
        spatial_coverage="日本全国の標準地（主に都市計画区域の中）。点",
        temporal_coverage="2026 年 1 月 1 日時点",
        contents=("標準地の公示価格", "対前年変動率", "所在と用途"),
        data_url=("https://huggingface.co/datasets/yuiseki/ksj-l01-land-price/resolve/"
                  "7e32fd1266b1eea107d83ebecd6974e94744c3a7/parquet/2026.parquet"),
    ),
    # 38f7a5f961b6e33343d82a11152e768c37d22664 (the card's revision)
    Dataset(
        id="yuiseki/osm-tokyo23-src-2026-08",
        description=("OpenStreetMap の東京 23 区の凍結版（2026-08-31）。osm2pgsql の点、線、面、道路の 4 つの表。"
                     "施設、店、公園、運動場、寺社、建物などを、タグの列（amenity、leisure、shop、sport など）で引ける。"
                     "全国版の約 30 分の 1 で、23 区の中で閉じる問いなら Overpass より軽い。"),
        url="https://huggingface.co/datasets/yuiseki/osm-tokyo23-src-2026-08",
        license="ODbL-1.0。派生物にも同じ条件と出典の表示（© OpenStreetMap contributors）が及ぶ",
        formats=("GeoParquet",),
        spatial_coverage="東京 23 区（区に掛かる way は丸ごと入るので、区の外の地物もある）",
        temporal_coverage="2026-08-31 の 1 時点",
        contents=("点", "線", "面", "道路"),
        data_url=("https://huggingface.co/datasets/yuiseki/osm-tokyo23-src-2026-08/resolve/"
                  "38f7a5f961b6e33343d82a11152e768c37d22664/parquet/planet_osm_polygon.parquet"),
    ),
)


def load_dataset_graph() -> DatasetGraph:
    graph = DatasetGraph()
    for dataset in CATALOG:
        graph.register(dataset)
    return graph


def load_readable_dataset_graph() -> DatasetGraph:
    """The datasets generated code can read: the ones with a data_url, which dataset_url serves.

    The Curriculum and the Planner see only these. A dataset the sandbox can not open makes a Goal or an Intent
    that no code can answer, and a model asked to write that code reasons about how to read it until its reply is cut.
    """
    graph = DatasetGraph()
    for dataset in CATALOG:
        if dataset.data_url:
            graph.register(dataset)
    return graph
