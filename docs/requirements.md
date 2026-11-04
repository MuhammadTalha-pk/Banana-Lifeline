I have two existing project files:

1. `banana-lifeline.zip` — contains the existing AI/backend-related work.
2. `Banana Lifeline.html` / `bananalifeline.html` — contains the existing frontend prototype and required application functionality.

I want you to build a **complete, production-ready Flutter mobile application** for this project.

## Main Objective

First, carefully review both files and understand:

- Existing features
- Existing workflows
- Existing AI functionality
- User roles
- Screens
- Forms
- Disease detection flow
- Chatbot flow
- Location-related functionality
- Farmer-related features
- Data structure
- Any API/backend logic already available

Do not remove useful functionality from the existing project.

The new Flutter application should provide the **same functionality as the existing system**, but with a much better, modern, professional, farmer-friendly UI/UX.

---

# 1. Technology Stack

Use:

- Flutter
- Dart
- Firebase Authentication
- Cloud Firestore
- Firebase Storage
- Firebase Cloud Messaging where required
- Firebase Crashlytics if useful
- Firebase Analytics if useful
- REST APIs or WebSocket APIs for communication with the AI layer
- Riverpod, Bloc, or another clean state-management solution
- Clean Architecture
- Repository pattern
- Proper service layer
- Proper error handling
- Environment variables for API URLs and secrets

The app should work properly on Android and should be structured so iOS support can also be added easily.

---

# 2. Do Not Use Fake Data

This is extremely important.

Do not build the application using hard-coded dummy information.

All dynamic information should come from:

- Firebase
- Real device location
- Real uploaded images
- Real AI APIs
- Real chatbot responses
- Real user accounts
- Real Firestore collections
- Real backend services

If an AI API is not yet available, create a proper service interface and clearly mark the endpoint that needs to be connected.

Do not silently replace missing APIs with fake results.

---

# 3. UI/UX Design

Keep the concept of the existing HTML project but completely improve its UI.

The application should feel:

- Modern
- Clean
- Agricultural
- Professional
- Simple for farmers
- Easy to understand
- Easy for low-technical users
- Responsive
- Accessible

Use a beautiful agriculture-inspired design system.

Suggested colors:

- Deep green
- Leaf green
- Light cream/off-white
- Soft yellow accents
- Neutral grey
- Red only for warnings/disease alerts

Do not make the UI overly colorful.

Create reusable widgets for:

- Buttons
- Cards
- Inputs
- App bars
- Alerts
- Loading indicators
- Empty states
- Error states
- Image upload cards
- Disease result cards
- Weather/location cards
- Chat messages

---

# 4. English and Urdu Language Support

The complete application must support:

- English
- Urdu

Add a language selector.

The user should be able to switch language from the settings/profile screen.

Implement proper Flutter localization.

Do not hard-code translated strings directly inside widgets.

Use proper localization files such as:

- `app_en.arb`
- `app_ur.arb`

Urdu should support proper RTL layout.

When Urdu is selected:

- Text direction should change correctly
- Buttons should remain readable
- Navigation should remain intuitive
- Chat should support Urdu
- AI requests should support Urdu questions
- AI answers may also be returned in Urdu

---

# 5. Firebase Authentication

Create a complete authentication system.

Support at minimum:

- User registration
- Login
- Logout
- Forgot password
- Password reset
- Persistent login/session
- Profile update

Save the farmer profile in Firestore.

Farmer profile fields may include:

- User ID
- Full name
- Phone number
- Email
- Preferred language
- District
- Province
- Farm location
- Farm size
- Crop information
- Registration date
- Profile photo

Use Firebase Auth UID as the primary user identifier.

---

# 6. Farmer Dashboard

Create a professional farmer dashboard.

It should provide quick access to:

- Scan banana plant
- AI chatbot
- Scan history
- Disease reports
- Farm information
- Current location
- Recent diagnoses
- Notifications
- Profile
- Settings

Do not overcrowd the dashboard.

Make the most important actions clearly visible.

---

# 7. Banana Plant Image Diagnosis

The farmer must be able to:

- Take a photo using camera
- Select image from gallery
- Preview image
- Add notes
- Automatically capture current GPS location
- Add location manually if GPS is unavailable
- Add date/time automatically
- Submit image to AI model

Before submitting, show:

- Plant image
- Farmer note
- Latitude
- Longitude
- Location/address if available
- Date/time

When the image is sent, call the real AI module.

The AI diagnosis result should support information such as:

- Disease detected
- Confidence score
- Disease description
- Severity level
- Recommended treatment
- Prevention steps
- Additional advice
- Whether expert assistance is recommended

