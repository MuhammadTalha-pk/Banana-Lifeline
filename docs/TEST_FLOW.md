# End-to-end test checklist

Test with **synthetic/demo farmer account data** and non-sensitive farm media until production privacy/legal review is complete.

## Authentication
- [ ] Register a farmer
- [ ] Confirm `users/{uid}` is created
- [ ] Logout / login
- [ ] Forgot-password email works
- [ ] Edit profile
- [ ] Switch English ↔ Urdu and verify RTL

## Farm
- [ ] Add a farm
- [ ] Capture farm GPS
- [ ] Edit farm
- [ ] Scan screen can select saved farm

## Scan
- [ ] Take real leaf photo from camera
- [ ] Pick real leaf photo from gallery
- [ ] Capture GPS and reverse-geocoded address
- [ ] Enter manual address if GPS denied
- [ ] Enter plot/sector, row, plant number, note
- [ ] Preview shows actual image + metadata + date/time
- [ ] Storage receives the image under `users/{uid}/scans/`
- [ ] Firestore `plant_scans` document is created
- [ ] Backend receives valid Firebase bearer token
- [ ] With checkpoint missing: visible service-not-ready state, no fabricated diagnosis
- [ ] With checkpoint configured: diagnosis writes from backend Admin
- [ ] Failed stored scan can be retried without creating a fake/new diagnosis
- [ ] High-risk real result creates Firestore notification / FCM attempt

## Chat / RAG
- [ ] Build Qdrant index from actual knowledge files
- [ ] Configure generation API key
- [ ] Create a chat session
- [ ] Send English multi-turn question
- [ ] Send Urdu multi-turn question
- [ ] Messages persist in Firestore
- [ ] Sources shown under assistant answer
- [ ] Unsupported question receives honest no-reliable-source behavior

## Image chat
- [ ] Attach real banana leaf image
- [ ] Add note
- [ ] Add GPS/manual address
- [ ] Backend applies the real vision model before adding image context
- [ ] If model is unavailable, request fails visibly instead of ignoring the image

## Voice
- [ ] Live speech-to-text works in English
- [ ] Live speech-to-text works in Urdu if device speech service supports Urdu
- [ ] Record WAV voice note
- [ ] Preview local recording
- [ ] Backend transcribes real audio
- [ ] Audio uploaded to Firebase Storage
- [ ] Transcription sent into contextual chat
- [ ] Assistant answer can play/pause/stop via device TTS

## Security
- [ ] User A cannot query User B farms/scans/chats/notifications
- [ ] Mobile client cannot write `diagnosis`
- [ ] Mobile client cannot create assistant chat messages
- [ ] Storage rejects files under another user's UID
- [ ] DeepSeek/Qdrant/Firebase Admin secrets are absent from Flutter


## Weak/no internet pending upload

- [ ] Disable internet before submitting a real scan
- [ ] Scan draft is saved locally with the real image, note, farm/plot/row/plant and GPS/address
- [ ] History shows Pending uploads
- [ ] Restore internet and tap Retry upload
- [ ] The real image uploads to Firebase Storage and the scan appears in Firestore
- [ ] The local pending item is removed only after upload succeeds
