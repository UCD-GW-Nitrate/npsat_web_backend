"""
Generated by 'django-admin startproject' using Django 2.1.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

from npsat_backend.local_settings import *

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'npsat_manager',
    'rest_framework',
    'rest_framework.authtoken',
]

if DEBUG:
    INSTALLED_APPS += ('corsheaders', )

CORS_ORIGIN_ALLOW_ALL = DEBUG
CORS_ORIGIN_WHITELIST = (
    'http://npsat.watershed.ucdavis.edu',
    'https://npsat.watershed.ucdavis.edu',
    'http://npsat.watershed.ucdavis.edu:8000',
    'https://npsat.watershed.ucdavis.edu:8000',
    'http://npsat.watershed.ucdavis.edu:8010',
    'https://npsat.watershed.ucdavis.edu:8010',
    'http://npsat.watershed.ucdavis.edu:8009',
    'https://npsat.watershed.ucdavis.edu:8009',
    'http://127.0.0.1',
    'http://127.0.0.1:8000',
    'http://127.0.0.1:8080',
    'http://localhost',
    'http://localhost:8000',
    'http://localhost:8080',
)

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated'
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 1000,
}

#UNAUTHENTICATED_USER = 'public'
#UNAUTHENTICATED_TOKEN = "c4e255c1d9f4404dab05ed27aa2e929cf8f53c42"

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
]

ROOT_URLCONF = 'npsat_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'npsat_backend.wsgi.application'



# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# The following code block sets it up to not email when DEBUG is on, assuming we'll see it. If DEBUG is off, then it will email too.
EMAIL_WHEN_DEBUG_ON = False
if (EMAIL_WHEN_DEBUG_ON and DEBUG) or not DEBUG:
    EMAIL_DEBUG_HANDLER = {
        'email_warn': {
            'level': "WARNING",
            'class': "django.utils.log.AdminEmailHandler",
        },
        'email_error': {
            'level': "ERROR",
            'class': "django.utils.log.AdminEmailHandler"
        }
    }
    EMAIL_HANDLERS = ['email_error', 'email_warn']
else:
    EMAIL_DEBUG_HANDLER = {}
    EMAIL_HANDLERS = []

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s : %(asctime)s : %(module)s : %(process)d : %(thread)d : %(message)s'
        },
        'simple': {
            'format': '%(levelname)s : %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'level': 'DEBUG',
        },
        'file_debug': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOGGING_FOLDER, 'npsat_web_backend_debug.log'),
            'formatter': 'verbose'
        },
        **EMAIL_DEBUG_HANDLER
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file_debug'] + EMAIL_HANDLERS,
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
        },
        'npsat': {
            'handlers': ['console', 'file_debug'] + EMAIL_HANDLERS,
            'level': 'DEBUG'
        },
    },
}