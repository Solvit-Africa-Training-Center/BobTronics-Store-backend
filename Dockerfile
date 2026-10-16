# Use official lightweight Python 3.12 image
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Set work directory inside the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project source code
COPY . /app/

# Ensure entrypoint script is executable
RUN chmod +x /app/entrypoint.sh

# Expose container port (Render supplies PORT at runtime)
EXPOSE 8000

# Run entrypoint script which handles collectstatic, migrations, and gunicorn
ENTRYPOINT ["/app/entrypoint.sh"]
