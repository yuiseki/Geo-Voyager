# The analysis worker: the scientific Python stack, run offline against data fixed on the host.
# Versions are those study-geoai-algo-py reported its oracle numbers with (its uv.lock, 2026-10-10),
# so a difference from an oracle is not a difference of library. DuckDB stays at Geo-Voyager's 1.5.6.
# torch (tabpfn, timesfm) is left out.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir \
    numpy==2.5.3 scipy==1.18.1 pandas==3.0.6 scikit-learn==1.9.1 statsmodels==0.15.0 \
    duckdb==1.5.6 pyarrow==25.0.1 matplotlib==3.11.2 networkx==3.7 \
    lightgbm==4.7.0 xgboost==3.4.1 catboost==1.2.10 shap==0.52.0 verde==1.9.0 rasterio==1.5.1 \
    ortools==9.15.6755 highspy==1.12.0
# rasterio's wheel needs libexpat, which the slim image lacks.
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 && rm -rf /var/lib/apt/lists/*
RUN python - <<'PY'
import duckdb
con = duckdb.connect(config={"threads": "1"})
con.execute("SET extension_directory='/opt/duckdb/extensions'")
con.execute("INSTALL spatial FROM 'https://extensions.duckdb.org'")
con.close()
PY
RUN chmod -R a+rX /opt/duckdb/extensions

COPY geo_voyager/__init__.py /usr/local/lib/python3.12/site-packages/geo_voyager/__init__.py
COPY geo_voyager/analysis_primitives /usr/local/lib/python3.12/site-packages/geo_voyager/analysis_primitives
ENV MPLBACKEND=Agg MPLCONFIGDIR=/tmp/matplotlib
USER 65534:65534
