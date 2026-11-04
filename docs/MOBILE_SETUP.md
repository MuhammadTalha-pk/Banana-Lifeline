# Flutter mobile setup

This `mobile/` directory contains the complete Dart source, routing, localization, repositories, Firebase integration, and AI API client. Platform wrappers (`android/`, `ios/`) must be generated with your installed Flutter SDK because platform templates vary with Flutter versions.

## 1. Generate platform wrappers

Open PowerShell:

```powershell
cd C:\Banana-Lifeline\mobile
flutter create . --project-name banana_lifeline --org com.muhammadtalha --platforms=android,ios
flutter pub get
flutter gen-l10n
```

If Flutter asks about overwriting source files, preserve the supplied `lib/`, `pubspec.yaml`, `l10n.yaml`, `analysis_options.yaml`, and `config/` files.

The helper `scripts/bootstrap_mobile.ps1` automates the backup/restore around `flutter create`.

## 2. Android permissions

In `android/app/src/main/AndroidManifest.xml`, add above `<application>`:

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
```

Inside `<manifest>` but outside `<application>` add:

```xml
<queries>
    <intent>
        <action android:name="android.speech.RecognitionService" />
    </intent>
</queries>
```

For **local hackathon testing only**, if `AI_BASE_URL` is plain `http://<LAN-IP>:8000`, set on `<application>`:

```xml
android:usesCleartextTraffic="true"
```

Use HTTPS in production and remove that local-dev allowance.

## 3. iOS permissions

In `ios/Runner/Info.plist` add descriptions for:
- `NSCameraUsageDescription`
- `NSPhotoLibraryUsageDescription`
- `NSMicrophoneUsageDescription`
- `NSSpeechRecognitionUsageDescription`
- `NSLocationWhenInUseUsageDescription`

## 4. Configure real Firebase + backend URL

```powershell
Copy-Item config\dev.example.json config\dev.json
notepad config\dev.json
```

Run:

```powershell
flutter run --dart-define-from-file=config/dev.json
```

## 5. Analyze

```powershell
flutter gen-l10n
flutter analyze
```

## 6. Build Android APK

```powershell
flutter build apk --release --dart-define-from-file=config/dev.json
```

Output:

```text
build\app\outputs\flutter-apk\app-release.apk
```

## What is real in the mobile app

- Firebase farmer accounts/profile
- Firebase farm records
- camera/gallery image selection
- real GPS + reverse geocoded address
- manual location fallback
- exact farm place: farm, plot/sector, row, plant number
- real Storage image/audio upload
- authenticated FastAPI calls with Firebase ID token
- real Firestore scan history
- real chat sessions/messages
- RAG source display
- English/Urdu localization and RTL
- live device speech-to-text
- actual WAV voice-note recording
- backend transcription
- text-to-speech play/pause/stop
- FCM token registration
- real Firestore notifications

No static disease/history/chat values are used as runtime data.
