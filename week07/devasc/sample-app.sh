#!/bin/bash
set -e

# Create directories
mkdir -p tempdir/templates tempdir/static

# Copy files
cp sample_app.py tempdir/
cp -r templates/* tempdir/templates/ 2>/dev/null || true
cp -r static/* tempdir/static/ 2>/dev/null || true

# Write Dockerfile
cat << 'EOF' > tempdir/Dockerfile
FROM python:3.11-slim
RUN pip install --no-cache-dir --progress-bar off flask gunicorn
WORKDIR /home/myapp
COPY ./static /home/myapp/static/
COPY ./templates /home/myapp/templates/
COPY sample_app.py /home/myapp/
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "1", "sample_app:sample"]
EOF

# Clean container
docker rm -f samplerunning 2>/dev/null || true

# Build without cache from explicit folder path
docker build --no-cache -t sampleapp tempdir/

# Run container
docker run -d -p 8080:8080 --name samplerunning sampleapp

# Verify status
docker ps -a
