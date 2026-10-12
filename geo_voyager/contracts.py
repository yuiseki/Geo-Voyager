"""The contracts a generated candidate has to follow, as text for prompts.

PRIMITIVE_CONTRACT is the same text the runtime repairer shows. A test keeps the two in step.
"""
from .datasets import load_dataset_graph
from .intent import Intent
from .services import load_service_graph

PRIMITIVE_CONTRACT = (
    'Control Primitive contract（geo_voyager.control_primitives から明示的に import）:\n'
    'connect_duckdb(): DuckDB connection。\n'
    'load_admin_units(connection, area=None): relation(code5,name,population,geometry)。area="東京都23区" 対応。\n'
    'load_stations(connection): relation(station_cd,station_g_cd,line_cd,name,status,latitude,longitude,geometry)。1駅が路線ごとに1行。\n'
    'sum_population_grid(connection, zones): zones の geometry 以外の列と estimated_population（WorldPop の2020年100m推計人口）。\n'
    'geometry は OGC:CRS84。relation どうしの結合は connection.sql で、変数名を表として書く。geometry は返り値に入れない。\n'
    'call_service(service_id, *, path="", params=None, body=None, content_type=None) -> str。'
    'params は dict[str,str]、body=None は GET、それ以外は POST。body は str のまま渡す。encode して bytes にしてはいけない。返答は text。JSON は json.loads。\n'
)


def service_contract(intent: Intent) -> str:
    graph = load_service_graph()
    return '\n'.join(f'{service.id}: {service.protocol}: {service.description}'
                     for service in [graph.get(service_id) for service_id in intent.service_ids])


def dataset_contract(intent: Intent) -> str:
    graph = load_dataset_graph()
    return '\n'.join(f'{dataset.id}: {dataset.description}'
                     for dataset in [graph.get(dataset_id) for dataset_id in intent.dataset_ids])
