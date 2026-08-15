# Firestore / Storage data model

The mobile app uses Firebase Authentication UID as the owner key.

## `users/{uid}`

```json
{
  "uid": "<firebase uid>",
  "email": "farmer@example.com",
  "fullName": "Farmer name",
  "phone": "+92...",
  "preferredLanguage": "en",
  "district": "Tando Allahyar",
  "province": "Sindh",
  "farmSize": "5 acres",
  "cropInfo": "Banana / Cavendish",
  "profilePhotoUrl": "https://...",
  "fcmTokens": ["..."],
  "createdAt": "<server timestamp>",
  "updatedAt": "<server timestamp>"
}
```

## `farms/{farmId}`

```json
{
  "ownerId": "<uid>",
  "name": "Main Banana Farm",
  "district": "...",
  "province": "...",
  "size": "...",
  "address": "...",
  "latitude": 25.123,
  "longitude": 68.456,
  "isPrimary": true,
  "updatedAt": "<server timestamp>"
}
```

## `plant_scans/{scanId}`

Created by Flutter with the real uploaded image and location. AI fields are written by the authenticated FastAPI backend through Firebase Admin.

```json
{
  "ownerId": "<uid>",
  "imageUrl": "https://...",
  "storagePath": "users/<uid>/scans/<scanId>.jpg",
  "location": {
    "latitude": 25.123,
    "longitude": 68.456,
    "address": "...",
    "farmName": "Main Farm",
    "plotSector": "Plot B",
    "row": "7",
    "plantNumber": "18"
  },
  "note": "Lower leaves are turning yellow",
  "language": "ur",
  "status": "completed",
  "diagnosis": {
    "label": "panama",
    "displayName": "Suspected Panama disease / Fusarium wilt",
    "confidence": 0.87,
    "severity": "high",
    "status": "completed",
    "description": "...",
    "treatment": [],
    "prevention": [],
    "additionalAdvice": [],
    "expertRecommended": true,
    "warning": "...",
    "sources": []
  },
  "createdAt": "<server timestamp>",
  "updatedAt": "<server timestamp>"
}
```

## `chat_sessions/{sessionId}`

Written by the trusted backend:

```json
{
  "ownerId": "<uid>",
  "title": "Yellow leaves in Plot B",
  "language": "ur",
  "relatedScanId": "<optional scan id>",
  "createdAt": "<timestamp>",
  "updatedAt": "<timestamp>"
}
```

### `chat_sessions/{sessionId}/messages/{messageId}`

```json
{
  "sender": "user",
  "text": "...",
  "messageType": "text | image | audio",
  "imageUrl": "https://...",
  "audioUrl": "https://...",
  "note": "...",
  "location": {
    "latitude": 25.123,
    "longitude": 68.456,
    "address": "..."
  },
  "sources": [],
  "aiConfidence": 0.86,
  "createdAt": "<timestamp>"
}
```

## `notifications/{notificationId}`

Only real backend events create notifications.

```json
{
  "ownerId": "<uid>",
  "scanId": "<scan id>",
  "title": "Important disease warning",
  "body": "...",
  "read": false,
  "type": "high_risk_diagnosis",
  "createdAt": "<timestamp>"
}
```

## Firebase Storage

All farmer media is scoped under the authenticated UID:

```text
users/{uid}/profile/
users/{uid}/scans/
users/{uid}/chat/images/
users/{uid}/chat/audio/
```

See `firebase/firestore.rules` and `firebase/storage.rules`.
