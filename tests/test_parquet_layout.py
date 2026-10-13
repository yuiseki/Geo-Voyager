"""Which column a Parquet file is split by, measured from its footer at sync time.

Memory run 1b (2026-10-13): reading two wards from jp-admin by name alone took 36 to 40 s, over the sandbox's 30 s,
because every one of the 47 row groups (one per prefecture) was read; with pref_code = '13' it took 3 to 4 s."""
import duckdb

from geo_voyager.parquet_layout import split_columns


def written(tmp_path, sql):
    path = tmp_path / 'table.parquet'
    connection = duckdb.connect(config={'threads': '1'})
    connection.execute(f"COPY ({sql}) TO '{path}' (FORMAT parquet, ROW_GROUP_SIZE 2048)")
    return connection, str(path)


def test_a_column_with_one_value_in_each_row_group_is_what_the_file_is_split_by(tmp_path):
    connection, path = written(tmp_path, "SELECT lpad((i // 2048 + 1)::VARCHAR, 2, '0') AS pref_code, i::VARCHAR AS name FROM range(4096) t(i) ORDER BY i")
    assert split_columns(connection, path) == (2, ['pref_code'])


def test_a_file_of_one_row_group_is_not_split(tmp_path):
    connection, path = written(tmp_path, "SELECT * FROM (VALUES ('01', 'a')) t(pref_code, name)")
    assert split_columns(connection, path) == (1, [])


def test_a_column_with_the_same_value_everywhere_does_not_split_the_file(tmp_path):
    connection, path = written(tmp_path, "SELECT 'x' AS kind, lpad((i // 2048 + 1)::VARCHAR, 2, '0') AS pref_code FROM range(4096) t(i) ORDER BY i")
    assert split_columns(connection, path) == (2, ['pref_code'])
