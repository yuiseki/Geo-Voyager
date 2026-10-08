"""行政区 Dataset のみを使う固定の人口最大区分析。"""


def analyze(connection, dataset_id):
    row = connection.execute(
        "SELECT code5, name, population FROM read_parquet(?) "
        "WHERE code5 BETWEEN '13101' AND '13123' "
        "ORDER BY population DESC LIMIT 1",
        [f"http://gateway:8000/datasets/{dataset_id}"],
    ).fetchone()
    if row is None:
        raise ValueError("No Tokyo ward found")
    _, name, population = row
    if type(population) is not int:
        raise TypeError("population must be an integer")
    return f"東京都23区で人口が最も多い区は{name}で、人口は{population}人である"


def main(dataset_id):
    from analyze_tokyo23 import connect

    with connect() as connection:
        print(analyze(connection, dataset_id))
