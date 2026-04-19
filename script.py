import cv2
import numpy as np
import json
import os
import base64
import tempfile
from flask import Flask, request, jsonify
from sklearn.cluster import KMeans
import mediapipe as mp

# Initialize Flask app
app = Flask(__name__)

# Configure upload limits for Render free tier (512MB RAM)
# Max 5MB per request to prevent memory issues
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB


class SelfieAnalyzer:
    """
    A class for analyzing selfies to extract various features like skin tone,
    color tone, brightness, and face shape using MediaPipe Face Mesh.
    """

    # Key landmark indices for face shape measurement
    FOREHEAD_TOP = 10
    CHIN_BOTTOM = 152
    LEFT_CHEEK = 234
    RIGHT_CHEEK = 454
    LEFT_JAW = 172
    RIGHT_JAW = 397
    LEFT_FOREHEAD = 71
    RIGHT_FOREHEAD = 301
    LEFT_CHEEKBONE = 116
    RIGHT_CHEEKBONE = 345

    # Skin sample regions
    SKIN_REGIONS = {
        'forehead': [10, 67, 69, 104, 108, 109, 151, 299, 337, 338],
        'left_cheek': [116, 117, 118, 119, 120, 121, 123, 126, 142, 203],
        'right_cheek': [345, 346, 347, 348, 349, 350, 352, 355, 371, 423],
    }

    def __init__(self, k=3, max_size=720):
        self.k = k
        self.max_size = max_size  # Reduced from 1024 to 720 for Render free tier memory optimization
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )

    def _resize(self, img):
        h, w = img.shape[:2]
        if max(h, w) <= self.max_size:
            return img
        scale = self.max_size / max(h, w)
        return cv2.resize(img, (int(w * scale), int(h * scale)))

    def _get_landmarks(self, img):
        results = self.face_mesh.process(img)
        if not results.multi_face_landmarks:
            return None
        landmarks = results.multi_face_landmarks[0]
        h, w = img.shape[:2]
        return [(int(lm.x * w), int(lm.y * h)) for lm in landmarks.landmark]

    def _sample_skin_colors(self, img, landmarks):
        h, w = img.shape[:2]
        skin_pixels = []

        for region_name, indices in self.SKIN_REGIONS.items():
            for idx in indices:
                cx, cy = landmarks[idx]
                for dx in range(-3, 4):
                    for dy in range(-3, 4):
                        px, py = cx + dx, cy + dy
                        if 0 <= px < w and 0 <= py < h:
                            skin_pixels.append(img[py, px])

        return np.array(skin_pixels)

    def dominant_colors(self, img, landmarks):
        skin_pixels = self._sample_skin_colors(img, landmarks)
        if len(skin_pixels) < self.k:
            skin_pixels = img.reshape(-1, 3)

        pixels = skin_pixels.astype(np.float32)
        km = KMeans(n_clusters=self.k, random_state=42, n_init=10).fit(pixels)
        counts = np.bincount(km.labels_)
        percentages = counts / len(pixels) * 100
        order = np.argsort(percentages)[::-1]

        return [
            {
                'hex': '#%02x%02x%02x' % tuple(km.cluster_centers_[i].astype(int)),
                'percentage': round(percentages[i], 2)
            }
            for i in order
        ]

    def skin_tone(self, colors):
        if not colors:
            return 'neutral'

        warm_score = 0.0
        cool_score = 0.0

        for color_data in colors[:3]:
            hex_color = color_data['hex']
            weight = color_data['percentage'] / 100.0
            r, g, b = [int(hex_color[j:j+2], 16) for j in (1, 3, 5)]

            rb_diff = r - b
            yellow_component = (r + g) / 2 - b

            if rb_diff > 30 and yellow_component > 20:
                warm_score += weight * 1.5
            elif rb_diff > 15:
                warm_score += weight
            elif rb_diff < -10:
                cool_score += weight * 1.5
            elif rb_diff < 5:
                cool_score += weight * 0.7

            if r > 150 and b > 120 and abs(r - b) < 40 and g < r:
                cool_score += weight * 0.8

            if r > 140 and g > 110 and b < 100:
                warm_score += weight * 1.2

        if warm_score > cool_score * 1.3:
            return 'warm'
        elif cool_score > warm_score * 1.3:
            return 'cool'
        else:
            return 'neutral'

    def brightness(self, img):
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
        brightness_value = np.mean(hsv[:, :, 2])

        if brightness_value < 85:
            level = 'low'
        elif brightness_value < 170:
            level = 'medium'
        else:
            level = 'high'

        return round(brightness_value, 2), level

    def face_shape(self, img, landmarks):
        if landmarks is None:
            return 'not_detected'

        def dist(a, b):
            return np.sqrt(
                (landmarks[a][0] - landmarks[b][0]) ** 2 +
                (landmarks[a][1] - landmarks[b][1]) ** 2
            )

        face_length = dist(self.FOREHEAD_TOP, self.CHIN_BOTTOM)
        face_width = dist(self.LEFT_CHEEK, self.RIGHT_CHEEK)
        forehead_width = dist(self.LEFT_FOREHEAD, self.RIGHT_FOREHEAD)
        jaw_width = dist(self.LEFT_JAW, self.RIGHT_JAW)
        cheekbone_width = dist(self.LEFT_CHEEKBONE, self.RIGHT_CHEEKBONE)

        length_to_width = face_length / face_width if face_width > 0 else 1.0
        forehead_to_jaw = forehead_width / jaw_width if jaw_width > 0 else 1.0
        cheekbone_to_jaw = cheekbone_width / jaw_width if jaw_width > 0 else 1.0
        forehead_to_cheekbone = forehead_width / cheekbone_width if cheekbone_width > 0 else 1.0

        if length_to_width > 1.45:
            return 'oblong'

        if length_to_width < 1.15 and 0.85 < forehead_to_jaw < 1.15:
            return 'round'

        if length_to_width < 1.25 and forehead_to_jaw < 1.15 and jaw_width >= cheekbone_width * 0.88:
            return 'square'

        if forehead_to_jaw > 1.25 or (forehead_to_cheekbone > 0.95 and cheekbone_to_jaw > 1.2):
            return 'heart'

        if cheekbone_to_jaw > 1.15 and forehead_to_cheekbone < 0.9:
            return 'diamond'

        return 'oval'

    def process(self, image_path):
        img = cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_BGR2RGB)
        if img is None:
            raise FileNotFoundError(f"Image not found: {image_path}")

        img = self._resize(img)
        landmarks = self._get_landmarks(img)

        if landmarks:
            colors = self.dominant_colors(img, landmarks)
            color_tone = self.skin_tone(colors)
            face_structure = self.face_shape(img, landmarks)
        else:
            pixels = img.reshape(-1, 3).astype(np.float32)
            km = KMeans(n_clusters=self.k, random_state=42, n_init=10).fit(pixels)
            counts = np.bincount(km.labels_)
            percentages = counts / len(pixels) * 100
            order = np.argsort(percentages)[::-1]

            colors = [
                {
                    'hex': '#%02x%02x%02x' % tuple(km.cluster_centers_[i].astype(int)),
                    'percentage': round(percentages[i], 2)
                }
                for i in order
            ]

            color_tone = 'unknown'
            face_structure = 'not_detected'

        brightness_value, brightness_level = self.brightness(img)

        return {
            'brightness_value': brightness_value,
            'brightness_level': brightness_level,
            'skin_tone': color_tone,
            'face_shape': face_structure,
            'dominant_skin_colors': colors
        }


@app.route('/analyze', methods=['POST'])
def analyze():
    """
    REST API endpoint to analyze a selfie image.

    Expects a POST request with an 'image' file.
    Maximum file size: 5MB

    Returns:
        JSON: Analysis results including the original image as base64.
    """
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400

    # Validate file size (max 5MB for Render free tier memory limit)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    if file_size > MAX_FILE_SIZE:
        return jsonify({'error': 'Image too large (max 5MB)'}), 400

    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
        file.save(temp_file.name)
        temp_path = temp_file.name

    try:
        analyzer = SelfieAnalyzer()
        result = analyzer.process(temp_path)

        img = cv2.imread(temp_path)
        _, buffer = cv2.imencode('.jpg', img)
        img_base64 = base64.b64encode(buffer).decode('utf-8')

        result['image'] = img_base64
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        image_path = sys.argv[2] if len(sys.argv) > 2 else 'selfie.jpg'
        result = SelfieAnalyzer(k=3).process(image_path)
        print(json.dumps(result, indent=2))
    else:
        app.run(debug=True)