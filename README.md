# Banana Lifeline — Flutter + Firebase + AI Integration

Banana Lifeline is a farmer-facing mobile application for banana disease early warning and grounded agricultural guidance.

This package was built after reviewing the supplied:
- friend AI ZIP
- Banana Lifeline HTML prototype
- detailed Flutter/Firebase/AI requirements

## Final architecture

```text
Flutter Mobile App
    |
    +--> Firebase Authentication
    |
    +--> Cloud Firestore
    |      users / farms / plant_scans / chat_sessions / notifications
    |
    +--> Firebase Storage
    |      scan images / chat images / voice notes / profile photos
    |
    +--> Firebase Cloud Messaging
    |
    +--> FastAPI AI Bridge  -- Firebase ID token -->
             |
             +--> Friend CNN checkpoint (healthy / panama / sigatoka)
             |
             +--> Qdrant + BGE-M3 RAG
             |
             +--> DeepSeek grounded answer generation
             |
             +--> Google Cloud Speech-to-Text
```

## UI direction

- **Brand:** Banana Lifeline
- **Theme:** clean green/cream agriculture UI with banana-yellow accents and red only for warnings
- **Screen/functionality direction:** the fuller HTML prototype flow
- English + Urdu with proper Flutter ARB localization and RTL

## Main mobile features

- onboarding
- Firebase register / login / logout / password reset
- farmer profile + profile photo
- saved farm records
- dashboard / farm risk summary
- real camera + gallery
- real GPS + reverse geocoded address
- manual location fallback
- exact place in farm: farm, plot/sector, row, plant number
- farmer note + automatic date/time
- preview before submit
- real Firebase Storage upload
- authenticated real AI API call
- diagnosis result / severity / confidence / warning
- history and detailed reports
- retry failed diagnosis using stored Firebase scan image
- Banana Expert contextual RAG chat
- real chat history stored in Firestore
- image + question + note + exact farm place + GPS in chat
- live English/Urdu speech-to-text
- actual WAV voice-note recording + preview + Storage upload
- backend voice transcription
- AI answer text-to-speech play / pause / stop
- knowledge-source display
- FCM token registration + backend-generated high-risk notifications
- connectivity banner, Firestore cache support, and a real local pending-upload queue that preserves scan photos/notes/farm place when upload fails
- settings / language / permissions / API health / privacy / about

## No fake runtime data

There are no static diagnosis, chat, notification, or history records used as live app data.

If a required service is not available:
- no trained checkpoint → diagnosis returns service-not-ready
- no RAG index → chat returns service-not-ready
- no generation API key → chat returns service-not-ready
- no speech backend → voice transcription returns service-not-ready

That behavior is intentional.

## Important finding from the friend AI ZIP

The friend repository is not yet a finished deployment AI service. Its own project status marks:
- foundation: done
- data audit / clean split: done
- CNN classifier: next
- OOD: planned
- RAG: planned
- answer generation: planned

The integration therefore **reuses** the friend's model loading/inference code once a real checkpoint exists, and adds the missing FastAPI/Firebase/RAG integration layer.

The friend dataset is leaf-only. The API rejects non-leaf classification. Panama/Fusarium output remains a **suspected screening result**, not laboratory confirmation.

## Folder layout

```text
backend/    FastAPI + Firebase Admin + real AI adapters
mobile/     Flutter application source
firebase/   security rules + indexes
docs/       analysis, schema, setup, testing
scripts/    Windows helper scripts
```

## Start here

Read in this order:

1. `docs/EXISTING_PROJECT_ANALYSIS.md`
2. `docs/INTEGRATE_WITH_FRIEND_REPO.md`
3. `docs/FIREBASE_SETUP.md`
4. `docs/AI_BACKEND_SETUP.md`
5. `docs/MOBILE_SETUP.md`
6. `docs/REQUIREMENTS_IMPLEMENTATION_MATRIX.md`
7. `docs/TEST_FLOW.md`

For the fastest Windows path, use:

`docs/SETUP_WINDOWS.md`

## Validation already performed in this generated package

- Python FastAPI source passes `python -m py_compile app/*.py`.
- ARB files are valid JSON and contain matching English/Urdu keys.
- Local Dart imports were checked for missing source files.
- The Flutter SDK is not available in the generation environment, so you must run `flutter gen-l10n` and `flutter analyze` on your machine after platform wrappers are generated.
