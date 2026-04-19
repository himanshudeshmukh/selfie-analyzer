# Use official Python runtime with more packages available
FROM python:3.10-bullseye

# Set working directory in container
WORKDIR /app

# Install system dependencies for opencv-python-headless and mediapipe
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libopengl0 \
    libglvnd0 \
    && rm -rf /var/lib/apt/lists/*

# Set OpenCV to use software rendering instead of GPU
ENV LIBGL_ALWAYS_INDIRECT=1

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
