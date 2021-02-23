"""
	TODO: Add issue about division by 100 in setup code
"""

import numpy
import logging

from numba import njit, jit

import arrow

from npsat_backend import settings
from npsat_manager import models
from npsat_manager.support import compatibility

log = logging.getLogger("npsat.mantis")

earliest_data_year = 1945
latest_data_year = 2050
min_year = earliest_data_year  # datetime.datetime.now().year
time_range = 105
max_year = min_year + time_range


"""
	Make a script that rewrites the URFs into a multidimensional raster
"""

"""
	Given user input loading values, reclassify land use rasters to use those new loading proportions.
	For values not given, use the value "1" - maybe we could use a raster that is constant 1s, then
	only adjust specific masks - not sure.

	Do this for each time range.

	Multiply these times the NGw rasters to get the modified scenario rasters. We'd also need to figure
	out some way to interpolate between the defined years for each. It'd be good to plan a route
	that gets us the end result of a reduced NGw/year band. This is flexible to adapt to be the same
	as Giorgos's code though.

	Then we need to convolute. This is where, for each year, we add the loading to every future year
	based on the current year's (reduced) value * the unit response function for the *distance* from the
	current year. When we're done, we sum that whole year's raster.

	If the URFs are just a multidimensional raster too, then we can multiply this year's reduced
	loading raster times all of the bands in the URF raster (from 0 until the end of period is
	reached - we can use a slice for that). Then we can just sum this stack with the sliced
	stack representing all years (by year).

	Then, when we're done, we just sum the raster band representing each year for our value.
"""


@jit
def make_weight_raster(land_use, modifications):
    """
            Given a land use raster and a set of weights, applies the weights to each land use type
            then sets everything else to 1 so that the raster can be used as a multiplier later
    :param land_use: path to a land use raster on disk
    :param modifications: an iterable of npsat_manager.models.Modification objects
    :return:
    """
    land_use_array = compatibility.raster_to_numpy_array(land_use)
    land_use_array += 10000  # offset everything by 10000 so we can identify everything that's still a default later
    for modification in modifications:
        land_use_array[
            land_use_array == modification.crop.caml_code
        ] = modification.reduction

    land_use_array[land_use_array >= 10000] = 1

    return land_use_array


def run(
    spatial_subset="Tulare",
):  # make sure to only run it for Tulare, which we have the URFs for here
    # need to subset the other rasters to that area
    pass


@jit
def create_ranges_nd(start, stop, N, endpoint=True):
    """
            Via https://stackoverflow.com/a/46694364 - for making in between matrices

            Basically, given a 2D array as start and a 2D array as stop, it will return
            a new 3D array (with N values in 3rd dimension) that interpolates between
            start and stop.

            Think of it as taking two bands of a raster and making them the first and last.
            Then, this function adds N-2 bands in between them where the cells are linearly
            interpolated values between the start and stop band cell values. That's what
            we're using this for.

    :param start:
    :param stop:
    :param N:
    :param endpoint:
    :return:
    """
    if endpoint:
        divisor = N - 1
    else:
        divisor = N
    steps = (1.0 / divisor) * (stop - start)
    return start[..., None] + steps[..., None] * numpy.arange(N)


@jit
def make_annual_loadings(modifications, years=settings.NgwRasters.keys()):

    # First make the loadings for just the years we have precalculated (1945, 1960, etc)

    print("Building Annual Loadings")
    loadings = {}
    for year in years:
        print(year)
        base_loading_matrix = compatibility.raster_to_numpy_array(
            settings.NgwRasters[year]
        )
        if (
            year >= settings.ChangeYear
        ):  # if this year is after our reductions are supposed to be made
            weight_matrix = make_weight_raster(
                settings.LandUseRasters[year], modifications=modifications
            )
            loadings[year] = weight_matrix * base_loading_matrix
        else:  # otherwise, use the straight Ngw values - no changes have been made since they're in the past
            loadings[year] = base_loading_matrix

    # Now that we have the values for the base years, we want to interpolate between them to make ndarrays for each year

    print("Interpolating between years")
    sorted_years = sorted(years)
    all_years_data = None
    for i, year in enumerate(sorted_years):
        print(year)
        if year == sorted_years[-1]:  # if it's the last year, we have special behavior
            break

        next_data_year = sorted_years[i + 1]
        interval_size = next_data_year - year
        all_years_in_range = create_ranges_nd(
            loadings[year], loadings[next_data_year], interval_size
        )
        if all_years_data is None:
            all_years_data = all_years_in_range
        else:
            all_years_data = numpy.concatenate(
                [all_years_data, all_years_in_range], -1
            )  # stack them on the last axis now

    return all_years_data


