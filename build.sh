#!/usr/bin/env bash
# Build script for Render deployment

set -o errexit

# Install frontend dependencies and build
cd frontend
npm install
npm run build
cd ..

# Install backend dependencies
cd backend
pip install -r requirements.txt
