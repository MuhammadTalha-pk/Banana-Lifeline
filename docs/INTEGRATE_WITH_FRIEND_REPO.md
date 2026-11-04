# Merge this work into the friend's Banana-Lifeline repository

The friend repository already owns the `ai/` directory. Keep it intact.

Recommended final repository:

```text
Banana-Lifeline/
  ai/                 # friend's original AI package + trained checkpoint
  backend/            # FastAPI/Firebase/RAG bridge from this package
  mobile/             # Flutter application from this package
  firebase/           # Firestore/Storage rules and indexes
  docs/
  scripts/
  README.md
```

## Safe merge

From the cloned friend repository:

```powershell
git switch -c talha-mobile-firebase-integration
```

Copy the supplied folders into the repo, but **do not overwrite `ai/`**.

Then:

```powershell
git status
git add backend mobile firebase docs scripts README.md .gitignore
git commit -m "Integrate Flutter Firebase app with Banana Lifeline AI layer"
git push -u origin talha-mobile-firebase-integration
```

After testing, create a pull request into the team's main branch.

## Backend link to friend AI

In `backend/.env`:

```dotenv
BANANA_AI_ROOT=C:/path/to/Banana-Lifeline/ai
BANANA_MODEL_CHECKPOINT=C:/path/to/Banana-Lifeline/ai/runs/<real-run>/best.pt
```

The backend imports the friend's real:

```python
banana_lifeline.vision.model.load_checkpoint
banana_lifeline.vision.transforms.build_eval_transform
```

It does not replace the friend's classifier architecture.

## What still belongs to the AI teammate

The uploaded AI ZIP explicitly marks CNN training as the next phase and RAG/generation as planned. The integration is ready for those real artifacts, but the teammate still needs to provide:

- trained and evaluated deployable checkpoint
- final model calibration/OOD policy if completed
- any additional approved knowledge documents
- optional future native RAG/generation package code

Until then, the application shows honest service-readiness errors rather than fake predictions.
