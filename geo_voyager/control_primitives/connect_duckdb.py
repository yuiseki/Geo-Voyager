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
