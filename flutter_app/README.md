# Selfie Analyzer Flutter App

A Flutter mobile app that captures or selects selfies and sends them to the Selfie Analyzer API for analysis.

## Features

- 📸 Capture image from camera
- 🖼️ Pick image from gallery
- 🎨 Real-time image preview
- 📊 Display analysis results:
  - Brightness level and value
  - Color tone (warm/cool/neutral)
  - Face shape detection
  - Dominant colors with percentages
  - Original image in response

## Project Structure

```
flutter_app/
├── lib/
│   ├── main.dart                    # Main app and UI
│   └── services/
│       └── selfie_analyzer_service.dart  # API service
├── pubspec.yaml                    # Dependencies
└── README.md
```

## Setup Instructions

### 1. Prerequisites

- Flutter SDK installed ([flutter.dev](https://flutter.dev/docs/get-started/install))
- Xcode (for iOS) or Android Studio (for Android)

### 2. Install Dependencies

```bash
cd flutter_app
flutter pub get
```

### 3. Update API URL

Edit `lib/services/selfie_analyzer_service.dart`:

```dart
static const String baseUrl = 'https://your-app-name.onrender.com';
```

Replace `your-app-name` with your actual Render app URL.

### 4. Android-Specific Setup (if targeting Android)

Add to `android/app/build.gradle`:

```gradle
android {
    compileSdk 33
    ...
}
```

Add to `android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
```

### 5. iOS-Specific Setup (if targeting iOS)

Edit `ios/Podfile` and ensure platform is set to at least iOS 11:

```ruby
post_install do |installer|
  installer.pods_project.targets.each do |target|
    flutter_additional_ios_build_settings(target)
  end
end
```

Add permissions to `ios/Runner/Info.plist`:

```xml
<key>NSCameraUsageDescription</key>
<string>This app needs camera access to capture selfies</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>This app needs photo library access to select images</string>
<key>NSPhotoLibraryAddUsageDescription</key>
<string>This app needs to save images to your photo library</string>
```

## Running the App

### Run on Emulator/Simulator

```bash
flutter run
```

### Run on Physical Device

1. Connect your device via USB
2. Enable USB debugging (Android) or trust the device (iOS)
3. Run:

```bash
flutter run
```

### Build APK (Android)

```bash
flutter build apk --release
```

### Build IPA (iOS)

```bash
flutter build ios --release
```

## How to Use

1. **Select Image**: Click "Gallery" or "Camera" button
2. **Preview**: Image appears in the preview area
3. **Analyze**: Click "Analyze Image" button
4. **View Results**: See analysis results including:
   - Brightness information
   - Color tone
   - Face structure
   - Dominant colors with visual indicators
   - Original image returned from API

## Dependencies

- **http**: For making HTTP requests to the API
- **image_picker**: For picking images from camera/gallery
- **cached_network_image**: For efficient image caching

## Troubleshooting

### Build Issues

```bash
flutter clean
flutter pub get
flutter pub upgrade
```

### Camera/Gallery Not Working

- Ensure permissions are granted in app settings
- Check platform-specific setup above

### API Connection Issues

- Verify API URL in settings
- Check internet connection
- Ensure server is running and accessible

## API Format

The app expects the API to accept:

- **Method**: POST
- **Endpoint**: `/analyze`
- **Body**: `multipart/form-data` with `image` field
- **Response**: JSON with analysis data

## License

BSD 3-Clause License
