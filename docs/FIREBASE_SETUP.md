# Firebase setup

## 1. Create Firebase project

Create a Firebase project for Banana Lifeline and add the Android app package you choose (recommended example: `com.muhammadtalha.bananalifeline`).

Enable:

- Authentication → Email/Password
- Cloud Firestore
- Firebase Storage
- Cloud Messaging

The app uses explicit Firebase values supplied with `--dart-define-from-file`, so it does not ship another user's Firebase project values.

## 2. Deploy rules and indexes

From the `firebase/` folder:

```powershell
firebase login
firebase use --add
firebase deploy --only firestore:rules,firestore:indexes,storage
```

The supplied rules are owner-scoped. The client cannot create AI chat answers or trusted diagnosis fields; those writes are performed by the authenticated FastAPI backend through Firebase Admin.

## 3. Get mobile Firebase values

From Firebase Project Settings → your Android app, collect the project/app values and create:

`mobile/config/dev.json`

from:

`mobile/config/dev.example.json`

Example structure:

```json
{
  "FIREBASE_API_KEY": "<real value>",
  "FIREBASE_APP_ID": "<real Android app id>",
  "FIREBASE_MESSAGING_SENDER_ID": "<real sender id>",
  "FIREBASE_PROJECT_ID": "<real project id>",
  "FIREBASE_STORAGE_BUCKET": "<real storage bucket>",
  "AI_BASE_URL": "http://<PC-LAN-IP>:8000",
  "API_PREFIX": "/api/v1"
}
```

`dev.json` is gitignored.

## 4. Firebase Authentication

The app implements:
- register
- login
- forgot/reset password email
- persistent Firebase session
- profile update
- logout

A real farmer document is written to `users/{uid}` on registration.

## 5. Firestore offline behavior

Firestore persistence is enabled. Previously fetched profile, history, chat, farms, and notifications can be served from cache when connectivity is weak.

New AI diagnosis/chat requests still require connectivity to the configured backend. The UI preserves entered scan/chat content on request failure and allows a stored failed diagnosis to be retried.

## 6. FCM

The app requests notification permission and stores its real device token in `users/{uid}.fcmTokens`.

The backend creates a Firestore notification and attempts FCM delivery only after a real high-risk diagnosis result. It does not generate sample notifications.

## 7. Production notes

- Keep the Firebase Admin service-account JSON outside Git.
- Do not put DeepSeek, Qdrant, or Google Cloud private keys in Flutter.
- Use HTTPS for the production AI backend.
- Tighten CORS to the domains/environments you actually use.
