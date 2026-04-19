# Flutter App Setup & Configuration

## Quick Start

```bash
cd flutter_app
flutter pub get
flutter run
```

## Before Running

### 1. Update API URL (IMPORTANT)

Open `lib/services/selfie_analyzer_service.dart` and change:

```dart
static const String baseUrl = 'https://your-app-name.onrender.com';
```

To your actual Render deployment URL.

## Platform-Specific Configuration

### Android

- Min SDK: 21
- Target SDK: 33
- Permissions handled automatically by image_picker

### iOS

- Min iOS: 11
- Permissions added to Info.plist

## Emulator/Device Testing

**Android Emulator:**

```bash
flutter emulators --launch Pixel_5_API_31
flutter run
```

**iPhone Simulator:**

```bash
open -a Simulator
flutter run
```

**Physical Device:**

```bash
# Connect device via USB
flutter run
```
