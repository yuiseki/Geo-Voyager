from .service import Service
from .service_graph import ServiceGraph


HTTP_USER_AGENT = 'Geo-Voyager/0.1.0 (+https://github.com/yuiseki/Geo-Voyager)'


def load_service_graph() -> ServiceGraph:
    graph = ServiceGraph()
    for service in (
        Service('overpass', 'セルフホストOSM検索。Overpass QLを /api/interpreter に送る。日本のOSM要素を検索できる。',
                'https://overpass.yuiseki.net', 'overpass'),
        Service('nominatim', 'セルフホスト地名検索・逆ジオコーディング。/search, /reverse, /lookup。format=jsonv2。',
                'https://nominatim.yuiseki.net', 'nominatim'),
        Service('valhalla', 'セルフホスト経路検索。/route, /locate, /status。',
                'https://valhalla.yuiseki.net', 'valhalla'),
        Service('taginfo', 'セルフホストOSMタグ辞書。/api/4/tags/list, /api/4/keys/all, /api/4/key/values, /api/4/site/info でタグや値を調べる。',
                'https://taginfo.yuiseki.net', 'taginfo'),
        Service('yuisekin-geosparql', 'YuisekinGeoSPARQLのpinned geographic graph。/geo/sparql, /geo/query。'
                'geo:Feature, rdfs:label, geo:sfTouches/geo:sfWithin 等を問い合わせられる。'
                'geo namespace=http://www.opengis.net/ont/geosparql#。rdfs labelsは日本語@jaや英語@en。',
                'http://geosparql:3030', 'sparql'),
    ):
        graph.register(service)
    return graph
