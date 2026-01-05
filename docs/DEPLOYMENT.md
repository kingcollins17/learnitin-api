# Deployment Guide

## Production Considerations

### Environment Variables

Create a production `.env` file with secure values:

```bash
# Application Settings
APP_NAME=LearnItIn API
APP_VERSION=1.0.0
DEBUG=False
API_V1_PREFIX=/api/v1

# Security - Generate a strong secret key
SECRET_KEY=<generate-strong-random-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database - Use PostgreSQL in production
DATABASE_URL=postgresql://user:password@localhost:5432/learnitin

# OpenAI / LangChain
OPENAI_API_KEY=<your-production-key>

# CORS - Update with your frontend domain
BACKEND_CORS_ORIGINS=["https://yourdomain.com"]
```

### Generate Secret Key

```python
import secrets
print(secrets.token_urlsafe(32))
```

### Database

#### PostgreSQL Setup

1. Install PostgreSQL:
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql
```

2. Create database:
```bash
sudo -u postgres psql
CREATE DATABASE learnitin;
CREATE USER learnitin_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE learnitin TO learnitin_user;
\q
```

3. Update `DATABASE_URL` in `.env`:
```
DATABASE_URL=postgresql://learnitin_user:your_password@localhost:5432/learnitin
```

4. Install psycopg2:
```bash
pip install psycopg2-binary
```

5. Initialize database:
```bash
python -m app.db.init_db
```

## Deployment Options

### Option 1: Docker

#### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### docker-compose.yml
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://learnitin_user:password@db:5432/learnitin
    depends_on:
      - db
    volumes:
      - .:/app
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=learnitin
      - POSTGRES_USER=learnitin_user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

#### Build and Run
```bash
docker-compose up -d
```

### Option 2: Systemd Service (Linux)

1. Create service file `/etc/systemd/system/learnitin-api.service`:
```ini
[Unit]
Description=LearnItIn API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/learnitin-api
Environment="PATH=/var/www/learnitin-api/venv/bin"
ExecStart=/var/www/learnitin-api/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

2. Enable and start:
```bash
sudo systemctl enable learnitin-api
sudo systemctl start learnitin-api
sudo systemctl status learnitin-api
```

### Option 3: Nginx + Gunicorn

1. Install Gunicorn:
```bash
pip install gunicorn
```

2. Run with Gunicorn:
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

3. Configure Nginx:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

4. Enable HTTPS with Let's Encrypt:
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### Option 4: Cloud Platforms

#### Heroku
```bash
# Install Heroku CLI
# Create Procfile
echo "web: uvicorn app.main:app --host 0.0.0.0 --port \$PORT" > Procfile

# Deploy
heroku create learnitin-api
git push heroku main
heroku config:set SECRET_KEY=your_secret_key
heroku config:set OPENAI_API_KEY=your_openai_key
```

#### AWS Elastic Beanstalk
```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p python-3.11 learnitin-api

# Create environment
eb create learnitin-api-env

# Deploy
eb deploy
```

#### Google Cloud Run
```bash
# Build and deploy
gcloud builds submit --tag gcr.io/PROJECT_ID/learnitin-api
gcloud run deploy learnitin-api --image gcr.io/PROJECT_ID/learnitin-api --platform managed
```

## Security Checklist

- [ ] Set `DEBUG=False` in production
- [ ] Use strong `SECRET_KEY`
- [ ] Use HTTPS/TLS
- [ ] Configure CORS properly
- [ ] Use PostgreSQL or production database
- [ ] Set up database backups
- [ ] Implement rate limiting
- [ ] Use environment variables for secrets
- [ ] Keep dependencies updated
- [ ] Set up monitoring and logging
- [ ] Configure firewall rules
- [ ] Use strong database passwords
- [ ] Implement API key rotation
- [ ] Set up automated security scanning

## Performance Optimization

1. **Use Connection Pooling:**
```python
# In app/db/session.py
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=0
)
```

2. **Enable Caching:**
```bash
pip install redis
```

3. **Add CDN for static files**

4. **Implement request rate limiting**

5. **Use async database drivers**

## Monitoring

### Logging
```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

### Health Checks
Already implemented at `/health` endpoint.

### Metrics
Consider integrating:
- Prometheus
- Grafana
- Sentry for error tracking

## Backup Strategy

1. **Database Backups:**
```bash
# PostgreSQL
pg_dump -U learnitin_user learnitin > backup.sql

# Automated with cron
0 2 * * * pg_dump -U learnitin_user learnitin > /backups/learnitin-$(date +\%Y\%m\%d).sql
```

2. **Application Backups:**
```bash
tar -czf learnitin-api-backup.tar.gz /var/www/learnitin-api
```

## Troubleshooting

### Check Logs
```bash
# Systemd service
sudo journalctl -u learnitin-api -f

# Docker
docker-compose logs -f api
```

### Database Connection Issues
- Verify `DATABASE_URL` in `.env`
- Check database is running
- Verify user permissions

### Performance Issues
- Check database query performance
- Monitor CPU/memory usage
- Review API response times
- Check for N+1 query problems
