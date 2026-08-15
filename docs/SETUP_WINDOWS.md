# Banana Lifeline — Windows setup order

1. Put the supplied `backend/`, `mobile/`, `firebase/`, `docs/`, `scripts/` folders into the same repository that already contains your friend's `ai/` folder.
2. Finish/train the friend's CNN and obtain a real checkpoint (`best.pt`). Until then the app correctly shows "model service not ready".
3. Create/configure Firebase and deploy `firebase/` rules/indexes.
4. Configure `backend/.env`.
5. Install Python 3.11 backend + friend AI `[vision]`.
6. Add authoritative RAG documents and run `python -m app.index_knowledge`.
7. Start FastAPI on `0.0.0.0:8000`.
8. Generate Flutter platform wrappers with `scripts/bootstrap_mobile.ps1`.
9. Configure `mobile/config/dev.json`.
10. Run `flutter gen-l10n`, `flutter analyze`, then `flutter run --dart-define-from-file=config/dev.json`.
11. Test using `docs/TEST_FLOW.md`.
12. Build release APK.

Read:
- `docs/EXISTING_PROJECT_ANALYSIS.md`
- `docs/AI_BACKEND_SETUP.md`
- `docs/FIREBASE_SETUP.md`
- `docs/MOBILE_SETUP.md`
