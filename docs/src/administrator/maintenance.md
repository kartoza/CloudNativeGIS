---
title: Maintenance
summary: Backup, monitoring, and troubleshooting Cloud Native GIS
---

# Maintenance

This guide covers ongoing maintenance tasks for Cloud Native GIS.

## Backup and Recovery

### Database Backup

#### Using Docker

```bash
# Backup PostgreSQL database
docker compose exec db pg_dump -U postgres cloudnativegis > backup_$(date +%Y%m%d).sql

# Compress backup
gzip backup_$(date +%Y%m%d).sql
```

#### Automated Backups

Create a cron job for regular backups:

```bash
# /etc/cron.d/cloudnativegis-backup
0 2 * * * root docker compose -f /path/to/docker-compose.yml exec -T db pg_dump -U postgres cloudnativegis | gzip > /backups/db_$(date +\%Y\%m\%d).sql.gz
```

### Database Restore

```bash
# Restore from backup
gunzip -c backup_20240101.sql.gz | docker compose exec -T db psql -U postgres cloudnativegis
```

### Media Files Backup

```bash
# Backup media directory
tar -czvf media_backup_$(date +%Y%m%d).tar.gz /path/to/media/
```

## Monitoring

### Health Checks

Cloud Native GIS provides health check endpoints:

```bash
# Check application health
curl http://localhost/health/

# Check database connectivity
curl http://localhost/health/db/
```

### Log Monitoring

#### View Container Logs

```bash
# All logs
docker compose logs -f

# Specific service
docker compose logs -f django

# Last 100 lines
docker compose logs --tail=100 django
```

#### Log Locations

| Service | Log Location |
|---------|-------------|
| Django | Container stdout/stderr |
| Nginx | `/var/log/nginx/` |
| PostgreSQL | Container stdout/stderr |

### Performance Monitoring

#### Database Queries

```sql
-- Check slow queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 seconds';
```

#### Tile Cache Statistics

Monitor cache hit rates through your caching solution (Redis, etc.).

## Updates and Upgrades

### Updating Docker Images

```bash
# Pull latest images
docker compose pull

# Restart with new images
docker compose down
docker compose up -d

# Run migrations
docker compose exec django python manage.py migrate
```

### Updating the Library

```bash
# Upgrade pip package
pip install --upgrade cloud-native-gis

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput
```

## Troubleshooting

### Common Issues

#### Container Won't Start

```bash
# Check container status
docker compose ps

# View logs
docker compose logs django

# Check for port conflicts
netstat -tlnp | grep :5000
```

#### Database Connection Errors

```bash
# Test database connectivity
docker compose exec django python manage.py dbshell

# Check database status
docker compose exec db pg_isready -U postgres
```

#### Migration Errors

```bash
# Show migration status
docker compose exec django python manage.py showmigrations

# Fake a migration if needed
docker compose exec django python manage.py migrate cloud_native_gis --fake 0001_initial
```

#### Static Files Not Loading

```bash
# Collect static files
docker compose exec django python manage.py collectstatic --noinput

# Check nginx configuration
docker compose exec nginx nginx -t
```

### Debug Mode

Enable debug mode temporarily for troubleshooting:

```bash
# In .env
DEBUG=True
```

!!! warning
    Never enable debug mode in production for extended periods.

### Getting Help

1. Check the [GitHub Issues](https://github.com/kartoza/CloudNativeGIS/issues)
2. Review the [Documentation](https://kartoza.github.io/CloudNativeGIS/)
3. Contact [Kartoza Support](https://kartoza.com/contact)

## Security Maintenance

### Regular Updates

1. Update Docker images monthly
2. Update Python dependencies quarterly
3. Apply security patches immediately

### Security Checklist

- [ ] Change default passwords
- [ ] Enable HTTPS
- [ ] Configure firewall rules
- [ ] Set up fail2ban for SSH
- [ ] Enable database SSL
- [ ] Review CORS settings
- [ ] Audit user accounts

---

Made with :heart: by [Kartoza](https://kartoza.com) | [Donate!](https://github.com/sponsors/kartoza) | [GitHub](https://github.com/kartoza/CloudNativeGIS)
