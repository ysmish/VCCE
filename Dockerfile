# Use Python 3.9 as the base image
FROM python:3.9

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    valgrind \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directory for SSL certificates
RUN mkdir -p /app/certs

# Copy the application code
COPY . .

# Expose the port the application runs on
EXPOSE 5001

# Command to run the application
CMD ["python", "server.py"]