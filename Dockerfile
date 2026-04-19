# Use official Python runtime as a parent image
FROM python:3.10-slim

# Set working directory in container
WORKDIR /app

# Copy requirements.txt and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application script
COPY script.py .

# Expose port 5000 for Flask
EXPOSE 5000

# Set environment variable for Flask
ENV FLASK_APP=script.py
ENV FLASK_ENV=production

# Run the application with Gunicorn (production WSGI server)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "script:app"]
