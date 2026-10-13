"""The contracts a generated candidate has to follow, as text for prompts.

PRIMITIVE_CONTRACT is the same text the runtime repairer shows. A test keeps the two in step. The tables of the
datasets an Intent declares are made from the dataset references (geo_voyager.table_contracts, ADR 0010).
"""
from .datasets import load_dataset_graph
from .intent import Intent
from .services import load_service_graph
from .table_contracts import table_contract

PRIMITIVE_CONTRACT = (
    'Control Primitive contract（geo_voyager.control_primitives から明示的に import）:\n'
    'connect_duckdb(): DuckDB connection。\n'
    'read_table(connection, dataset_id, table): Dataset の表の全列の relation。列名は表の説明のまま。地域は filter の条件で絞る。\n'
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


def primitive_contract(intent: Intent) -> str:
    """The primitives, and the tables of the datasets the Intent declares."""
    tables = table_contract(intent.dataset_ids)
    return PRIMITIVE_CONTRACT + (f'Intent の Dataset の表:\n{tables}\n' if tables else '')
