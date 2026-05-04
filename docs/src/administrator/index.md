---
title: Administrator Guide
summary: System administration for Cloud Native GIS
---

# Administrator Guide

This guide covers the installation, configuration, and maintenance of Cloud Native GIS.

## Overview

Cloud Native GIS is a Django-based platform that can be deployed as:

- A standalone application using Docker
- A Django library integrated into existing projects

## Sections

- [Deployment](deployment.md) - Installation and deployment options
- [Configuration](configuration.md) - Environment variables and settings
- [Maintenance](maintenance.md) - Backup, monitoring, and troubleshooting

## System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| CPU | 2 cores |
| RAM | 4 GB |
| Storage | 20 GB SSD |
| OS | Linux (Ubuntu 22.04+, Debian 11+) |

### Recommended Requirements

| Component | Requirement |
|-----------|-------------|
| CPU | 4+ cores |
| RAM | 8+ GB |
| Storage | 100+ GB SSD |
| OS | Linux with Docker |

### Software Dependencies

- **Python**: 3.10, 3.11, or 3.12
- **PostgreSQL**: 13+ with PostGIS 3.0+
- **Docker**: 20.10+ (for containerized deployment)
- **Node.js**: 18+ (for frontend development)

## Quick Start

### Docker Deployment

```bash
# Clone the repository
git clone https://github.com/kartoza/CloudNativeGIS
cd CloudNativeGIS

# Configure environment
cp deployment/.template.env deployment/.env
cp deployment/docker-compose.override.template deployment/docker-compose.override.yml

# Edit .env with your settings
nano deployment/.env

# Start the application
make up
```

### Django Library Installation

```bash
pip install cloud-native-gis
```

Add to your Django settings:

```python
INSTALLED_APPS = [
    # ...
    'cloud_native_gis',
    # ...
]
```

Add to your URLs:

```python
urlpatterns = [
    # ...
    path('', include('cloud_native_gis.urls')),
]
```

## Security Considerations

1. **Change default credentials** immediately after installation
2. **Use HTTPS** in production
3. **Configure CORS** appropriately for your domain
4. **Set secure environment variables** (see [Configuration](configuration.md))
5. **Regular security updates** for all dependencies

## Support

- [GitHub Issues](https://github.com/kartoza/CloudNativeGIS/issues)
- [Kartoza Support](https://kartoza.com/contact)

---

Made with :heart: by [Kartoza](https://kartoza.com) | [Donate!](https://github.com/sponsors/kartoza) | [GitHub](https://github.com/kartoza/CloudNativeGIS)
