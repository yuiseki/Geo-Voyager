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
        description="デジタル庁のアドレス・ベース・レジストリと e-Stat の2020年国勢調査小地域境界を結合・集約。",
        url="https://huggingface.co/datasets/yuiseki/jp-admin-2026-09",
        license="CC-BY-4.0",
        formats=("GeoParquet 1.1",),
        spatial_coverage="日本47都道府県・1,918市区町村（境界・人口が欠ける自治体あり）",
        temporal_coverage="名称・コード: 2026-09、境界・人口・世帯: 2020年国勢調査",
        contents=("行政区域名・コード", "代表点", "行政区域ポリゴン", "人口", "世帯数"),
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
    ),
    # cb54e5985662c617a235278bc3529cc172e6368c
    Dataset(
        id="yuiseki/worldpop-jp-2026-01",
        description="WorldPop R2025A の日本人口ラスター原本と、画素値を保持したCOG変換版。国勢調査値ではなく推計・予測。",
        url="https://huggingface.co/datasets/yuiseki/worldpop-jp-2026-01",
        license="CC-BY-4.0（各製品の DOI による引用）",
        formats=("GeoTIFF", "Cloud Optimized GeoTIFF", "Parquet"),
        spatial_coverage="日本全国",
        temporal_coverage="2015〜2030年の推計・予測、R2025A（原本の更新: 2025-07〜2026-01）",
        contents=("100m・1km総人口", "1km年齢・性別人口", "都市化度", "ラスターのファイルメタデータ表"),
    ),
)


def load_dataset_graph() -> DatasetGraph:
    graph = DatasetGraph()
    for dataset in CATALOG:
        graph.register(dataset)
    return graph
