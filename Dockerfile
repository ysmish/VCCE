# Use Python 3.9 as the base image
FROM python:3.9-slim

# Set working directory
WORKDIR /VCCE

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port the application runs on
EXPOSE 5001

# Command to run the application
CMD ["python", "server.py"]