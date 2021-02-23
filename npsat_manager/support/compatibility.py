import logging

import numpy

log = logging.getLogger("npsat.support.compatibility")

ARCPY = False
GDAL = False
PY_MANTIS = False  # flag on whether we can run Mantis
try:
    import arcpy

    ARCPY = True
except ImportError:
    pass

try:
    from osgeo import gdal

    GDAL = True
except ImportError:
    pass

if not ARCPY and not GDAL:
    PY_MANTIS = False
    log.warning(
        "Both arcpy and GDAL are missing - won't be able to run Mantis via Python - make sure at least one is available for processing"
    )
else:
    PY_MANTIS = True


def raster_to_numpy_array(raster):
    """
            Provides a compatibility layer for loading rasters into numpy arrays using either arcpy or GDAL.

            Not totally great since this means our testing and live environments could be different, but right now
            the flexibility is nice. We'll want to make sure we run the actual tests on the production machine. It's
            possible that the data types from the different methods of loading could be different. Be careful!

            GDAL method via https://gis.stackexchange.com/a/33070/1955
    :param raster: Full path to a raster on disk - reads only the first band when using GDAL
    :return: numpy array representing the values in the raster
    """
    if ARCPY:
        return arcpy.RasterToNumPyArray(arcpy.Raster(raster))
    elif GDAL:
        raster_source = gdal.Open(raster)
        return numpy.array(raster_source.GetRasterBand(1).ReadAsArray())
    else:
        raise RuntimeError(
            "Both arcpy and GDAL are unavailable - can't load raster into numpy array. Please install Arcpy or GDAL with Python bindings in the current interpreter"
        )
