#!/bin/bash

# Start script for development
echo "Starting Veterinary Clinic Platform Backend..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please update the .env file with your configuration before running again."
    exit 1
fi

# Start with Docker Compose
echo "Starting services with Docker Compose..."
docker-compose up --build