Save the complete result in Firestore.

Save the original image in Firebase Storage.

Store the Firebase Storage URL in Firestore.

---

# 8. Image Metadata

Every submitted plant image should be connected with:

- User ID
- Image URL
- Timestamp
- Latitude
- Longitude
- Address/location name
- Farmer note
- Diagnosis
- Confidence
- AI response
- Severity
- Status

The farmer should later be able to open a diagnosis and see where that image was taken.

---

# 9. Location

Use real device GPS.

Request proper Android/iOS permissions.

Use packages such as:

- `geolocator`
- `geocoding`

Handle cases such as:

- Permission denied
- Permission permanently denied
- GPS disabled
- No location available
- Poor connection

Do not crash if location is unavailable.

---

# 10. Diagnosis History

Create a history screen showing all previous scans.

Each history item should display:

- Thumbnail
- Disease name
- Date
- Severity
- Location
- Diagnosis status

Add filters such as:

- All
- Healthy
- Disease detected
- Severe
- Latest

Allow opening a detailed report.

---

# 11. AI Farmer Chatbot

Create a complete AI chatbot for farmers.

The chatbot should be able to answer questions about:

- Banana diseases
- Plant symptoms
- Fertilizer
- Irrigation
- Pest management
- Crop health
- Weather-related crop questions if weather data is available
- Treatment recommendations
- Prevention
- Banana farming best practices

The chatbot must connect with the AI module contained in the existing AI project.

---

# 12. RAG Chatbot

Implement Retrieval-Augmented Generation.

The chatbot should not rely only on a general language model.

It should retrieve relevant information from the banana agriculture knowledge base.

Suggested architecture:

Farmer Question
→ Generate embedding
→ Search vector database
→ Retrieve relevant banana disease/farming documents
→ Send retrieved context + farmer question to LLM
→ Generate final answer
→ Return answer to Flutter app

Use the RAG implementation available in the AI module if already implemented.

If RAG is not complete, prepare proper API integration hooks.

Possible vector databases may include:

- FAISS
- Pinecone
- Chroma
- Firestore vector search
- Another vector solution already used by the AI module

Do not invent a second architecture if the existing AI project already contains one.

Inspect the AI project first.

---

# 13. Context-Aware Chat

The chatbot should maintain conversation context.

The farmer should be able to say something like:

"My banana leaves are turning yellow."

Then:

"There are also black spots."

Then:

"What treatment should I use?"

The AI should understand that all three messages belong to the same problem.

Save chat sessions in Firestore.

Suggested collections:

`chat_sessions`

`chat_messages`

Each chat session should include:

- Session ID
- User ID
- Created date
- Updated date
- Title
- Language
- Related diagnosis ID if applicable

Each message should include:

- Sender
- Message
- Message type
- Timestamp
- Audio URL if applicable
- Image URL if applicable
- AI metadata if applicable

---

# 14. Voice Chat

The farmer should be able to communicate using voice.

Support:

### Speech to Text

Farmer records a voice message.

The application converts speech to text.

Support:

- English
- Urdu

Then send the transcription to the AI chatbot.

Possible implementation:

- Device speech recognition
- Whisper API
- Backend speech recognition

Use whichever solution is most suitable with the existing AI architecture.

---

# 15. Voice Message

Also allow the farmer to send an actual voice note.

Flow:

Record
→ Preview
→ Send
→ Upload audio to Firebase Storage
→ Save audio URL in Firestore
→ Transcribe audio
→ Send transcription to AI
→ Receive response

Show the voice message inside the chat UI.

---

# 16. AI Voice Response

The farmer should also be able to listen to the chatbot answer.

Add a speaker/play button with every AI response.

Implement Text-to-Speech.

Support:

- English speech
- Urdu speech

The user should be able to:

- Play answer
- Pause answer
- Stop answer

---

# 17. Image in Chat

Allow the farmer to send an image directly inside the chatbot.

For example:

"My plant has this problem."

Then attach an image.

The backend should receive:

- Image
- User question
- Chat history
- Current language
- GPS location if permitted
- Farmer note if provided

The AI should use both image analysis and chatbot/RAG context when possible.

---

# 18. Firebase Database Design

Create a proper Firestore structure.

Suggested collections:

```
users
farms
plant_scans
diagnoses
chat_sessions
chat_messages
notifications
knowledge_documents
user_settings

```

You may modify this structure if the current backend requires something better.

Define proper Firestore models in Flutter.

---

# 19. Firebase Storage

Use Firebase Storage for:

