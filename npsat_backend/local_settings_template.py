import os

from .databases import DATABASES

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'MAKE_ME_A_SAFE_CRYPTOGRAPHICALLY_SECURE_SEED_VALUE'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

LOGGING_FOLDER = os.path.join(BASE_DIR) if DEBUG else os.path.join(BASE_DIR, "..", "logs")

ADMINS = []

SERVE_ADDRESS = "*:8010"  # what address and port should we serve the site on
ALLOWED_HOSTS = []

# EMAIL SENDING SETTINGS
EMAIL_HOST = 'smtp.gmail.com'  # email server
EMAIL_PORT = 587
EMAIL_HOST_USER = ''  # email server username
EMAIL_HOST_PASSWORD = ''  # email server password
EMAIL_USE_TLS = True
SERVER_EMAIL = ''  # what address does the email come from?

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

MANTIS_STATUS_MESSAGE = "status"
MANTIS_STATUS_RESPONSE = "online"

StartYear = 1945  # When to start the curves off
EndYear = 2065  # What's the max year to calculate until?
ChangeYear = 2020  # When do we actually start trying to get a reduction?
DataFolder = os.path.join(BASE_DIR, "npsat_manager", "data")

NgwRasters = {
    1945: os.path.join(DataFolder, "Tulare.gdb", "Ngw_1945.tif"),
    1960: os.path.join(DataFolder, "Tulare.gdb", "Ngw_1960.tif"),
    1975: os.path.join(DataFolder, "Tulare.gdb", "Ngw_1975.tif"),
    1990: os.path.join(DataFolder, "Tulare.gdb", "Ngw_1990.tif"),
    2005: os.path.join(DataFolder, "Tulare.gdb", "Ngw_2005.tif"),
    2020: os.path.join(DataFolder, "Tulare.gdb", "Ngw_2020.tif"),
    2035: os.path.join(DataFolder, "Tulare.gdb", "Ngw_2035.tif"),
    2050: os.path.join(DataFolder, "Tulare.gdb", "Ngw_2050.tif"),
}

LandUseRasters = {
    1945: os.path.join(DataFolder, "Tulare.gdb", "LU_1945.tif"),
    1960: os.path.join(DataFolder, "Tulare.gdb", "LU_1960.tif"),
    1975: os.path.join(DataFolder, "Tulare.gdb", "LU_1975.tif"),
    1990: os.path.join(DataFolder, "Tulare.gdb", "LU_1990.tif"),
    2005: os.path.join(DataFolder, "Tulare.gdb", "LU_2005.tif"),
    2020: os.path.join(DataFolder, "Tulare.gdb", "LU_2005.tif"),
    2035: os.path.join(DataFolder, "Tulare.gdb", "LU_2005.tif"),
    2050: os.path.join(DataFolder, "Tulare.gdb", "LU_2005.tif"),
}