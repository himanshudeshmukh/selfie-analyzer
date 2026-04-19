import cv2
import numpy as np
import json
import os
import base64
import tempfile
from flask import Flask, request, jsonify
from sklearn.cluster import KMeans

# Initialize Flask app
app = Flask(__name__)

class SelfieAnalyzer:
    """
    A class for analyzing selfies to extract various features like dominant colors,
    color tone, brightness, and face shape.
    """

    def __init__(self, k=3, max_size=1024):
        """
        Initialize the SelfieAnalyzer.

        Args:
            k (int): Number of dominant colors to extract.
            max_size (int): Maximum size for image resizing to optimize processing.
        """
        self.k = k
        self.max_size = max_size
        # Load Haar cascade for face detection
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    def _resize(self, img):
        """
        Resize the image if it exceeds the maximum size to improve performance.

        Args:
            img (numpy.ndarray): Input image.

        Returns:
            numpy.ndarray: Resized image if necessary, otherwise original.
        """
        h, w = img.shape[:2]
        if max(h, w) <= self.max_size:
            return img
        scale = self.max_size / max(h, w)
        return cv2.resize(img, (int(w * scale), int(h * scale)))

    def dominant_colors(self, img):
        """
        Extract the dominant colors from the image using K-Means clustering.

        Args:
            img (numpy.ndarray): Input image in RGB format.

        Returns:
            list: List of dictionaries with hex color and percentage.
        """
        # Reshape image to a list of pixels
        pixels = img.reshape(-1, 3).astype(np.float32)
        # Perform K-Means clustering
        km = KMeans(n_clusters=self.k, random_state=42, n_init=10).fit(pixels)
        # Calculate percentages
        counts = np.bincount(km.labels_)
        percentages = counts / len(pixels) * 100
        # Sort by percentage descending
        order = np.argsort(percentages)[::-1]
        return [
            {
                'hex': '#%02x%02x%02x' % tuple(km.cluster_centers_[i].astype(int)),
                'percentage': round(percentages[i], 2)
            }
            for i in order
        ]

    def color_tone(self, colors):
        """
        Determine the color tone (warm, cool, neutral) based on the dominant color.

        Args:
            colors (list): List of dominant colors.

        Returns:
            str: Color tone ('warm', 'cool', or 'neutral').
        """
        if not colors:
            return 'neutral'
        # Extract RGB from the first (most dominant) color
        hex_color = colors[0]['hex']
        r, g, b = [int(hex_color[i:i+2], 16) for i in (1, 3, 5)]
        # Calculate hue
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        if max_val == min_val:
            hue = 0
        elif max_val == r:
            hue = 60 * ((g - b) / (max_val - min_val))
        elif max_val == g:
            hue = 60 * (2 + (b - r) / (max_val - min_val))
        else:
            hue = 60 * (4 + (r - g) / (max_val - min_val))
        hue = (hue + 360) % 360
        # Determine tone
        if hue <= 60 or hue >= 300:
            return 'warm'
        elif 180 <= hue < 300:
            return 'cool'
        else:
            return 'neutral'

    def brightness(self, img):
        """
        Calculate the brightness value and level of the image.

        Args:
            img (numpy.ndarray): Input image in RGB format.

        Returns:
            tuple: (brightness_value, brightness_level)
        """
        # Convert to HSV and get average value (brightness)
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        brightness_value = np.mean(hsv[:, :, 2])
        # Classify brightness level
        if brightness_value < 85:
            level = 'low'
        elif brightness_value < 170:
            level = 'medium'
        else:
            level = 'high'
        return round(brightness_value, 2), level

    def face_shape(self, img):
        """
        Detect and classify the face shape in the image.

        Args:
            img (numpy.ndarray): Input image in RGB format.

        Returns:
            str: Face shape ('oblong', 'round', 'heart', 'oval', 'square', or 'not_detected').
        """
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        # Detect faces
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)
        if len(faces) == 0:
            return 'not_detected'
        # Use the first detected face
        x, y, w, h = faces[0]
        face_roi = gray[y:y+h, x:x+w]
        aspect_ratio = w / h
        # Threshold the face ROI
        _, thresh = cv2.threshold(face_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            # Calculate roundness using convex hull
            largest_contour = max(contours, key=cv2.contourArea)
            hull = cv2.convexHull(largest_contour)
            hull_area = cv2.contourArea(hull)
            contour_area = cv2.contourArea(largest_contour)
            roundness = contour_area / hull_area if hull_area > 0 else 0.5
        else:
            roundness = 0.5
        # Classify based on aspect ratio and roundness
        if aspect_ratio > 1.3:
            return 'oblong'
        elif aspect_ratio < 0.9:
            return 'heart' if roundness > 0.75 else 'round'
        else:
            return 'oval' if roundness > 0.8 else 'square'

    def process(self, image_path):
        """
        Process the image to extract analysis details.

        Args:
            image_path (str): Path to the input image.

        Returns:
            dict: Dictionary containing analysis results.
        """
        # Load and preprocess the image
        img = cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_BGR2RGB)
        if img is None:
            raise FileNotFoundError(f"Image not found: {image_path}")
        # Resize if necessary
        img = self._resize(img)
        
        # Perform analyses
        colors = self.dominant_colors(img)
        brightness_value, brightness_level = self.brightness(img)
        color_tone = self.color_tone(colors)
        face_structure = self.face_shape(img)
        
        # Return results
        return {
            'brightness_value': brightness_value,
            'brightness_level': brightness_level,
            'color_tone': color_tone,
            'face_structure': face_structure,
            'dominant_colors': colors
        }

@app.route('/analyze', methods=['POST'])
def analyze():
    """
    REST API endpoint to analyze a selfie image.

    Expects a POST request with an 'image' file.

    Returns:
        JSON: Analysis results including the original image as base64.
    """
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400
    
    # Save the uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
        file.save(temp_file.name)
        temp_path = temp_file.name
    
    try:
        # Initialize analyzer and process the image
        analyzer = SelfieAnalyzer()
        result = analyzer.process(temp_path)
        
        # Read the original image and encode to base64
        img = cv2.imread(temp_path)
        _, buffer = cv2.imencode('.jpg', cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        result['image'] = img_base64
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

if __name__ == '__main__':
    # Run the Flask app
    app.run(debug=True)
    result = SelfieAnalyzer(k=3).process('selfie.jpg')
    print(json.dumps(result, indent=2))