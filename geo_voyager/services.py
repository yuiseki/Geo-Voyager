from .service import Service
from .service_graph import ServiceGraph


HTTP_USER_AGENT = 'Geo-Voyager/0.1.0 (+https://github.com/yuiseki/Geo-Voyager)'


def load_service_graph() -> ServiceGraph:
    graph = ServiceGraph()
    for service in (
        Service('overpass', '既存 planet DB の read-only OSM 検索。'
                'GET /api/interpreter は params の data に QL、POST text/plain は body に QL。JSON を受け取るには QL の先頭に [out:json]; が必須。JSON elements が結果。'
                'Overpass QL grammar (abstract metavariables, not a concrete query): '
                'program = header + feature_selection + output; '
                'header = [out:json]; '
                'feature_selection = nwr["<key>"="<value>"](area:<area_id>); area_filter = (area:<area_id>); '
                'output = out body; Count program = [out:json][timeout:12];nwr["<key>"="<value>"](area:<area_id>);out count; Count query header MUST be [out:json][timeout:12]; and count output MUST be out count;。返答は JSON object、件数は data["elements"][0]["tags"]["total"]（文字列の整数）を読む。'
                'timeout は12秒以下、HTTP上限15秒。remark があれば失敗扱い。繰り返すタグ検索は対象集合を先に取得すると速い。'
                'Replace <...> with runtime values. Never use bare IDs as statements. '
                'Every relation ID, including gs:osmRelation, must be converted to an Overpass area ID. nominatim の osm_type=relation なら area_id = int(osm_id) + 3600000000（整数の加算）。文字列連結や乗算ではない。Verify the resolved area exists before counting: area(<area_id>);out ids; returns an area element. Missing area must raise an error, not a zero count.'
                'Numeric area IDs use a colon (area:<area_id>), never a dot, which denotes a named set. タグ比較は = であり == ではない。'
                'bbox は south,west,north,east だが国境検索には area を使う。',
                'https://overpass.yuiseki.net', 'overpass'),
        Service('nominatim', 'セルフホスト地名検索・逆ジオコーディング。/search, /reverse, /lookup。format=jsonv2。/search は q と limit を受け取り JSON 配列を返す。boundingbox は south,north,west,east の文字列配列。boundingbox は国境ではない。他国を含む場合があるため国内検索には osm_type と osm_id を使って境界で絞る。lat/lon, osm_type/osm_id も返す。',
                'https://nominatim.yuiseki.net', 'nominatim'),
        Service('valhalla', 'セルフホスト経路検索。/route, /locate, /status。'
                '/route は POST で、body に JSON 文字列（json.dumps）、content_type="application/json" を渡す。'
                'JSON は locations（[{"lat": 緯度, "lon": 経度}, ...] の 2 点以上）と costing（必須。auto、pedestrian、bicycle など）と '
                'units（"kilometers"）を持つ。応答の JSON root は dict で、経路は payload["trip"]、距離は payload["trip"]["summary"]["length"]（units の単位）、'
                '所要時間は payload["trip"]["summary"]["time"]（秒）。routes というキーは無い。',
                'https://valhalla.yuiseki.net', 'valhalla'),
        Service('taginfo', 'セルフホストOSMタグ辞書。/api/4/search/by_value は query で値を部分一致検索し、JSON data 配列の key/value/count_all を返す。JSON root は dict。payload = json.loads(response) の後、候補は payload["data"]、1候補は候補["key"] と候補["value"] で読む。page は1から、rp で件数を制限、sortname=count_all と sortorder=desc で使用頻度順にできる。/api/4/search/by_keyword は query で説明を検索する。/api/4/key/values は key を受け取り、そのキーの値の一覧を返す。page（1 から）と rp（件数）の両方が必須で、どちらかが無いとHTTP 412（number of results too large, use paging）になる。sortname=count、sortorder=desc で使用数の多い順に並ぶ。JSON root は dict で、payload["data"] の各要素が value（タグの値）、count（使用数）、fraction、in_wiki、description を持つ。使用数のフィールドは count（count_all ではない）。/api/4/tags/list は key または tags が必須で query 検索には使わない。1 つのタグ（key と value）の使用数は /api/4/tag/stats に key と value を渡して取る。payload["data"] の要素のうち type が "all" のものの count が全体の使用数。search/by_value は部分一致なので（ramen で noodle;ramen なども返る）、1 つのタグの使用数には使わない。',
                'https://taginfo.yuiseki.net', 'taginfo'),
        Service('yuisekin-geosparql', 'YuisekinGeoSPARQLのpinned geographic graph。東京23区の全23個の gs:Ward に日本語 rdfs:label と必須 gs:osmRelation（URI）が登録されている。型から対象集合、名称、外部IDの一覧を取得できる。/geo/sparql, /geo/query。SELECT の JSON root は dict、行の配列は payload["results"]["bindings"]。各変数は dict で、文字列は row["<variable>"]["value"] から取得する。row["uri"] や row["label"] 自体を文字列として扱わない。'
                'geo:Feature, rdfs:label, geo:sfTouches/geo:sfWithin 等を問い合わせられる。必須の relation ID は gs:osmRelation から取得する（geo:osmRelation ではない）。gs:osmRelation は OSM relation URI、末尾が正の数値ID。外部IDの必須プロパティパターンは ?ward gs:osmRelation ?relation 。SELECT ?label ?relation にし、?ward のURIではなく ?relation の値を使う。URIをそのまま SELECT し、Python の uri.rsplit("/", 1)[-1] でIDを取る。出力する relation_id は数字だけにし、str(relation_id).isdigit() を assert する。SPARQL の REPLACE や複雑な正規表現は使わない。gs:osmId は負数を含むため relation ID と同一視しない。'
                'geo namespace=http://www.opengis.net/ont/geosparql#。rdfs labelsは日本語@jaや英語@en。同じ個体に両方あるので日本語の一覧は FILTER(LANG(?label) = "ja") で1個体1行にし、ORDER BY ?label で順序を固定する。言語タグなしの文字列とは一致しない。rdfs:label のトリプルでラベル変数を束縛してから FILTER する。未束縛の変数を FILTER するだけでは名前は検索できない。名前の検索は FILTER(STR(?label) = "対象の名前") を使い、言語タグを除いた文字列同士で比較する。東京23区の型は gs:Ward、gs namespace=https://yuiseki.net/geosparql/schema#。rdfs namespace=http://www.w3.org/2000/01/rdf-schema#。個体URIを推測しない。schema namespaceは個体URIではない。個体URIはrdfs:labelから検索して取得する。各クエリで PREFIX を明示する。prefix はサーバーへ暗黙登録されていない。',
                'http://geosparql:3030', 'sparql'),
    ):
        graph.register(service)
    return graph
