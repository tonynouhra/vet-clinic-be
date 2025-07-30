# Deployment Documentation

This directory contains deployment guides and configuration for the vet-clinic-be project.

## Deployment Options

### Development Environment
- **Local Development**: Docker Compose setup
- **Development Server**: Direct Python execution
- **Testing Environment**: Isolated test database

### Production Environment
- **Container Deployment**: Docker with orchestration
- **Cloud Deployment**: AWS/GCP/Azure configurations
- **Database**: Managed PostgreSQL service
- **Caching**: Redis cluster
- **Background Tasks**: Celery workers

## Quick Start

### Local Development
```bash
# Clone repository
git clone <repository-url>
cd vet-clinic-be

# Setup environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start services
docker-compose up -d

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

### Production Deployment
```bash
# Build container
docker build -t vet-clinic-be .

# Deploy with docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

## Documentation Files

- [**docker.md**](./docker.md) - Docker deployment guide
- [**production.md**](./production.md) - Production deployment
- [**monitoring.md**](./monitoring.md) - Monitoring and logging

## Environment Configuration

### Required Environment Variables
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# Redis
REDIS_URL=redis://localhost:6379/0

# Clerk Authentication
CLERK_SECRET_KEY=your_clerk_secret_key

# Application
SECRET_KEY=your_secret_key
DEBUG=false
ENVIRONMENT=production
```

### Optional Configuration
```bash
# Sentry (Error Tracking)
SENTRY_DSN=your_sentry_dsn

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email
SMTP_PASSWORD=your_password

# File Storage (Supabase)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

## Health Checks

The application provides health check endpoints:

- **Basic Health**: `GET /health`
- **Detailed Health**: `GET /health/detailed`
- **Database Health**: `GET /health/database`
- **Redis Health**: `GET /health/redis`

## Scaling Considerations

### Horizontal Scaling
- **API Servers**: Multiple FastAPI instances behind load balancer
- **Background Workers**: Multiple Celery workers
- **Database**: Read replicas for query scaling

### Vertical Scaling
- **CPU**: Multi-core processing with async/await
- **Memory**: Connection pooling and caching
- **Storage**: SSD storage for database performance

## Security

### Production Security Checklist
- [ ] HTTPS/TLS encryption enabled
- [ ] Database connections encrypted
- [ ] Environment variables secured
- [ ] API rate limiting configured
- [ ] CORS properly configured
- [ ] Security headers implemented
- [ ] Dependency vulnerabilities scanned
- [ ] Access logs enabled

## Monitoring

### Application Metrics
- **Performance**: Response times, throughput
- **Errors**: Error rates, exception tracking
- **Resources**: CPU, memory, disk usage
- **Database**: Query performance, connection pool

### Alerting
- **Critical**: Database down, high error rates
- **Warning**: High response times, resource usage
- **Info**: Deployment notifications, scheduled tasks

## Backup and Recovery

### Automated Backups
- **Database**: Daily full backups, hourly incrementals
- **Files**: Regular file storage backups
- **Configuration**: Infrastructure as code backups

### Disaster Recovery
- **RTO**: Recovery Time Objective < 4 hours
- **RPO**: Recovery Point Objective < 1 hour
- **Testing**: Monthly disaster recovery drills