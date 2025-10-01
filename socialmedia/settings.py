# --------------------------------------------------
# 0.  Drop-in env loader
# --------------------------------------------------
import os
from dotenv import load_dotenv
load_dotenv()          # reads .env from same dir

# --------------------------------------------------
# 1.  Core Django
# --------------------------------------------------
from datetime import timedelta
from pathlib import Path
from cassandra.auth import PlainTextAuthProvider

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY                  = os.getenv('SECRET_KEY', 'django-insecure-9g07l^3)d-&ujs#r!)+#k_ai=06f@wh0fsh^58nrgv3g7&28%r')
DEBUG                       = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS               = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '*').split(',') if h.strip()]

# --------------------------------------------------
# 2.  Installed Apps (unchanged)
# --------------------------------------------------
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
THIRD_PARTY_APPS = [
    'strawberry.django',
    'corsheaders',
    'django_cassandra_engine',
    'channels',
    'graphql_jwt.refresh_token.apps.RefreshTokenConfig',
]
LOCAL_APPS = [
    'apps.users.apps.UsersConfig',
    'apps.graphql_api',
    'apps.chat.apps.ChatConfig',
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880

# --------------------------------------------------
# 3.  Middleware (unchanged)
# --------------------------------------------------
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'socialmedia.urls'
AUTH_USER_MODEL = 'users.User'

# --------------------------------------------------
# 4.  Templates (unchanged)
# --------------------------------------------------
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

# --------------------------------------------------
# 5.  ASGI (unchanged)
# --------------------------------------------------
ASGI_APPLICATION = 'socialmedia.asgi.application'

# --------------------------------------------------
# 6.  PostgreSQL
# --------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_NAME', 'socialmedia'),
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'postgres'),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': int(os.getenv('POSTGRES_PORT', 5432)),
    }
}

# --------------------------------------------------
# 7.  Cassandra
# --------------------------------------------------
_cassandra_auth = PlainTextAuthProvider(
    username=os.getenv('CASSANDRA_USER', 'cassandra'),
    password=os.getenv('CASSANDRA_PASSWORD', 'cassandra'),
)
CASSANDRA_DATABASES = {
    'cassandra': {
        'ENGINE':   'django_cassandra_engine',
        'NAME':     os.getenv('CASSANDRA_KEYSPACE', 'socialmedia'),
        'TEST_NAME':'test_socialmedia',
        'HOST':     os.getenv('CASSANDRA_HOST', '127.0.0.1'),
        'PORT':     int(os.getenv('CASSANDRA_PORT', 9042)),
        'OPTIONS': {
            'replication': {
                'strategy_class': 'SimpleStrategy',
                'replication_factor': 1,
            },
            'consistency': 1,
            'retry_connect': True,
            'auth_provider': _cassandra_auth,
            'connection': {
                'connect_timeout': 20,
                'control_connection_timeout': 20,
            },
        }
    }
}
DATABASES.update(CASSANDRA_DATABASES)

# --------------------------------------------------
# 8.  Redis / Channels / Celery
# --------------------------------------------------
_redis_host = os.getenv('REDIS_HOST', 'localhost')
_redis_port = int(os.getenv('REDIS_PORT', 6379))

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': f'redis://{_redis_host}:{_redis_port}/{os.getenv("REDIS_DB_CACHE", 1)}',
    }
}
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {'hosts': [(_redis_host, _redis_port)]},
    },
}
BLACKLIST_REDIS_URL = f'redis://{_redis_host}:{_redis_port}/{os.getenv("REDIS_DB_BLACKLIST", 2)}'
CELERY_BROKER_URL   = f'redis://{_redis_host}:{_redis_port}/{os.getenv("REDIS_DB_CHANNELS", 0)}'
CELERY_RESULT_BACKEND = CELERY_BROKER_URL

# --------------------------------------------------
# 9.  Password validators (unchanged)
# --------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --------------------------------------------------
# 10.  Internationalization (unchanged)
# --------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --------------------------------------------------
# 11.  Static / Media (unchanged)
# --------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --------------------------------------------------
# 12.  CORS (unchanged)
# --------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = True
CSRF_COOKIE_SAMESITE  = 'Lax'
SESSION_COOKIE_SAMESITE = 'Lax'
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = ['http://localhost:5173']

# --------------------------------------------------
# 13.  GraphQL JWT
# --------------------------------------------------
JWT_EXPIRATION_DELTA      = timedelta(minutes=int(os.getenv('JWT_EXPIRATION_MINUTES', 120)))
JWT_REFRESH_EXPIRATION_DELTA = timedelta(days=int(os.getenv('JWT_REFRESH_EXPIRATION_DAYS', 30)))

GRAPHQL_JWT = {
    'JWT_VERIFY_EXPIRATION': True,
    'JWT_LONG_RUNNING_REFRESH_TOKEN': True,
    'JWT_EXPIRATION_DELTA': JWT_EXPIRATION_DELTA,
    'JWT_REFRESH_EXPIRATION_DELTA': JWT_REFRESH_EXPIRATION_DELTA,
    'JWT_ERROR_HANDLER': 'apps.graphql_api.utils.jwt_error_handler',
}
AUTHENTICATION_BACKENDS = [
    'graphql_jwt.backends.JSONWebTokenBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# --------------------------------------------------
# 14.  Cloudflare Turnstile
# --------------------------------------------------
TURNSTILE_SITE_KEY   = os.getenv('TURNSTILE_SITE_KEY')
TURNSTILE_SECRET_KEY = os.getenv('TURNSTILE_SECRET_KEY')

# --------------------------------------------------
# 15.  Email (Gmail SMTP)
# --------------------------------------------------
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL  = os.getenv('DEFAULT_FROM_EMAIL')