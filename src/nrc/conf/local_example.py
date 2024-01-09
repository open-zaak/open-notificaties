from pathlib import Path

#
# Any machine specific settings when using development settings.
#

# Automatically figure out the ROOT_DIR and PROJECT_DIR.
DJANGO_PROJECT_DIR = Path(__file__).resolve(strict=True).parents[1]
ROOT_DIR = DJANGO_PROJECT_DIR.parents[1]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "notifications",
        "USER": "notifications",
        "PASSWORD": "notifications",
        "HOST": "",  # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        "PORT": "",  # Set to empty string for default.
    }
}
