from pathlib import Path
from unittest.mock import Mock, patch

from scripts.analyze_tokyo23 import connect


def test_worker_dockerfile_installs_pinned_duckdb_and_extensions_at_build_time():
    definition = Path("docker/worker/Dockerfile").read_text()
    assert "duckdb==1.5.6" in definition
    assert "INSTALL httpfs" in definition and "INSTALL spatial" in definition
    assert "/opt/duckdb/extensions" in definition
    assert "chmod -R a+rX" in definition
    assert "USER 65534:65534" in definition


def test_runtime_loads_installed_extensions_without_autoinstall():
    duckdb = Mock()
    with patch.dict("sys.modules", {"duckdb": duckdb}):
        connection = connect()
    settings = duckdb.connect.call_args.kwargs["config"]
    assert settings["extension_directory"] == "/opt/duckdb/extensions"
    assert settings["autoinstall_known_extensions"] == "false"
    assert settings["autoload_known_extensions"] == "false"
    assert "allow_unsigned_extensions" not in settings
    assert connection.execute.call_args_list[0].args == ("LOAD httpfs",)
    assert connection.execute.call_args_list[1].args == ("LOAD spatial",)
    assert not any("INSTALL" in call.args[0] for call in connection.execute.call_args_list)
