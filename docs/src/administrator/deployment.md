---
title: Deployment Guide
summary: Deploying Cloud Native GIS
---

# Deployment Guide

This guide covers various deployment options for Cloud Native GIS.

## Docker Deployment (Recommended)

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Git

### Step-by-Step Installation

```bash
# 1. Clone the repository
git clone https://github.com/kartoza/CloudNativeGIS
cd CloudNativeGIS

# 2. Initialize submodules
git submodule update --init --recursive

# 3. Copy configuration templates
cp deployment/.template.env deployment/.env
cp deployment/docker-compose.override.template deployment/docker-compose.override.yml

# 4. Edit environment variables
nano deployment/.env

# 5. Start the application
make up
```

### Docker Services

| Service | Description | Port |
|---------|-------------|------|
| `nginx` | Reverse proxy | 80 |
| `django` | Application server | 5000 |
| `db` | PostgreSQL/PostGIS | 5432 |
| `dev` | Development server | 5000 |

### Verifying Installation

1. Open `http://localhost/` in your browser
2. Access admin at `http://localhost/admin/`
3. Default credentials are in your `.env` file

## Production Deployment

### Using Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  nginx:
    image: kartoza/cloud_native_gis:latest
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - django

  django:
    image: kartoza/cloud_native_gis:latest
    restart: always
    env_file:
      - .env.prod
    depends_on:
      - db

  db:
    image: kartoza/postgis:15-3.3
    restart: always
    volumes:
      - pgdata:/var/lib/postgresql/data
    env_file:
      - .env.prod

volumes:
  pgdata:
```

### Environment Variables for Production

```bash
# .env.prod
DEBUG=False
SECRET_KEY=your-very-secure-secret-key
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DATABASE_URL=postgis://user:password@db:5432/cloudnativegis
CSRF_TRUSTED_ORIGINS=https://your-domain.com
```

### SSL/TLS Configuration

For HTTPS, use Let's Encrypt with certbot:

```bash
# Install certbot
apt install certbot python3-certbot-nginx

# Obtain certificate
certbot --nginx -d your-domain.com
```

## Kubernetes Deployment

### Helm Chart (Coming Soon)

A Helm chart for Kubernetes deployment is planned for future releases.

### Basic Kubernetes Manifests

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cloud-native-gis
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cloud-native-gis
  template:
    metadata:
      labels:
        app: cloud-native-gis
    spec:
      containers:
      - name: django
        image: kartoza/cloud_native_gis:latest
        ports:
        - containerPort: 5000
        envFrom:
        - secretRef:
            name: cloud-native-gis-secrets
```

## Django Library Integration

### Installation

```bash
pip install cloud-native-gis
```

### Django Settings

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    # Cloud Native GIS
    'cloud_native_gis',
    # Required dependencies
    'rest_framework',
    'rest_framework_gis',
    'corsheaders',
]

# Database with PostGIS
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'your_database',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### URL Configuration

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('gis/', include('cloud_native_gis.urls')),
]
```

### Run Migrations

```bash
python manage.py migrate
```

## Scaling

### Horizontal Scaling

For high-traffic deployments:

1. Use a load balancer (nginx, HAProxy, or cloud LB)
2. Run multiple Django instances
3. Use Redis for caching and Celery broker
4. Consider a managed PostgreSQL service

### Performance Tuning

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
    }
}

# Tile caching
TILE_CACHE_TIMEOUT = 3600  # 1 hour
```

---

Made with :heart: by [Kartoza](https://kartoza.com) | [Donate!](https://github.com/sponsors/kartoza) | [GitHub](https://github.com/kartoza/CloudNativeGIS)
