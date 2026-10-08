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
COPY geo_voyager/__init__.py /usr/local/lib/python3.12/site-packages/geo_voyager/__init__.py
COPY geo_voyager/service.py geo_voyager/service_graph.py geo_voyager/services.py /usr/local/lib/python3.12/site-packages/geo_voyager/
COPY geo_voyager/control_primitives /usr/local/lib/python3.12/site-packages/geo_voyager/control_primitives
USER 65534:65534
CMD ["python", "-I", "-B", "/opt/geo_voyager/analyze_tokyo23.py"]
