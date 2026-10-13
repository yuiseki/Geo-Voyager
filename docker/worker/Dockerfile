FROM python:3.12-slim

RUN pip install --no-cache-dir duckdb==1.5.6
# rasterio reads the population grid (sum_population_grid). Its wheel carries GDAL with curl, so the COG is read
# by Range through the Gateway; it needs libexpat, which the slim image lacks. The versions are the analysis image's.
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir rasterio==1.5.1 numpy==2.5.3
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
COPY geo_voyager/execution_failure.py geo_voyager/service.py geo_voyager/service_graph.py geo_voyager/services.py geo_voyager/dataset_tables.py geo_voyager/dataset_references.json /usr/local/lib/python3.12/site-packages/geo_voyager/
COPY geo_voyager/control_primitives /usr/local/lib/python3.12/site-packages/geo_voyager/control_primitives
USER 65534:65534
CMD ["python", "-I", "-B", "/opt/geo_voyager/analyze_tokyo23.py"]
