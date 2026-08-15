// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appName => 'Banana Lifeline';

  @override
  String get tagline => 'Detect early. Act early. Protect the farm.';

  @override
  String get continueLabel => 'Continue';

  @override
  String get getStarted => 'Get started';

  @override
  String get english => 'English';

  @override
  String get urdu => 'Urdu';

  @override
  String get login => 'Login';

  @override
  String get register => 'Create account';

  @override
  String get logout => 'Logout';

  @override
  String get email => 'Email';

  @override
  String get password => 'Password';

  @override
  String get confirmPassword => 'Confirm password';

  @override
  String get fullName => 'Full name';

  @override
  String get phone => 'Phone number';

  @override
  String get forgotPassword => 'Forgot password?';

  @override
  String get resetPassword => 'Reset password';

  @override
  String get resetEmailSent => 'Password reset email sent.';

  @override
  String get noAccount => 'New to Banana Lifeline?';

  @override
  String get haveAccount => 'Already have an account?';

  @override
  String get welcomeBack => 'Welcome back';

  @override
  String get authSubtitle =>
      'Sign in to access your farm scans and Banana Expert.';

  @override
  String get createFarmerProfile => 'Create your farmer profile';

  @override
  String get province => 'Province';

  @override
  String get district => 'District';

  @override
  String get farmSize => 'Farm size';

  @override
  String get cropInfo => 'Crop information';

  @override
  String get save => 'Save';

  @override
  String get cancel => 'Cancel';

  @override
  String get home => 'Home';

  @override
  String get scan => 'Scan';

  @override
  String get aiChat => 'AI Chat';

  @override
  String get history => 'History';

  @override
  String get profile => 'Profile';

  @override
  String goodMorning(String name) {
    return 'Good morning, $name';
  }

  @override
  String get dashboardSubtitle =>
      'Check suspicious banana leaves early and keep a real plot-by-plot record.';

  @override
  String get farmRisk => 'Farm risk level';

  @override
  String get farmRiskEmpty =>
      'No severe diagnosis is currently recorded in your scan history.';

  @override
  String get scanNow => 'Scan now';

  @override
  String get scanNowSubtitle =>
      'Take a real leaf photo, add its farm place, and send it to the AI model.';

  @override
  String get askExpert => 'Ask Banana Expert';

  @override
  String get recentChecks => 'Recent checks';

  @override
  String get seeAll => 'See all';

  @override
  String get noScans => 'No scans yet';

  @override
  String get noScansSubtitle =>
      'Your real AI diagnosis history will appear here after your first scan.';

  @override
  String get currentLocation => 'Current location';

  @override
  String get notifications => 'Notifications';

  @override
  String get farmInformation => 'Farm information';

  @override
  String get newScan => 'New banana leaf scan';

  @override
  String get leafOnlyTitle => 'Current model scope: leaf images';

  @override
  String get leafOnlyBody =>
      'The supplied AI dataset is made of banana leaf photos. Stem, fruit, corm and whole-plant photos are not sent to this classifier.';

  @override
  String get takePhoto => 'Take photo';

  @override
  String get chooseGallery => 'Choose from gallery';

  @override
  String get imageRequired => 'Please take or select a banana leaf photo.';

  @override
  String get farmPlace => 'Place in farm';

  @override
  String get farmName => 'Farm name';

  @override
  String get plotSector => 'Plot / Sector';

  @override
  String get row => 'Row';

  @override
  String get plantNumber => 'Plant number';

  @override
  String get note => 'Farmer note';

  @override
  String get noteHint => 'What are you seeing on this plant?';

  @override
  String get gpsLocation => 'GPS location';

  @override
  String get captureGps => 'Capture GPS';

  @override
  String get manualAddress => 'Manual address / landmark';

  @override
  String get locationUnavailable => 'Location unavailable';

  @override
  String get locationPermissionDenied =>
      'Location permission was denied. You can enter the place manually.';

  @override
  String get locationServicesOff =>
      'GPS is disabled. Enable location services or enter the place manually.';

  @override
  String get preview => 'Review scan';

  @override
  String get photo => 'Plant image';

  @override
  String get dateTime => 'Date & time';

  @override
  String get latitude => 'Latitude';

  @override
  String get longitude => 'Longitude';

  @override
  String get address => 'Address';

  @override
  String get submitForDiagnosis => 'Analyze banana leaf';

  @override
  String get analyzing => 'Analyzing your banana plant...';

  @override
  String get analyzingSubtitle =>
      'The original image is saved securely and the real AI service is being contacted.';

  @override
  String get diagnosisFailed =>
      'Unable to analyze the image. Please check your internet connection and try again.';

  @override
  String get retry => 'Try again';

  @override
  String get diagnosis => 'Diagnosis';

  @override
  String get confidence => 'Confidence';

  @override
  String get severity => 'Severity';

  @override
  String get description => 'What this means';

  @override
  String get treatment => 'Management / treatment guidance';

  @override
  String get prevention => 'Prevention';

  @override
  String get additionalAdvice => 'Additional advice';

  @override
  String get expertRecommended => 'Expert assistance recommended';

  @override
  String get screeningWarning =>
      'AI screening is not a laboratory-confirmed diagnosis.';

  @override
  String get source => 'Source';

  @override
  String get sources => 'Sources';

  @override
  String get status => 'Status';

  @override
  String get healthy => 'Healthy';

  @override
  String get diseaseDetected => 'Disease detected';

  @override
  String get severe => 'Severe';

  @override
  String get latest => 'Latest';

  @override
  String get all => 'All';

  @override
  String get scanHistory => 'Scan history';

  @override
  String get openReport => 'Open report';

  @override
  String get noHistoryMatch => 'No scans match this filter.';

  @override
  String get bananaExpert => 'Banana Expert';

  @override
  String get expertSubtitle => 'RAG-grounded banana farming assistant';

  @override
  String get newChat => 'New chat';

  @override
  String get chatPlaceholder =>
      'Ask about symptoms, Panama disease, irrigation, prevention...';

  @override
  String get send => 'Send';

  @override
  String get listen => 'Listen';

  @override
  String get pause => 'Pause';

  @override
  String get stop => 'Stop';

  @override
  String get voiceQuestion => 'Ask by voice';

  @override
  String get listening => 'Listening...';

  @override
  String get recordVoiceNote => 'Record voice note';

  @override
  String get recording => 'Recording...';

  @override
  String get stopRecording => 'Stop recording';

  @override
  String get sendVoiceNote => 'Send voice note';

  @override
  String get attachImage => 'Attach image';

  @override
  String get chatImageNote => 'Add a note about this image';

  @override
  String get chatLocationQuestion =>
      'Share current location with this question';

  @override
  String get ragUnavailable =>
      'The AI knowledge service is not ready. No answer was fabricated.';

  @override
  String get chatEmpty => 'Start a conversation with Banana Expert.';

  @override
  String get settings => 'Settings';

  @override
  String get language => 'Language';

  @override
  String get notificationSettings => 'Notification settings';

  @override
  String get locationPermission => 'Location permission';

  @override
  String get appInformation => 'App information';

  @override
  String get privacy => 'Privacy';

  @override
  String get aboutHelp => 'About & help';

  @override
  String get preferredLanguage => 'Preferred language';

  @override
  String get editProfile => 'Edit profile';

  @override
  String get profileUpdated => 'Profile updated.';

  @override
  String get profilePhoto => 'Profile photo';

  @override
  String get account => 'Account';

  @override
  String get farm => 'Farm';

  @override
  String get addFarm => 'Add farm';

  @override
  String get editFarm => 'Edit farm';

  @override
  String get primaryFarm => 'Primary farm';

  @override
  String get offline => 'Offline';

  @override
  String get weakConnection => 'Weak or no connection';

  @override
  String get offlineBody =>
      'Firebase can keep cached data locally. New AI requests require a working connection; your selected image and note remain on this screen until you retry.';

  @override
  String get backendNotReady => 'AI service is not configured or not ready.';

  @override
  String get firebaseNotConfigured => 'Firebase configuration required';

  @override
  String get firebaseSetupBody =>
      'Copy config/dev.example.json to config/dev.json, add your real Firebase values, and run with --dart-define-from-file=config/dev.json.';

  @override
  String get apiNotConfigured => 'AI API URL required';

  @override
  String get apiSetupBody =>
      'Set AI_BASE_URL in config/dev.json to the real FastAPI server URL reachable from this phone.';

  @override
  String get notificationEmpty => 'No notifications yet.';

  @override
  String get helpTitle => 'How Banana Lifeline works';

  @override
  String get helpBody =>
      'Take a real banana leaf photo, record its exact farm location, submit it to the trained AI service, then use Banana Expert for source-grounded follow-up guidance.';

  @override
  String get privacyBody =>
      'Banana Lifeline stores your account details, farm information, images, location, chat and optional audio in your Firebase project. Camera, microphone and location are requested only when needed.';

  @override
  String get modelNotReadyBody =>
      'The friend AI ZIP does not contain a trained deployment checkpoint. The app will show an honest service error until a real checkpoint is configured on the backend.';

  @override
  String get unknown => 'Unknown';

  @override
  String get low => 'Low';

  @override
  String get medium => 'Medium';

  @override
  String get high => 'High';

  @override
  String get completed => 'Completed';

  @override
  String get failed => 'Failed';

  @override
  String get pending => 'Pending';

  @override
  String get processing => 'Processing';

  @override
  String get delete => 'Delete';

  @override
  String get close => 'Close';

  @override
  String get productCapabilities => 'Vision AI • RAG • Farm location • Voice';

  @override
  String get passwordMismatch => 'Passwords do not match.';

  @override
  String get signInFailed => 'Unable to sign in right now.';

  @override
  String get registerFailed => 'Unable to create account right now.';

  @override
  String get emailRequired => 'Enter your email address.';

  @override
  String get requiredField => 'This field is required.';

  @override
  String get farmLocationDetails => 'Farm location details';

  @override
  String get farmLocationHelp =>
      'Save the exact plot, row and plant so future disease checks can be traced inside the farm.';

  @override
  String get useSavedFarm => 'Use a saved farm';

  @override
  String get noSavedFarm => 'No saved farm yet';

  @override
  String get continueToPhoto => 'Continue to photo';

  @override
  String get changePhoto => 'Change photo';

  @override
  String get removePhoto => 'Remove photo';

  @override
  String get reviewBeforeSubmit => 'Review before submitting';

  @override
  String get leafPhotoGuidance =>
      'Use natural daylight, keep one banana leaf in focus, and avoid blur or strong shadows.';

  @override
  String get modelScopeNotice => 'Current AI scope';

  @override
  String get locationCaptured => 'Location captured.';

  @override
  String get useManualLocation => 'Use manual location';

  @override
  String get locationOptional =>
      'GPS is recommended, but you can enter a farm place manually if unavailable.';

  @override
  String get imageUploadFailed =>
      'The image could not be uploaded. Your note remains on this screen.';

  @override
  String get realAiNotice =>
      'This scan is sent to the configured real AI service. No sample diagnosis is generated by the app.';

  @override
  String get scanStatus => 'Scan status';

  @override
  String get scanFailedReason => 'The AI service did not complete this scan.';

  @override
  String get modelServiceNotReady =>
      'The trained model service is not ready yet. No diagnosis was fabricated.';

  @override
  String get askAboutThisScan => 'Ask about this scan';

  @override
  String get exactFarmPlace => 'Exact farm place';

  @override
  String get coordinates => 'Coordinates';

  @override
  String get noCoordinates => 'No GPS coordinates saved';

  @override
  String get aiSources => 'Knowledge sources';

  @override
  String get noGuidanceAvailable =>
      'No grounded guidance was returned by the knowledge service.';

  @override
  String get chatSessions => 'Banana Expert chats';

  @override
  String get noChats => 'No chat sessions yet.';

  @override
  String get newConversation => 'Start a new conversation';

  @override
  String get imageAttached => 'Image attached';

  @override
  String get locationShared => 'Location shared';

  @override
  String get addImageNote => 'Add a note about what you see in the image';

  @override
  String get captureLocation => 'Capture location';

  @override
  String get sendImageQuestion => 'Send image + question';

  @override
  String get voiceNoteReady => 'Voice note ready';

  @override
  String get voiceNoteFailed =>
      'The voice note could not be transcribed. It was not sent to AI.';

  @override
  String get micPermissionHelp => 'Microphone access is needed for voice chat.';

  @override
  String get photoPermissionHelp =>
      'Camera or photo access is needed to send a banana leaf image.';

  @override
  String get playVoice => 'Play voice note';

  @override
  String get stopVoice => 'Stop audio';

  @override
  String get aiThinking => 'Banana Expert is checking trusted sources...';

  @override
  String get noReliableAnswer =>
      'No reliable answer was returned. Try a clearer question or contact an agriculture expert.';

  @override
  String get shareLocation => 'Share current location';

  @override
  String get chatContextNote =>
      'Messages in this chat stay in the same context and are stored in your Firebase account.';

  @override
  String get farmerProfile => 'Farmer profile';

  @override
  String get farmRecords => 'Farm records';

  @override
  String get noFarms => 'No farms saved yet.';

  @override
  String get farmAddress => 'Farm address';

  @override
  String get farmSaved => 'Farm saved.';

  @override
  String get profileImagePick => 'Choose profile photo';

  @override
  String get saveChanges => 'Save changes';

  @override
  String get notificationPermissionEnabled =>
      'Notification permission requested and this device was registered.';

  @override
  String get markRead => 'Mark as read';

  @override
  String get aboutTitle => 'Banana Lifeline';

  @override
  String get aboutSubtitle =>
      'AI-assisted banana disease early warning and source-grounded farmer support.';

  @override
  String get whatAppDoes => 'What this app does';

  @override
  String get scientificScope => 'Scientific scope';

  @override
  String get scientificScopeBody =>
      'The supplied classifier is trained on banana leaf images. Panama predictions are screening signals only and should be confirmed using field signs and expert or laboratory review.';

  @override
  String get privacyTitle => 'Privacy & permissions';

  @override
  String get logoutConfirm => 'Log out of Banana Lifeline?';

  @override
  String get yesLogout => 'Log out';

  @override
  String get latestFirst => 'Latest first';

  @override
  String get errorTryAgain => 'Something went wrong. Please try again.';

  @override
  String get refresh => 'Refresh';

  @override
  String get noInternetAi =>
      'AI requests need internet. Firebase may still show previously cached scans and chats.';

  @override
  String get apiHealth => 'AI service status';

  @override
  String get checkApi => 'Check AI service';

  @override
  String get visionReady => 'Vision model ready';

  @override
  String get ragReady => 'RAG knowledge ready';

  @override
  String get generationReady => 'Answer generation ready';

  @override
  String get notReady => 'Not ready';

  @override
  String get ready => 'Ready';

  @override
  String get farmRiskHigh => 'A recent high-risk scan needs attention.';

  @override
  String get farmRiskMedium => 'A recent scan needs review or monitoring.';

  @override
  String get farmRiskLow => 'No high-risk diagnosis is currently stored.';

  @override
  String recentCheckCount(int count) {
    return '$count recent checks';
  }

  @override
  String get noProfile => 'Farmer profile not found.';

  @override
  String get created => 'Created';

  @override
  String get openSettings => 'Open settings';

  @override
  String get locationSettingsHelp =>
      'If permission is permanently denied, enable location from your phone settings.';

  @override
  String get healthCheckFailed => 'Could not reach the AI server.';

  @override
  String get chatSendFailed =>
      'Your message could not be sent. It remains in the text box so you can retry.';

  @override
  String get audioTranscribing => 'Transcribing voice note...';

  @override
  String get uploading => 'Uploading...';

  @override
  String get processingImage => 'Analyzing your banana leaf...';

  @override
  String get viewDetails => 'View details';

  @override
  String sourcePage(int page) {
    return 'Page $page';
  }

  @override
  String get chatImageLeafOnly =>
      'The current vision classifier accepts banana leaf images only.';

  @override
  String get deleteFarm => 'Delete farm';

  @override
  String get farmNameRequired => 'Farm name is required.';

  @override
  String get permissions => 'Permissions';

  @override
  String get notificationPermission => 'Notification permission';

  @override
  String get cameraPermission => 'Camera permission';

  @override
  String get microphonePermission => 'Microphone permission';

  @override
  String get locationPermissionInfo =>
      'Location is used only when you choose to attach a farm place to a scan or chat question.';

  @override
  String get edit => 'Edit';

  @override
  String get add => 'Add';

  @override
  String get done => 'Done';

  @override
  String get back => 'Back';

  @override
  String get next => 'Next';

  @override
  String get viewOnMap => 'Map coordinates';

  @override
  String get serviceUnavailable => 'Service unavailable';

  @override
  String get relatedScan => 'Related scan';

  @override
  String get conversationSources => 'Sources used for this answer';

  @override
  String get emptyNote => 'No note added';

  @override
  String get profileEmail => 'Account email';

  @override
  String get farmSizeHint => 'e.g. 5 acres';

  @override
  String get cropInfoHint => 'e.g. Banana, Cavendish';

  @override
  String get districtHint => 'e.g. Tando Allahyar';

  @override
  String get provinceHint => 'e.g. Sindh';

  @override
  String get processingWarning =>
      'Keep this screen open while the image uploads and the AI service responds.';

  @override
  String get notificationInfo =>
      'Notifications are created only from real backend events such as a completed high-risk diagnosis.';

  @override
  String get authInvalidEmail => 'Please enter a valid email address.';

  @override
  String get authWrongCredentials => 'Email or password is incorrect.';

  @override
  String get authEmailInUse => 'An account already exists with this email.';

  @override
  String get authWeakPassword => 'Please use a stronger password.';

  @override
  String get authTooMany => 'Too many attempts. Please try again later.';

  @override
  String get authGeneric =>
      'Authentication could not be completed. Please try again.';

  @override
  String get farmerFallback => 'Farmer';

  @override
  String get diagnosisStatusProcessing => 'Processing';

  @override
  String get diagnosisStatusFailed => 'Failed';

  @override
  String get diagnosisStatusCompleted => 'Completed';

  @override
  String get diagnosisStatusPending => 'Pending';

  @override
  String get severityUnknown => 'Unknown';

  @override
  String get retryDiagnosis => 'Retry diagnosis';

  @override
  String get retryingDiagnosis => 'Retrying diagnosis...';

  @override
  String get retryStarted => 'Diagnosis retry started.';

  @override
  String get retryFailed =>
      'Could not retry diagnosis. Please check the AI service and internet connection.';

  @override
  String get manualFarmPlace => 'Manual farm place';

  @override
  String get imageLocation => 'Image location';

  @override
  String get realServiceOnly => 'Real service only';

  @override
  String get scanAgain => 'Start a new scan';

  @override
  String get savedOfflineTitle => 'Saved on this phone';

  @override
  String get savedOfflineBody =>
      'The upload could not be completed. Your photo, farm place and note were saved locally so you can retry without losing them.';

  @override
  String get pendingUploads => 'Pending uploads';

  @override
  String get pendingUploadsHelp =>
      'These real scan drafts are stored on this device until Firebase upload succeeds.';

  @override
  String get retryUpload => 'Retry upload';

  @override
  String get removePending => 'Remove';

  @override
  String get pendingUploadRetrying => 'Retrying upload…';

  @override
  String get pendingUploadSuccess =>
      'Upload completed. The scan is now in your Firebase history.';

  @override
  String get pendingUploadFailed =>
      'Upload still could not be completed. The draft remains safely on this phone.';

  @override
  String get noPendingUploads => 'No pending uploads.';
}
