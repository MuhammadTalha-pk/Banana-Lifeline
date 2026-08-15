# Requirements implementation matrix

This matrix distinguishes app/backend implementation from external artifacts that are not present in the supplied friend AI ZIP.

| Area | Status | Implementation |
|---|---|---|
| Modern farmer UI | Implemented | Green/cream agriculture theme, banana-yellow accents, reusable widgets |
| English + Urdu | Implemented | `app_en.arb` / `app_ur.arb`, runtime locale switch, automatic RTL |
| Firebase Auth | Implemented | register, login, reset password, persistent session, logout |
| Farmer profile | Implemented | Firestore profile, photo upload, district/province/farm size/crop info |
| Farms | Implemented | create/edit/delete saved farms with GPS/address |
| Dashboard | Implemented | real recent scans, farm-risk summary, scan/chat/history/notifications shortcuts |
| Camera/gallery | Implemented | `image_picker`, real selected image preview |
| Exact place in farm | Implemented | farm, plot/sector, row, plant number, GPS, reverse-geocoded/manual address |
| Scan note + timestamp | Implemented | stored with real scan metadata |
| Firebase Storage scan image | Implemented | owner-scoped Storage path |
| Plant diagnosis API | Integrated, needs teammate checkpoint | FastAPI imports friend `load_checkpoint` + evaluation transform; no fake fallback |
| Model scope safety | Implemented | leaf-only requests; Panama remains suspected screening |
| Diagnosis Firestore result | Implemented | trusted backend/Admin writes diagnosis fields |
| Diagnosis retry | Implemented | retries the same stored Firebase scan image |
| Scan history/report | Implemented | real Firestore stream + filters + detail screen |
| Weak/no internet | Implemented | Firestore cache + connectivity banner + local pending scan upload queue |
| Contextual chatbot | Implemented | session/message context persisted in Firestore |
| RAG | Implemented bridge | BGE-M3 + Qdrant index over real local documents; current included corpus is Fusarium manual only |
| Friend native RAG module | Not present in ZIP | Friend README marks it planned; backend bridge can be replaced when teammate ships it |
| LLM generation | Implemented bridge | grounded generation via configurable DeepSeek OpenAI-compatible endpoint |
| Chat image | Implemented | real Firebase Storage upload + note + exact farm place + GPS + backend vision context |
| Live speech-to-text | Implemented | device speech recognition, English/Urdu |
| Voice note | Implemented | real WAV recording, preview, Firebase Storage upload, backend transcription |
| Backend speech transcription | Implemented bridge | Google Cloud Speech-to-Text with service-account credentials |
| AI answer speech | Implemented | device TTS play/pause/stop, English/Urdu |
| RAG source display | Implemented | assistant messages and diagnosis guidance carry source metadata |
| FCM | Implemented | device token registration; high-risk backend notification + Firestore notification |
| Firestore rules | Implemented | owner-scoped client access; trusted AI/chat writes reserved for Admin backend |
| Storage rules | Implemented | owner-only paths, image/audio types, size limit |
| Environment/secrets | Implemented | `dev.json` and backend `.env`; AI/private credentials stay out of Flutter source |
| Android/iOS wrappers | Bootstrap required | Generated with the user's installed Flutter SDK using `scripts/bootstrap_mobile.ps1` |
| Real trained CNN checkpoint | Missing external artifact | Not contained in supplied ZIP; teammate must train/export/provide `best.pt` |
| OOD policy/calibration | Missing external artifact | Friend plan marks OOD as planned; backend currently uses confidence abstention only |
| Full multi-topic knowledge corpus | Needs authoritative docs | Only the supplied Fusarium manual is bundled; add approved Sigatoka/fertilizer/irrigation/pest documents before claiming those topics |
