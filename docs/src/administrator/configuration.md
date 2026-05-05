---
title: Configuration
summary: Environment variables and settings for Cloud Native GIS
---

# Configuration

Cloud Native GIS is configured through environment variables and Django settings.

## Environment Variables

### Core Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DEBUG` | Enable debug mode | `False` | No |
| `SECRET_KEY` | Django secret key | - | Yes |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost` | Yes (prod) |

### Database Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Full database URL | - |
| `DATABASE_NAME` | Database name | `django` |
| `DATABASE_USERNAME` | Database user | `docker` |
| `DATABASE_PASSWORD` | Database password | `docker` |
| `DATABASE_HOST` | Database host | `db` |
| `DATABASE_PORT` | Database port | `5432` |

### Security Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `CSRF_TRUSTED_ORIGINS` | Trusted origins for CSRF | - |
| `CORS_ALLOWED_ORIGINS` | Allowed CORS origins | - |
| `CORS_ALLOW_ALL_ORIGINS` | Allow all CORS origins | `False` |

### Static Files

| Variable | Description | Default |
|----------|-------------|---------|
| `STATIC_URL` | Static files URL | `/static/` |
| `STATIC_ROOT` | Static files directory | `/home/web/static` |
| `MEDIA_URL` | Media files URL | `/media/` |
| `MEDIA_ROOT` | Media files directory | `/home/web/media` |

### Maputnik Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `MAPUTNIK_URL` | External Maputnik URL | - |

## Django Settings

### Basic Configuration

```python
# settings.py
from cloud_native_gis.settings import *

# Override settings as needed
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.environ.get('SECRET_KEY')
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
```

### REST Framework

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
}
```

### CORS Configuration

```python
CORS_ALLOWED_ORIGINS = [
    "https://your-frontend.com",
    "http://localhost:3000",
]

# Or allow all (not recommended for production)
CORS_ALLOW_ALL_ORIGINS = True
```

### Logging

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': '/var/log/cloudnativegis/app.log',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'cloud_native_gis': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

## Example `.env` File

```bash
# =============================================================================
# Django Core
# =============================================================================
DEBUG=False
SECRET_KEY=your-super-secret-key-change-this-in-production
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# =============================================================================
# Database (PostGIS)
# =============================================================================
DATABASE_NAME=cloudnativegis
DATABASE_USERNAME=postgres
DATABASE_PASSWORD=your-secure-password
DATABASE_HOST=db
DATABASE_PORT=5432

# =============================================================================
# Security
# =============================================================================
CSRF_TRUSTED_ORIGINS=https://your-domain.com
CORS_ALLOWED_ORIGINS=https://your-frontend.com

# =============================================================================
# Static & Media
# =============================================================================
STATIC_URL=/static/
MEDIA_URL=/media/

# =============================================================================
# Maputnik (optional)
# =============================================================================
# MAPUTNIK_URL=http://localhost:8888
```

## Configuration Best Practices

1. **Never commit `.env` files** to version control
2. **Use strong secrets** for `SECRET_KEY` in production
3. **Limit `ALLOWED_HOSTS`** to actual domains
4. **Configure CORS carefully** for API security
5. **Enable logging** for troubleshooting
6. **Use environment-specific settings** (dev, staging, prod)

---

Made with :heart: by [Kartoza](https://kartoza.com) | [Donate!](https://github.com/sponsors/kartoza) | [GitHub](https://github.com/kartoza/CloudNativeGIS)
