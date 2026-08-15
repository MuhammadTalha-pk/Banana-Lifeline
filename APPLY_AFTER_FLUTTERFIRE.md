# Firebase Options Integration Patch

Apply this patch AFTER running:

flutterfire configure --project=banana-lifeline --platforms=android

Important:
- Keep your generated `mobile/lib/firebase_options.dart`.
- This patch does NOT contain or overwrite `firebase_options.dart`.
- It changes `main.dart` to use `DefaultFirebaseOptions.currentPlatform`.
- Firebase values are no longer required in `config/dev.json`.
- `config/dev.json` is now only for the AI backend URL and API prefix.

After copying the files into your project root, run:

cd mobile
flutter clean
flutter pub get
flutter analyze

Do not run the complete app until Firebase Authentication and Firestore are enabled in Firebase Console.