- Profile images
- Banana plant images
- Chat images
- Voice notes
- Generated documents if required

Use organized paths.

Example:

```
users/{uid}/profile/
users/{uid}/scans/
users/{uid}/chat/images/
users/{uid}/chat/audio/

```

---

# 20. Firebase Security

Create proper Firebase Security Rules.

Farmers should only access their own:

- Profile
- Chats
- Scan history
- Uploaded images
- Diagnosis results

Do not leave Firestore or Storage publicly accessible.

Provide:

- `firestore.rules`
- `storage.rules`

---

# 21. AI Module Integration

Carefully inspect `banana-lifeline.zip`.

Find all available:

- Models
- APIs
- Python services
- Disease detection logic
- RAG logic
- Chatbot logic
- Embedding logic
- Image analysis logic
- Existing endpoints
- Authentication requirements
- Expected request/response JSON

Do not rewrite the AI model unnecessarily.

Build the Flutter integration around the existing AI module.

If the AI module does not currently expose APIs, create or recommend a proper API layer using something like FastAPI.

Example endpoints may include:

```
POST /api/v1/diagnose
POST /api/v1/chat
POST /api/v1/chat/image
POST /api/v1/transcribe
POST /api/v1/rag/query
GET  /api/v1/health

```

But first inspect the existing backend and reuse existing endpoints where possible.

---

# 22. Secure Firebase-to-AI Communication

The Flutter application should not expose sensitive API keys.

Use:

Flutter
→ Firebase authenticated user
→ AI backend API

Send Firebase ID token with requests.

The backend should verify the Firebase token if possible.

Never put private AI credentials directly inside Flutter source code.

---

# 23. Networking Layer

Create a reusable API client.

Implement:

- Base URL
- Authorization headers
- Firebase token
- Timeouts
- Multipart image upload
- Audio upload
- JSON parsing
- Retry logic where appropriate
- API exceptions
- Offline errors
- Server errors

Use packages such as:

- Dio
  or
- http

Dio is preferred if suitable.

---

# 24. Loading and Error Handling

Every real API operation must have proper states:

- Initial
- Loading
- Success
- Error

Examples:

When diagnosing an image:

Show:

"Analyzing your banana plant..."

Do not freeze the UI.

If API fails, show:

"Unable to analyze the image. Please check your internet connection and try again."

Do not show raw technical exceptions to farmers.

---

# 25. Offline/Weak Internet Behaviour

Many farmers may have weak internet.

Design the application accordingly.

Where possible:

- Cache farmer profile
- Cache scan history
- Cache previous chat messages
- Queue uploads when appropriate
- Show network status
- Avoid losing entered notes if upload fails

Use Firestore offline persistence where suitable.

---

# 26. Notifications

Prepare notification functionality.

Possible notifications:

- Diagnosis completed
- Important disease warning
- New treatment recommendation
- Follow-up reminder
- Backend alert

Use Firebase Cloud Messaging.

Do not generate fake notifications.

---

# 27. Settings Screen

Include:

- Language
- Notifications
- Profile
- Location permission
- App information
- Privacy policy
- Logout

---

# 28. Project Architecture

Use a scalable project structure similar to:

```
lib/
  app/
  core/
    constants/
    errors/
    network/
    services/
    theme/
    utils/

  features/
    auth/
      data/
      domain/
      presentation/

    dashboard/
    diagnosis/
    chatbot/
    history/
    profile/
    settings/
    notifications/

  firebase/
  localization/
  shared/
  main.dart

```

Keep UI, business logic, Firebase logic, and AI API logic separated.

---

# 29. Dart Models

Create strongly typed Dart models for:

- Farmer
- Farm
- Diagnosis
- PlantScan
- ChatSession
- ChatMessage
- LocationData
- AIResponse
- DiseaseResult
- Notification

Provide:

- `fromJson`
- `toJson`
- Firestore converters where useful

---

# 30. Required Flutter Screens

At minimum create:

1. Splash Screen
2. Onboarding
3. Login
4. Register
5. Forgot Password
6. Main Dashboard
7. Banana Scan Screen
8. Image Preview Screen
9. Diagnosis Loading Screen
10. Diagnosis Result Screen
11. Scan History
12. Scan Detail
13. AI Chatbot
14. Voice Chat
15. Farmer Profile
16. Edit Profile
17. Settings
18. Language Settings
19. Notifications
20. About/Help

---

# 31. Navigation

Use a clean navigation solution such as:

- GoRouter

Suggested bottom navigation:

- Home
- Scan
- AI Chat
- History
- Profile

---

# 32. Flutter Packages

Use stable current versions compatible with the Flutter SDK used by the project.