@njit
def convolve_and_sum(loadings, unit_response_functions=None):
    """

    :param loadings:
    :param unit_response_functions: A 3D array where 2D represents space and the third represents "time into the future"
                                                                    from any arbitrary year. These should be the unit response functions from Giorgos
                                                                    where each location has a value for how many years in the future we are currently considering.
                                                                    These values are then convoluted with the loadings to represent travel times

    :return:
    """

    loadings = loadings.T
    print(loadings.shape)
    print("Convolving")
    # if unit_response_functions is None:  # this logic is temporary, but have a safeguard so it's not accidentally used in production
    # 	if settings.DEBUG:
    unit_response_functions = numpy.ones(
        (loadings.shape[0], loadings.shape[1], loadings.shape[2]), dtype=numpy.float64
    )
    # 	else:
    # 		raise ValueError("Must provide Unit Response Functions!")

    # output_matrix = numpy.zeros([loadings.shape[0], loadings.shape[1], loadings.shape[2]], dtype=numpy.float64)
    print("Fake URFs made, convolving")
    x_length = loadings.shape[2]
    y_length = loadings.shape[1]

    # start_time = arrow.utcnow()
    for x in range(x_length):
        for y in range(y_length):
            output = numpy.convolve(
                loadings[:, y, x], unit_response_functions[:, y, x]
            )  # , mode="same")

    # end_time = arrow.utcnow()
    # print("Convolution took {}".format(end_time-start_time))
    print("Done convolving, summing")
    results = loadings.sum()  # axis=(1, 2))  # sum in 2D space
    print("Done summing")
    return results


@njit
def numba_convolve_repr():
    l1 = [1, 2, 3, 4, 5, 6, 7]
    l2 = [10, 11, 12, 13, 14, 15, 16]
    a1 = numpy.asarray(l1)
    a2 = numpy.asarray(l2)
    return numpy.convolve(a1, a2)


@jit
def convolve_and_sum_slow(loadings, unit_response_functions=None):
    """
            This was the first version of the convolution function I wrote. It takes an approach I thought would be
            faster originally and takes the loading matrix for each year and multiplies it against the entire
            URF matrix representing the future relative to the year, then adds its result to the output.
            That would probably take about two hours (it was a minute to a 80 seconds/year), so I wrote the
            other version that's in use, where we convolve each pixel individually, but using numpy's
            convolve.
    :param loadings:
    :param unit_response_functions: A 3D array where 2D represents space and the third represents "time into the future"
                                                                    from any arbitrary year.
    :return:
    """

    loadings = loadings.T
    print(loadings.shape)
    print("Convolving")
    if (
        unit_response_functions is None
    ):  # this logic is temporary, but have a safeguard so it's not accidentally used in production
        if settings.DEBUG:
            unit_response_functions = numpy.ones(
                [loadings.shape[0], loadings.shape[1], loadings.shape[2]],
                dtype=numpy.float64,
            )
        else:
            raise ValueError("Must provide Unit Response Functions!")

    time_span = loadings.shape[0]
    output_matrix = numpy.zeros(
        [loadings.shape[0], loadings.shape[1], loadings.shape[2]], dtype=numpy.float64
    )

    for year in range(time_span):
        print(year)
        URF_length = time_span - year

        print("Subset")
        subset_start = arrow.utcnow()
        current_year_loadings = loadings[
            year,
            :,
            :,
        ]
        subset_end = arrow.utcnow()
        print(subset_end - subset_start)

        # print("Reshape")
        # reshape_start = arrow.utcnow()
        # reshaped_loadings = current_year_loadings.reshape(current_year_loadings.shape)
        # print(reshaped_loadings.shape)
        # repeated_loadings = numpy.repeat(reshaped_loadings, URF_length, 2)
        # reshape_end = arrow.utcnow()
        # print(reshape_end - reshape_start)

        print("Multiply")
        multiply_start = arrow.utcnow()
        new_loadings = numpy.multiply(
            current_year_loadings, unit_response_functions[:URF_length, :, :]
        )
        multiply_end = arrow.utcnow()
        print(multiply_end - multiply_start)

        print("Add and Insert Back in")
        add_start = arrow.utcnow()
        numpy.add(output_matrix[year:, :, :], new_loadings, output_matrix[year:, :, :])
        add_end = arrow.utcnow()
        print(add_end - add_start)
        # multiply this year's matrix * URFs matrix sliced to represent size of future
        # then add result to output_matrix

    results = numpy.sum(output_matrix, [1, 2])  # sum in 2D space


def run_mantis(modifications):
    annual_loadings = make_annual_loadings(modifications=modifications)
    start_time = arrow.utcnow()
    results = convolve_and_sum(
        annual_loadings,
    )
    end_time = arrow.utcnow()

    print("Convolution took: {}".format(end_time - start_time))

    return results


if __name__ == "__main__":
    start_time = arrow.utcnow()

    print(results)
    end_time = arrow.utcnow()
    print("Total Process took {}".format(end_time - start_time))
