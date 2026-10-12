import os

# A shell that exports another GDAL's or PROJ's data files (anaconda does) makes rasterio's own GDAL fail on EPSG
# codes, or read a missing value as None. The worker image has no such variables; the tests run without them too.
for name in ('GDAL_DRIVER_PATH', 'GDAL_DATA', 'PROJ_DATA', 'PROJ_LIB'):
    os.environ.pop(name, None)
