# AI backend setup — Windows

The friend ZIP contains an AI **package in progress**, not a deployed API. This integration adds a FastAPI bridge while reusing the friend's vision package.

## What the supplied AI ZIP actually has

- Phase 0 foundation: done
- Phase 1 dataset audit / clean split / cache: done
- Phase 2 CNN: next
- OOD, RAG, generation: planned
- Dataset/model scope: banana **leaf** photos
- Vision classes: `healthy`, `panama`, `sigatoka`
- No deployable trained checkpoint is included in the uploaded ZIP

Therefore `/diagnose` deliberately returns HTTP 503 until a real checkpoint exists. Nothing in this package invents a diagnosis.

## 1. Keep the friend's AI folder

Example repo:

```text
C:\Banana-Lifeline\
  ai\
    src\
    configs\
    ...
  backend\
  mobile\
```

The backend expects `BANANA_AI_ROOT` to point to `C:\Banana-Lifeline\ai`.

## 2. Python environment

Use Python 3.11 because the friend's package declares Python `>=3.11,<3.13`.

```powershell
cd C:\Banana-Lifeline\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

# Reuse the friend's vision package itself:
pip install -e "C:\Banana-Lifeline\ai[vision]"
```

## 3. Firebase Admin

Firebase Console → Project Settings → Service accounts → create/download a service-account JSON.

Keep it outside Git, for example:

```text
C:\secure\banana-lifeline-service-account.json
```

Set `GOOGLE_APPLICATION_CREDENTIALS` to that file in `backend\.env`.

## 4. Configure backend

```powershell
Copy-Item .env.example .env
notepad .env
```

Set real values:

```dotenv
BANANA_AI_ROOT=C:/Banana-Lifeline/ai
BANANA_MODEL_CHECKPOINT=C:/Banana-Lifeline/ai/runs/<real-run>/best.pt
GOOGLE_APPLICATION_CREDENTIALS=C:/secure/banana-lifeline-service-account.json
FIREBASE_PROJECT_ID=<your Firebase project id>

DEEPSEEK_API_KEY=<real key>
DEEPSEEK_MODEL=deepseek-v4-flash

KNOWLEDGE_DIR=./knowledge
QDRANT_LOCAL_PATH=./.qdrant
```

## 5. RAG corpus

The package includes the uploaded Fusarium/Panama manual in `backend/knowledge/`.

Do **not** make the chatbot claim knowledge that is not in the corpus. If you want robust answers for Sigatoka, fertilizer, irrigation, pest management, etc., add real authoritative PDF/MD/TXT documents to `backend/knowledge/` first.

Build the index:

```powershell
cd C:\Banana-Lifeline\backend
.\.venv\Scripts\Activate.ps1
python -m app.index_knowledge
```

The implementation uses BGE-M3 embeddings with Qdrant. If you set `QDRANT_URL`, it uses a remote Qdrant service; otherwise it uses the local path.

## 6. Google Cloud speech transcription

Recorded voice notes use the backend transcription endpoint. Enable Google Cloud Speech-to-Text for the same/appropriate Google Cloud project and ensure the service account has permission.

`SPEECH_ENABLED=true`

## 7. Run backend

```powershell
cd C:\Banana-Lifeline\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Check:

```powershell
curl http://127.0.0.1:8000/api/v1/health
```

Expected readiness fields:

- `vision_ready`
- `rag_ready`
- `generation_ready`
- `speech_enabled`

A `false` field is an honest configuration/readiness state, not fake fallback data.

## 8. Android phone connection

A physical phone cannot call your PC with `127.0.0.1`.

Run:

```powershell
ipconfig
```

Find the PC IPv4 on the same Wi-Fi, for example `192.168.1.25`, then use:

```json
"AI_BASE_URL": "http://192.168.1.25:8000"
```

in the Flutter `config/dev.json`.

Allow Python/port 8000 through Windows Firewall for the private network.

## API contract

### `GET /api/v1/health`

No farmer data. Shows server component readiness.

### `POST /api/v1/diagnose`

Multipart:
- `scan_id`
- `image`
- `language`
- `scan_target=leaf`
- `note`
- `latitude`
- `longitude`
- `address`

Requires `Authorization: Bearer <Firebase ID token>`.

### `POST /api/v1/diagnose/retry/{scan_id}`

Retries a failed scan using the existing image URL in the authenticated user's Firestore scan.

### `POST /api/v1/chat`

JSON:
- `session_id`
- `message`
- `language`
- `related_scan_id`
- `image_url`
- `audio_url`
- `latitude`
- `longitude`
- `address`
- `note`

The backend maintains the Firestore session context, retrieves RAG sources, and then calls the generation provider.

### `POST /api/v1/transcribe`

Multipart:
- WAV `audio`
- `language=en|ur`

Requires Firebase bearer token.

## Scientific safety preserved from the friend's AI design

- The current classifier is leaf-only.
- Panama output is presented as *suspected screening*, not lab-confirmed TR4.
- The system abstains below the configured confidence threshold.
- No chemical cure is invented for Panama.
- RAG answers are generated only when actual indexed source chunks exist.
