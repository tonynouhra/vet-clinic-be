#!/bin/bash
"""
Production deployment script for Veterinary Clinic Backend.
Handles database migrations and production server startup.
"""

set -e  # Exit on any error

echo "🏭 Deploying Veterinary Clinic Backend to Production"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check environment
if [ "$ENVIRONMENT" != "production" ] && [ "$ENVIRONMENT" != "staging" ]; then
    print_error "This script should only be run in production or staging environment"
    print_error "Set ENVIRONMENT=production or ENVIRONMENT=staging"
    exit 1
fi

print_status "Environment: $ENVIRONMENT"

# Check required environment variables
required_vars=("DATABASE_URL" "JWT_SECRET_KEY" "CLERK_SECRET_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        print_error "Required environment variable $var is not set"
        exit 1
    fi
done

print_success "Environment variables validated"

# Install dependencies
print_status "Installing production dependencies..."
pip install --no-cache-dir -r requirements.txt

# Run database migrations
print_status "Running database migrations..."
alembic upgrade head

if [ $? -eq 0 ]; then
    print_success "Database migrations completed"
else
    print_error "Database migrations failed"
    exit 1
fi

# Test database connection
print_status "Testing database connection..."
python scripts/test_db.py > /dev/null 2>&1

if [ $? -eq 0 ]; then
    print_success "Database connection successful"
else
    print_error "Database connection failed"
    exit 1
fi

print_success "Production deployment completed successfully!"

# Start production server
print_status "Starting production server..."
print_status "Server will be available on the configured port"

echo ""
echo "=================================================="

# Start gunicorn for production
if command -v gunicorn &> /dev/null; then
    print_status "Starting with Gunicorn..."
    gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
else
    print_warning "Gunicorn not found, starting with Uvicorn..."
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
fi