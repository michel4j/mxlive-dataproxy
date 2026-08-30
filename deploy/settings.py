import os

ALLOWED_HOSTS = ['*']

DEBUG = True
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'dataserver',
        'USER': 'dataserver',
        'PASSWORD': os.getenv('DATABASE_PASSWORD'),
        'HOST': 'database',
        'PORT': '5432'
    }
}

ADMINS = [
    ('Your Name', 'your.email@example.ca'),
]

# Define hosts allowed to fetch data from here
CORS_ALLOWED_ORIGINS = [
    'http://127.0.0.1',
    'http://localhost',
    'https://localhost',
]

# Allowlisted directories, only paths in these directories can be served
DOWNLOAD_DIRS = ['/data', '/home', '/tmp']
DOWNLOAD_FRAME_COLORMAP = 'magma'
