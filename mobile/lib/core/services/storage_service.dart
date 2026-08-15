/// Firebase Storage is intentionally not used in the no-billing Banana Lifeline
/// build. Real image/audio files are uploaded to the authenticated FastAPI
/// service instead.
///
/// This file remains only so applying the patch over an older checkout does not
/// leave an import of `firebase_storage` behind.
class StorageServiceDisabled {
  const StorageServiceDisabled._();
}
