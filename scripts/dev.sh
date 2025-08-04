#!/bin/bash
"""
Development server startup script for Veterinary Clinic Backend.
Handles database initialization and starts the FastAPI server.
"""

set -e  # Exit on any error

echo "🚀 Starting Veterinary Clinic Backend Development Server"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found!"
    print_status "Creating .env file from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_warning "Please update .env file with your actual values"
    else
        print_error ".env.example not found. Please create .env file manually."
        exit 1
    fi
fi

# Check if virtual environment exists
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    print_warning "Virtual environment not found. Creating one..."
    python3 -m venv venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    print_status "Activated virtual environment (venv)"
elif [ -d ".venv" ]; then
    source .venv/bin/activate
    print_status "Activated virtual environment (.venv)"
fi

# Install dependencies
print_status "Installing dependencies..."
pip install -r requirements.txt

# Test database connection and setup
print_status "Testing database connection..."
if python scripts/test_db.py > /dev/null 2>&1; then
    print_success "Database connection successful"
    
    # Check for schema changes (new tables or columns)
    print_status "Checking for schema changes..."
    python scripts/schema_manager.py --update > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        print_success "Database schema is up to date"
    else
        print_warning "Schema updates were applied"
    fi
else
    print_warning "Database connection failed or tables missing. Setting up database..."
    
    # Initialize database with sample data for development
    print_status "Initializing database..."
    python scripts/init_db.py --seed
    
    if [ $? -eq 0 ]; then
        print_success "Database initialized successfully"
    else
        print_error "Database initialization failed"
        exit 1
    fi
fi

# Start the development server
print_status "Starting FastAPI development server..."
print_status "Server will be available at: http://localhost:8000"
print_status "API documentation: http://localhost:8000/docs"
print_status "Press Ctrl+C to stop the server"

echo ""
echo "=================================================="

# Start uvicorn with reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000