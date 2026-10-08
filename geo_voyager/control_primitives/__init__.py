"""検証済みの sandbox 接続と Gateway 経由の行政区域読み込み。"""


def connect_duckdb():
    import duckdb

    connection = duckdb.connect(config={
        "extension_directory": "/opt/duckdb/extensions",
        "autoinstall_known_extensions": "false",
        "autoload_known_extensions": "false",
        "threads": "1",
        "memory_limit": "64MB",
    })
    connection.execute("LOAD httpfs")
    connection.execute("LOAD spatial")
    return connection


def dataset_url(dataset_id: str) -> str:
    if dataset_id != "yuiseki/jp-admin-2026-09":
        raise ValueError("Only the administrative dataset is supported")
    return f"http://gateway:8000/datasets/{dataset_id}"


def load_admin_units(dataset_id: str, connection):
    return connection.read_parquet(dataset_url(dataset_id)).project("code5, name, population")
