# Existing project analysis

## AI ZIP

The supplied AI repository is an AI-layer work-in-progress, not a running backend. Its own README marks data cleaning/audit as complete, the CNN as the next phase, and OOD, RAG, and answer generation as planned. The current Python source contains the data pipeline and vision training/evaluation modules, but no FastAPI service, no RAG package, no generation package, and no trained deployment checkpoint in the ZIP.

Important constraints from the AI project that this integration preserves:

- Canonical vision classes: `healthy`, `panama`, `sigatoka`.
- Model architecture is configured through the friend package and checkpoints are self-describing.
- Evaluation preprocessing is deterministic and uses the same configured image size.
- The current dataset contains banana **leaf** photos. The backend therefore rejects non-leaf diagnosis requests rather than pretending the classifier supports fruit/stem/corm images.
- Panama predictions are treated as **suspected / screening results**, never a laboratory-confirmed diagnosis.
- No chemical cure is invented for Panama/Fusarium wilt.
- A real model checkpoint is required through `BANANA_MODEL_CHECKPOINT`. If it is missing, `/diagnose` returns an explicit service-not-ready error; it never fabricates a diagnosis.

## HTML prototype

The supplied HTML prototype contains eight main states/screens:

1. Splash
2. Home
3. Camera / image capture
4. Banana Expert chat
5. Full diagnosis result
6. Settings / English-Urdu switch
7. History
8. Offline / queued state

Useful UX concepts retained in Flutter:

- Banana Lifeline brand and Banana Expert assistant.
- Start a new check with photo or voice.
- Recent checks and history.
- Camera framing guidance, gallery selection, clear-photo hint.
- Image + farmer question in chat.
- Thinking/loading state.
- Confidence/severity/result card.
- Full diagnosis, listen-to-answer button, source display.
- English/Urdu support and RTL.
- Offline-safe UX: entered data is not silently discarded.

The HTML content itself uses static sample diagnosis/history data. The Flutter rebuild does **not** copy those values as runtime data; Firebase and the AI API are the dynamic sources.

## Added requested functionality

- Firebase email/password authentication and persisted farmer profile.
- Farm records in Firestore.
- Exact place within the farm: farm, plot/sector, row, plant number, GPS coordinates, reverse-geocoded address, manual fallback address, and note.
- Original image upload to Firebase Storage.
- Real AI REST call authenticated with the Firebase ID token.
- Firestore scan history and detailed reports.
- RAG-backed contextual chat with persisted sessions/messages.
- Text chat, image chat, live speech-to-text, recorded voice notes, backend transcription hook, and text-to-speech answers.
- Firestore-backed notifications and FCM device token registration.
- Real local pending-upload queue for weak/no internet: the selected image is copied into app documents, metadata is persisted locally, and the farmer can retry from History.
- No hard-coded fake diagnosis/chat/history data.
