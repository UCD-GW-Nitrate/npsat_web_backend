from numba import njit
import numpy

import django

import os

os.environ["DJANGO_SETTINGS_MODULE"] = "npsat_backend.settings"
django.setup()

from npsat_manager import mantis
from npsat_manager import models


@njit
def numba_sum():
    l1 = [13, 214, 125]
    array = numpy.array(l1, dtype=numpy.float64)
    return array.sum()


test = numba_sum()

mods = models.Modification.objects.all()

mantis.run_mantis(mods)
