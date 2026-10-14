def connect_duckdb():
    import duckdb

    connection = duckdb.connect(config={
        "extension_directory": "/opt/duckdb/extensions",
        "autoinstall_known_extensions": "false",
        "autoload_known_extensions": "false",
        "threads": "2",
        "memory_limit": "512MB",
        # The working directory is read-only; past its memory a query spills to the tmpfs (256 MB).
        "temp_directory": "/tmp/duckdb",
    })
    connection.execute("LOAD httpfs")
    connection.execute("LOAD spatial")
    return connection