Potential packages:

```
firebase_core
firebase_auth
cloud_firestore
firebase_storage
firebase_messaging
firebase_crashlytics
firebase_analytics
flutter_riverpod
go_router
dio
image_picker
camera
geolocator
geocoding
permission_handler
record
just_audio
flutter_tts
speech_to_text
cached_network_image
intl
flutter_localizations
shared_preferences
connectivity_plus
uuid

```

Do not add unnecessary packages.

---

# 33. Environment Configuration

Create environment configuration for:

```
AI_BASE_URL
API_VERSION
FIREBASE values if required

```

Do not hard-code production URLs throughout the code.

Example:

```
class ApiConfig {
  static const String baseUrl =
      String.fromEnvironment('AI_BASE_URL');
}

```

---

# 34. Backend Request Example

For plant diagnosis, the Flutter application may send:

```
{
  "user_id": "firebase_uid",
  "latitude": 33.0000,
  "longitude": 73.0000,
  "note": "Yellow leaves with black spots",
  "language": "en"
}

```

plus the actual image using multipart upload.

The backend response should be converted into proper Dart models.

---

# 35. Chat Request Example

The chatbot API may receive:

```
{
  "user_id": "firebase_uid",
  "session_id": "session_id",
  "message": "My banana leaves have black spots. What should I do?",
  "language": "en",
  "latitude": 33.0000,
  "longitude": 73.0000
}

```

Response example:

```
{
  "answer": "...",
  "sources": [],
  "confidence": 0.91,
  "session_id": "session_id"
}

```

Adapt this structure based on the existing AI project.

---

# 36. RAG Sources

Where appropriate, allow the chatbot response to include information about its retrieved sources.

For example:

- Banana farming guide
- Disease management document
- Agriculture research document

Do not expose raw internal vector database implementation details to the farmer.

---

# 37. Privacy

Because the application stores:

- User details
- Location
- Images
- Voice
- Agricultural information

Add privacy-aware design.

Ask permission before:

- Camera access
- Microphone access
- GPS access

Explain why each permission is required.

---

# 38. Code Quality

The code must:

- Compile
- Be organized
- Avoid duplicated logic
- Avoid giant widgets
- Use reusable components
- Use null safety
- Follow Dart conventions
- Include comments only where useful
- Handle errors properly
- Avoid deprecated APIs

Do not provide incomplete pseudo-code when complete Flutter code can be provided.

---

# 39. Work in Phases

Do not randomly generate files.

Follow this order.

### Phase 1 — Existing Project Analysis

Review:

- ZIP project
- HTML prototype

Give me:

- Existing features
- AI features
- APIs
- Missing features
- Recommended architecture
- Firebase mapping

### Phase 2 — Flutter Architecture

Create:

- `pubspec.yaml`
- Project folders
- Theme
- Localization
- Routing
- Firebase initialization

### Phase 3 — Authentication

Implement real Firebase authentication.

### Phase 4 — Farmer Dashboard

Implement real dashboard and Firestore integration.

### Phase 5 — Plant Diagnosis

Implement:

Camera/gallery
→ GPS
→ Note
→ Upload
→ AI API
→ Firestore result

### Phase 6 — AI RAG Chatbot

Implement:

- Text chat
- Chat history
- RAG API
- Firebase session storage

### Phase 7 — Voice

Implement:

- Voice recording
- Speech-to-text
- Voice note upload
- Text-to-speech

### Phase 8 — History and Reports

Implement real Firestore scan history.

### Phase 9 — Urdu

Translate and verify complete RTL layout.

### Phase 10 — Testing and Final Setup

Provide:

- Firebase configuration steps
- Backend integration instructions
- Android permissions
- Firestore indexes
- Security rules
- How to run
- How to build APK

---

# 40. Most Important Requirement

Before writing the Flutter implementation, **inspect the provided existing project files carefully**.

Do not guess their functionality.

Reuse the AI layer where possible.

The final architecture should be:

```
Flutter Mobile App
        |
        |
Firebase Authentication
        |
        +----------------------+
        |                      |
Cloud Firestore          Firebase Storage
        |                      |
        +----------+-----------+
                   |
             Flutter Services
                   |
                   |
              AI REST API
                   |
         +---------+---------+
         |                   |
Disease Detection          RAG
         |                   |
Image AI             Vector Database
                             |
                            LLM

```

The final application must feel like a real agricultural product, not a university demo with static screens.

Start by inspecting `banana-lifeline.zip` and `Banana Lifeline.html`, explain what already exists, and then begin implementing the Flutter application file by file.