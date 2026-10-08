FROM python:3.12-slim

RUN pip install --no-cache-dir duckdb==1.5.6
RUN python - <<'PY'
import duckdb
con = duckdb.connect(config={"threads": "1"})
con.execute("SET extension_directory='/opt/duckdb/extensions'")
con.execute("INSTALL httpfs FROM 'https://extensions.duckdb.org'")
con.execute("INSTALL spatial FROM 'https://extensions.duckdb.org'")
con.close()
PY
RUN chmod -R a+rX /opt/duckdb/extensions

COPY scripts/analyze_tokyo23.py /opt/geo_voyager/analyze_tokyo23.py
USER 65534:65534
CMD ["python", "-I", "-B", "/opt/geo_voyager/analyze_tokyo23.py"]
