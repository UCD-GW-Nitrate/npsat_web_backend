import os

import arcpy

from npsat_backend import settings


def extract_region(region_polygon, output_geodatabase, inputs, name):
    for year in inputs:
        raster = inputs[year]
        print(raster)
        output_path = os.path.join(output_geodatabase, "{}_{}".format(name, year))
        print(output_path)
        with arcpy.EnvManager(
            outputCoordinateSystem=raster,
            extent="MINOF",
            snapRaster=raster,
            pyramid="NONE",
        ):
            output = arcpy.sa.ExtractByMask(
                arcpy.Raster(raster), region_polygon
            )  # Clip_management(arcpy.Raster(raster), region_polygon, output_path, region_polygon, "#", "NONE", "NO_MAINTAIN_EXTENT")  # NO_MAINTAIN_EXTENT should mean to keep cell alignment
            output.save(output_path)


def run_tulare():
    base_gdb = os.path.join(settings.BASE_DIR, "npsat_manager", "data", "Tulare.gdb")
    tulare = os.path.join(
        base_gdb, "TulareCounty"
    )  # "38,169.875000 -247,393.296900 182,116.171900 -139,171.828100"

    print("Using Tulare County at {}".format(tulare))
    extract_region(
        tulare, output_geodatabase=base_gdb, inputs=settings.NgwRasters, name="Ngw"
    )
    extract_region(
        tulare, output_geodatabase=base_gdb, inputs=settings.LandUseRasters, name="LU"
    )


if __name__ == "__main__":
    run_tulare()
