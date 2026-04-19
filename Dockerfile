# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Copy requirements.txt and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application app
COPY app.py .

# Expose port 5000 for Flask
EXPOSE 5000

# Set environment variable for Flask
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Run the application
CMD ["python", "app.py"]
