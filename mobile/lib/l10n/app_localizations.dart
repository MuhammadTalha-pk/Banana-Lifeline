import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_ur.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('ur'),
  ];

  /// No description provided for @appName.
  ///
  /// In en, this message translates to:
  /// **'Banana Lifeline'**
  String get appName;

  /// No description provided for @tagline.
  ///
  /// In en, this message translates to:
  /// **'Detect early. Act early. Protect the farm.'**
  String get tagline;

  /// No description provided for @continueLabel.
  ///
  /// In en, this message translates to:
  /// **'Continue'**
  String get continueLabel;

  /// No description provided for @getStarted.
  ///
  /// In en, this message translates to:
  /// **'Get started'**
  String get getStarted;

  /// No description provided for @english.
  ///
  /// In en, this message translates to:
  /// **'English'**
  String get english;

  /// No description provided for @urdu.
  ///
  /// In en, this message translates to:
  /// **'Urdu'**
  String get urdu;

  /// No description provided for @login.
  ///
  /// In en, this message translates to:
  /// **'Login'**
  String get login;

  /// No description provided for @register.
  ///
  /// In en, this message translates to:
  /// **'Create account'**
  String get register;

  /// No description provided for @logout.
  ///
  /// In en, this message translates to:
  /// **'Logout'**
  String get logout;

  /// No description provided for @email.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get email;

  /// No description provided for @password.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get password;

  /// No description provided for @confirmPassword.
  ///
  /// In en, this message translates to:
  /// **'Confirm password'**
  String get confirmPassword;

  /// No description provided for @fullName.
  ///
  /// In en, this message translates to:
  /// **'Full name'**
  String get fullName;

  /// No description provided for @phone.
  ///
  /// In en, this message translates to:
  /// **'Phone number'**
  String get phone;

  /// No description provided for @forgotPassword.
  ///
  /// In en, this message translates to:
  /// **'Forgot password?'**
  String get forgotPassword;

  /// No description provided for @resetPassword.
  ///
  /// In en, this message translates to:
  /// **'Reset password'**
  String get resetPassword;

  /// No description provided for @resetEmailSent.
  ///
  /// In en, this message translates to:
  /// **'Password reset email sent.'**
  String get resetEmailSent;

  /// No description provided for @noAccount.
  ///
  /// In en, this message translates to:
  /// **'New to Banana Lifeline?'**
  String get noAccount;

  /// No description provided for @haveAccount.
  ///
  /// In en, this message translates to:
  /// **'Already have an account?'**
  String get haveAccount;

  /// No description provided for @welcomeBack.
  ///
  /// In en, this message translates to:
  /// **'Welcome back'**
  String get welcomeBack;

  /// No description provided for @authSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Sign in to access your farm scans and Banana Expert.'**
  String get authSubtitle;

  /// No description provided for @createFarmerProfile.
  ///
  /// In en, this message translates to:
  /// **'Create your farmer profile'**
  String get createFarmerProfile;

  /// No description provided for @province.
  ///
  /// In en, this message translates to:
  /// **'Province'**
  String get province;

  /// No description provided for @district.
  ///
  /// In en, this message translates to:
  /// **'District'**
  String get district;

  /// No description provided for @farmSize.
  ///
  /// In en, this message translates to:
  /// **'Farm size'**
  String get farmSize;

  /// No description provided for @cropInfo.
  ///
  /// In en, this message translates to:
  /// **'Crop information'**
  String get cropInfo;

  /// No description provided for @save.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get save;

  /// No description provided for @cancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancel;

  /// No description provided for @home.
  ///
  /// In en, this message translates to:
  /// **'Home'**
  String get home;

  /// No description provided for @scan.
  ///
  /// In en, this message translates to:
  /// **'Scan'**
  String get scan;

  /// No description provided for @aiChat.
  ///
  /// In en, this message translates to:
  /// **'AI Chat'**
  String get aiChat;

  /// No description provided for @history.
  ///
  /// In en, this message translates to:
  /// **'History'**
  String get history;

  /// No description provided for @profile.
  ///
  /// In en, this message translates to:
  /// **'Profile'**
  String get profile;

  /// No description provided for @goodMorning.
  ///
  /// In en, this message translates to:
  /// **'Good morning, {name}'**
  String goodMorning(String name);

  /// No description provided for @dashboardSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Check suspicious banana leaves early and keep a real plot-by-plot record.'**
  String get dashboardSubtitle;

  /// No description provided for @farmRisk.
  ///
  /// In en, this message translates to:
  /// **'Farm risk level'**
  String get farmRisk;

  /// No description provided for @farmRiskEmpty.
  ///
  /// In en, this message translates to:
  /// **'No severe diagnosis is currently recorded in your scan history.'**
  String get farmRiskEmpty;

  /// No description provided for @scanNow.
  ///
  /// In en, this message translates to:
  /// **'Scan now'**
  String get scanNow;

  /// No description provided for @scanNowSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Take a real leaf photo, add its farm place, and send it to the AI model.'**
  String get scanNowSubtitle;

  /// No description provided for @askExpert.
  ///
  /// In en, this message translates to:
  /// **'Ask Banana Expert'**
  String get askExpert;

  /// No description provided for @recentChecks.
  ///
  /// In en, this message translates to:
  /// **'Recent checks'**
  String get recentChecks;

  /// No description provided for @seeAll.
  ///
  /// In en, this message translates to:
  /// **'See all'**
  String get seeAll;

  /// No description provided for @noScans.
  ///
  /// In en, this message translates to:
  /// **'No scans yet'**
  String get noScans;

  /// No description provided for @noScansSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Your real AI diagnosis history will appear here after your first scan.'**
  String get noScansSubtitle;

  /// No description provided for @currentLocation.
  ///
  /// In en, this message translates to:
  /// **'Current location'**
  String get currentLocation;

  /// No description provided for @notifications.
  ///
  /// In en, this message translates to:
  /// **'Notifications'**
  String get notifications;

  /// No description provided for @farmInformation.
  ///
  /// In en, this message translates to:
  /// **'Farm information'**
  String get farmInformation;

  /// No description provided for @newScan.
  ///
  /// In en, this message translates to:
  /// **'New banana leaf scan'**
  String get newScan;

  /// No description provided for @leafOnlyTitle.
  ///
  /// In en, this message translates to:
  /// **'Current model scope: leaf images'**
  String get leafOnlyTitle;

  /// No description provided for @leafOnlyBody.
  ///
  /// In en, this message translates to:
  /// **'The supplied AI dataset is made of banana leaf photos. Stem, fruit, corm and whole-plant photos are not sent to this classifier.'**
  String get leafOnlyBody;

  /// No description provided for @takePhoto.
  ///
  /// In en, this message translates to:
  /// **'Take photo'**
  String get takePhoto;

  /// No description provided for @chooseGallery.
  ///
  /// In en, this message translates to:
  /// **'Choose from gallery'**
  String get chooseGallery;

  /// No description provided for @imageRequired.
  ///
  /// In en, this message translates to:
  /// **'Please take or select a banana leaf photo.'**
  String get imageRequired;

  /// No description provided for @farmPlace.
  ///
  /// In en, this message translates to:
  /// **'Place in farm'**
  String get farmPlace;

  /// No description provided for @farmName.
  ///
  /// In en, this message translates to:
  /// **'Farm name'**
  String get farmName;

  /// No description provided for @plotSector.
  ///
  /// In en, this message translates to:
  /// **'Plot / Sector'**
  String get plotSector;

  /// No description provided for @row.
  ///
  /// In en, this message translates to:
  /// **'Row'**
  String get row;

  /// No description provided for @plantNumber.
  ///
  /// In en, this message translates to:
  /// **'Plant number'**
  String get plantNumber;

  /// No description provided for @note.
  ///
  /// In en, this message translates to:
  /// **'Farmer note'**
  String get note;

  /// No description provided for @noteHint.
  ///
  /// In en, this message translates to:
  /// **'What are you seeing on this plant?'**
  String get noteHint;

  /// No description provided for @gpsLocation.
  ///
  /// In en, this message translates to:
  /// **'GPS location'**
  String get gpsLocation;

  /// No description provided for @captureGps.
  ///
  /// In en, this message translates to:
  /// **'Capture GPS'**
  String get captureGps;

  /// No description provided for @manualAddress.
  ///
  /// In en, this message translates to:
  /// **'Manual address / landmark'**
  String get manualAddress;

  /// No description provided for @locationUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Location unavailable'**
  String get locationUnavailable;

  /// No description provided for @locationPermissionDenied.
  ///
  /// In en, this message translates to:
  /// **'Location permission was denied. You can enter the place manually.'**
  String get locationPermissionDenied;

  /// No description provided for @locationServicesOff.
  ///
  /// In en, this message translates to:
  /// **'GPS is disabled. Enable location services or enter the place manually.'**
  String get locationServicesOff;

  /// No description provided for @preview.
  ///
  /// In en, this message translates to:
  /// **'Review scan'**
  String get preview;

  /// No description provided for @photo.
  ///
  /// In en, this message translates to:
  /// **'Plant image'**
  String get photo;

  /// No description provided for @dateTime.
  ///
  /// In en, this message translates to:
  /// **'Date & time'**
  String get dateTime;

  /// No description provided for @latitude.
  ///
  /// In en, this message translates to:
  /// **'Latitude'**
  String get latitude;

  /// No description provided for @longitude.
  ///
  /// In en, this message translates to:
  /// **'Longitude'**
  String get longitude;

  /// No description provided for @address.
  ///
  /// In en, this message translates to:
  /// **'Address'**
  String get address;

  /// No description provided for @submitForDiagnosis.
  ///
  /// In en, this message translates to:
  /// **'Analyze banana leaf'**
  String get submitForDiagnosis;

  /// No description provided for @analyzing.
  ///
  /// In en, this message translates to:
  /// **'Analyzing your banana plant...'**
  String get analyzing;

  /// No description provided for @analyzingSubtitle.
  ///
  /// In en, this message translates to:
  /// **'The original image is saved securely and the real AI service is being contacted.'**
  String get analyzingSubtitle;

  /// No description provided for @diagnosisFailed.
  ///
  /// In en, this message translates to:
  /// **'Unable to analyze the image. Please check your internet connection and try again.'**
  String get diagnosisFailed;

  /// No description provided for @retry.
  ///
  /// In en, this message translates to:
  /// **'Try again'**
  String get retry;

  /// No description provided for @diagnosis.
  ///
  /// In en, this message translates to:
  /// **'Diagnosis'**
  String get diagnosis;

  /// No description provided for @confidence.
  ///
  /// In en, this message translates to:
  /// **'Confidence'**
  String get confidence;

  /// No description provided for @severity.
  ///
  /// In en, this message translates to:
  /// **'Severity'**
  String get severity;

  /// No description provided for @description.
  ///
  /// In en, this message translates to:
  /// **'What this means'**
  String get description;

  /// No description provided for @treatment.
  ///
  /// In en, this message translates to:
  /// **'Management / treatment guidance'**
  String get treatment;

  /// No description provided for @prevention.
  ///
  /// In en, this message translates to:
  /// **'Prevention'**
  String get prevention;

  /// No description provided for @additionalAdvice.
  ///
  /// In en, this message translates to:
  /// **'Additional advice'**
  String get additionalAdvice;

  /// No description provided for @expertRecommended.
  ///
  /// In en, this message translates to:
  /// **'Expert assistance recommended'**
  String get expertRecommended;

  /// No description provided for @screeningWarning.
  ///
  /// In en, this message translates to:
  /// **'AI screening is not a laboratory-confirmed diagnosis.'**
  String get screeningWarning;

  /// No description provided for @source.
  ///
  /// In en, this message translates to:
  /// **'Source'**
  String get source;

  /// No description provided for @sources.
  ///
  /// In en, this message translates to:
  /// **'Sources'**
  String get sources;

  /// No description provided for @status.
  ///
  /// In en, this message translates to:
  /// **'Status'**
  String get status;

  /// No description provided for @healthy.
  ///
  /// In en, this message translates to:
  /// **'Healthy'**
  String get healthy;

  /// No description provided for @diseaseDetected.
  ///
  /// In en, this message translates to:
  /// **'Disease detected'**
  String get diseaseDetected;

  /// No description provided for @severe.
  ///
  /// In en, this message translates to:
  /// **'Severe'**
  String get severe;

  /// No description provided for @latest.
  ///
  /// In en, this message translates to:
  /// **'Latest'**
  String get latest;

  /// No description provided for @all.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get all;

  /// No description provided for @scanHistory.
  ///
  /// In en, this message translates to:
  /// **'Scan history'**
  String get scanHistory;

  /// No description provided for @openReport.
  ///
  /// In en, this message translates to:
  /// **'Open report'**
  String get openReport;

  /// No description provided for @noHistoryMatch.
  ///
  /// In en, this message translates to:
  /// **'No scans match this filter.'**
  String get noHistoryMatch;

  /// No description provided for @bananaExpert.
  ///
  /// In en, this message translates to:
  /// **'Banana Expert'**
  String get bananaExpert;

  /// No description provided for @expertSubtitle.
  ///
  /// In en, this message translates to:
  /// **'RAG-grounded banana farming assistant'**
  String get expertSubtitle;

  /// No description provided for @newChat.
  ///
  /// In en, this message translates to:
  /// **'New chat'**
  String get newChat;

  /// No description provided for @chatPlaceholder.
  ///
  /// In en, this message translates to:
  /// **'Ask about symptoms, Panama disease, irrigation, prevention...'**
  String get chatPlaceholder;

  /// No description provided for @send.
  ///
  /// In en, this message translates to:
  /// **'Send'**
  String get send;

  /// No description provided for @listen.
  ///
  /// In en, this message translates to:
  /// **'Listen'**
  String get listen;

  /// No description provided for @pause.
  ///
  /// In en, this message translates to:
  /// **'Pause'**
  String get pause;

  /// No description provided for @stop.
  ///
  /// In en, this message translates to:
  /// **'Stop'**
  String get stop;

  /// No description provided for @voiceQuestion.
  ///
  /// In en, this message translates to:
  /// **'Ask by voice'**
  String get voiceQuestion;

  /// No description provided for @listening.
  ///
  /// In en, this message translates to:
  /// **'Listening...'**
  String get listening;

  /// No description provided for @recordVoiceNote.
  ///
  /// In en, this message translates to:
  /// **'Record voice note'**
  String get recordVoiceNote;

  /// No description provided for @recording.
  ///
  /// In en, this message translates to:
  /// **'Recording...'**
  String get recording;

  /// No description provided for @stopRecording.
  ///
  /// In en, this message translates to:
  /// **'Stop recording'**
  String get stopRecording;

  /// No description provided for @sendVoiceNote.
  ///
  /// In en, this message translates to:
  /// **'Send voice note'**
  String get sendVoiceNote;

  /// No description provided for @attachImage.
  ///
  /// In en, this message translates to:
  /// **'Attach image'**
  String get attachImage;

  /// No description provided for @chatImageNote.
  ///
  /// In en, this message translates to:
  /// **'Add a note about this image'**
  String get chatImageNote;

  /// No description provided for @chatLocationQuestion.
  ///
  /// In en, this message translates to:
  /// **'Share current location with this question'**
  String get chatLocationQuestion;

  /// No description provided for @ragUnavailable.
  ///
  /// In en, this message translates to:
  /// **'The AI knowledge service is not ready. No answer was fabricated.'**
  String get ragUnavailable;

  /// No description provided for @chatEmpty.
  ///
  /// In en, this message translates to:
  /// **'Start a conversation with Banana Expert.'**
  String get chatEmpty;

  /// No description provided for @settings.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get settings;

  /// No description provided for @language.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get language;

  /// No description provided for @notificationSettings.
  ///
  /// In en, this message translates to:
  /// **'Notification settings'**
  String get notificationSettings;

  /// No description provided for @locationPermission.
  ///
  /// In en, this message translates to:
  /// **'Location permission'**
  String get locationPermission;

  /// No description provided for @appInformation.
  ///
  /// In en, this message translates to:
  /// **'App information'**
  String get appInformation;

  /// No description provided for @privacy.
  ///
  /// In en, this message translates to:
  /// **'Privacy'**
  String get privacy;

  /// No description provided for @aboutHelp.
  ///
  /// In en, this message translates to:
  /// **'About & help'**
  String get aboutHelp;

  /// No description provided for @preferredLanguage.
  ///
  /// In en, this message translates to:
  /// **'Preferred language'**
  String get preferredLanguage;

  /// No description provided for @editProfile.
  ///
  /// In en, this message translates to:
  /// **'Edit profile'**
  String get editProfile;

  /// No description provided for @profileUpdated.
  ///
  /// In en, this message translates to:
  /// **'Profile updated.'**
  String get profileUpdated;

  /// No description provided for @profilePhoto.
  ///
  /// In en, this message translates to:
  /// **'Profile photo'**
  String get profilePhoto;

  /// No description provided for @account.
  ///
  /// In en, this message translates to:
  /// **'Account'**
  String get account;

  /// No description provided for @farm.
  ///
  /// In en, this message translates to:
  /// **'Farm'**
  String get farm;

  /// No description provided for @addFarm.
  ///
  /// In en, this message translates to:
  /// **'Add farm'**
  String get addFarm;

  /// No description provided for @editFarm.
  ///
  /// In en, this message translates to:
  /// **'Edit farm'**
  String get editFarm;

  /// No description provided for @primaryFarm.
  ///
  /// In en, this message translates to:
  /// **'Primary farm'**
  String get primaryFarm;

  /// No description provided for @offline.
  ///
  /// In en, this message translates to:
  /// **'Offline'**
  String get offline;

  /// No description provided for @weakConnection.
  ///
  /// In en, this message translates to:
  /// **'Weak or no connection'**
  String get weakConnection;

  /// No description provided for @offlineBody.
  ///
  /// In en, this message translates to:
  /// **'Firebase can keep cached data locally. New AI requests require a working connection; your selected image and note remain on this screen until you retry.'**
  String get offlineBody;

  /// No description provided for @backendNotReady.
  ///
  /// In en, this message translates to:
  /// **'AI service is not configured or not ready.'**
  String get backendNotReady;

  /// No description provided for @firebaseNotConfigured.
  ///
  /// In en, this message translates to:
  /// **'Firebase configuration required'**
  String get firebaseNotConfigured;

  /// No description provided for @firebaseSetupBody.
  ///
  /// In en, this message translates to:
  /// **'Copy config/dev.example.json to config/dev.json, add your real Firebase values, and run with --dart-define-from-file=config/dev.json.'**
  String get firebaseSetupBody;

  /// No description provided for @apiNotConfigured.
  ///
  /// In en, this message translates to:
  /// **'AI API URL required'**
  String get apiNotConfigured;

  /// No description provided for @apiSetupBody.
  ///
  /// In en, this message translates to:
  /// **'Set AI_BASE_URL in config/dev.json to the real FastAPI server URL reachable from this phone.'**
  String get apiSetupBody;

  /// No description provided for @notificationEmpty.
  ///
  /// In en, this message translates to:
  /// **'No notifications yet.'**
  String get notificationEmpty;

  /// No description provided for @helpTitle.
  ///
  /// In en, this message translates to:
  /// **'How Banana Lifeline works'**
  String get helpTitle;

  /// No description provided for @helpBody.
  ///
  /// In en, this message translates to:
  /// **'Take a real banana leaf photo, record its exact farm location, submit it to the trained AI service, then use Banana Expert for source-grounded follow-up guidance.'**
  String get helpBody;

  /// No description provided for @privacyBody.
  ///
  /// In en, this message translates to:
  /// **'Banana Lifeline stores your account details, farm information, images, location, chat and optional audio in your Firebase project. Camera, microphone and location are requested only when needed.'**
  String get privacyBody;

  /// No description provided for @modelNotReadyBody.
  ///
  /// In en, this message translates to:
  /// **'The friend AI ZIP does not contain a trained deployment checkpoint. The app will show an honest service error until a real checkpoint is configured on the backend.'**
  String get modelNotReadyBody;

  /// No description provided for @unknown.
  ///
  /// In en, this message translates to:
  /// **'Unknown'**
  String get unknown;

  /// No description provided for @low.
  ///
  /// In en, this message translates to:
  /// **'Low'**
  String get low;

  /// No description provided for @medium.
  ///
  /// In en, this message translates to:
  /// **'Medium'**
  String get medium;

  /// No description provided for @high.
  ///
  /// In en, this message translates to:
  /// **'High'**
  String get high;

  /// No description provided for @completed.
  ///
  /// In en, this message translates to:
  /// **'Completed'**
  String get completed;

  /// No description provided for @failed.
  ///
  /// In en, this message translates to:
  /// **'Failed'**
  String get failed;

  /// No description provided for @pending.
  ///
  /// In en, this message translates to:
  /// **'Pending'**
  String get pending;

  /// No description provided for @processing.
  ///
  /// In en, this message translates to:
  /// **'Processing'**
  String get processing;

  /// No description provided for @delete.
  ///
  /// In en, this message translates to:
  /// **'Delete'**
  String get delete;

  /// No description provided for @close.
  ///
  /// In en, this message translates to:
  /// **'Close'**
  String get close;

  /// No description provided for @productCapabilities.
  ///
  /// In en, this message translates to:
  /// **'Vision AI • RAG • Farm location • Voice'**
  String get productCapabilities;

  /// No description provided for @passwordMismatch.
  ///
  /// In en, this message translates to:
  /// **'Passwords do not match.'**
  String get passwordMismatch;

  /// No description provided for @signInFailed.
  ///
  /// In en, this message translates to:
  /// **'Unable to sign in right now.'**
  String get signInFailed;

  /// No description provided for @registerFailed.
  ///
  /// In en, this message translates to:
  /// **'Unable to create account right now.'**
  String get registerFailed;

  /// No description provided for @emailRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter your email address.'**
  String get emailRequired;

  /// No description provided for @requiredField.
  ///
  /// In en, this message translates to:
  /// **'This field is required.'**
  String get requiredField;

  /// No description provided for @farmLocationDetails.
  ///
  /// In en, this message translates to:
  /// **'Farm location details'**
  String get farmLocationDetails;

  /// No description provided for @farmLocationHelp.
  ///
  /// In en, this message translates to:
  /// **'Save the exact plot, row and plant so future disease checks can be traced inside the farm.'**
  String get farmLocationHelp;

  /// No description provided for @useSavedFarm.
  ///
  /// In en, this message translates to:
  /// **'Use a saved farm'**
  String get useSavedFarm;

  /// No description provided for @noSavedFarm.
  ///
  /// In en, this message translates to:
  /// **'No saved farm yet'**
  String get noSavedFarm;

  /// No description provided for @continueToPhoto.
  ///
  /// In en, this message translates to:
  /// **'Continue to photo'**
  String get continueToPhoto;

  /// No description provided for @changePhoto.
  ///
  /// In en, this message translates to:
  /// **'Change photo'**
  String get changePhoto;

  /// No description provided for @removePhoto.
  ///
  /// In en, this message translates to:
  /// **'Remove photo'**
  String get removePhoto;

  /// No description provided for @reviewBeforeSubmit.
  ///
  /// In en, this message translates to:
  /// **'Review before submitting'**
  String get reviewBeforeSubmit;

  /// No description provided for @leafPhotoGuidance.
  ///
  /// In en, this message translates to:
  /// **'Use natural daylight, keep one banana leaf in focus, and avoid blur or strong shadows.'**
  String get leafPhotoGuidance;

  /// No description provided for @modelScopeNotice.
  ///
  /// In en, this message translates to:
  /// **'Current AI scope'**
  String get modelScopeNotice;

  /// No description provided for @locationCaptured.
  ///
  /// In en, this message translates to:
  /// **'Location captured.'**
  String get locationCaptured;

  /// No description provided for @useManualLocation.
  ///
  /// In en, this message translates to:
  /// **'Use manual location'**
  String get useManualLocation;

  /// No description provided for @locationOptional.
  ///
  /// In en, this message translates to:
  /// **'GPS is recommended, but you can enter a farm place manually if unavailable.'**
  String get locationOptional;

  /// No description provided for @imageUploadFailed.
  ///
  /// In en, this message translates to:
  /// **'The image could not be uploaded. Your note remains on this screen.'**
  String get imageUploadFailed;

  /// No description provided for @realAiNotice.
  ///
  /// In en, this message translates to:
  /// **'This scan is sent to the configured real AI service. No sample diagnosis is generated by the app.'**
  String get realAiNotice;

  /// No description provided for @scanStatus.
  ///
  /// In en, this message translates to:
  /// **'Scan status'**
  String get scanStatus;

  /// No description provided for @scanFailedReason.
  ///
  /// In en, this message translates to:
  /// **'The AI service did not complete this scan.'**
  String get scanFailedReason;

  /// No description provided for @modelServiceNotReady.
  ///
  /// In en, this message translates to:
  /// **'The trained model service is not ready yet. No diagnosis was fabricated.'**
  String get modelServiceNotReady;

  /// No description provided for @askAboutThisScan.
  ///
  /// In en, this message translates to:
  /// **'Ask about this scan'**
  String get askAboutThisScan;

  /// No description provided for @exactFarmPlace.
  ///
  /// In en, this message translates to:
  /// **'Exact farm place'**
  String get exactFarmPlace;

  /// No description provided for @coordinates.
  ///
  /// In en, this message translates to:
  /// **'Coordinates'**
  String get coordinates;

  /// No description provided for @noCoordinates.
  ///
  /// In en, this message translates to:
  /// **'No GPS coordinates saved'**
  String get noCoordinates;

  /// No description provided for @aiSources.
  ///
  /// In en, this message translates to:
  /// **'Knowledge sources'**
  String get aiSources;

  /// No description provided for @noGuidanceAvailable.
  ///
  /// In en, this message translates to:
  /// **'No grounded guidance was returned by the knowledge service.'**
  String get noGuidanceAvailable;

  /// No description provided for @chatSessions.
  ///
  /// In en, this message translates to:
  /// **'Banana Expert chats'**
  String get chatSessions;

  /// No description provided for @noChats.
  ///
  /// In en, this message translates to:
  /// **'No chat sessions yet.'**
  String get noChats;

  /// No description provided for @newConversation.
  ///
  /// In en, this message translates to:
  /// **'Start a new conversation'**
  String get newConversation;

  /// No description provided for @imageAttached.
  ///
  /// In en, this message translates to:
  /// **'Image attached'**
  String get imageAttached;

  /// No description provided for @locationShared.
  ///
  /// In en, this message translates to:
  /// **'Location shared'**
  String get locationShared;

  /// No description provided for @addImageNote.
  ///
  /// In en, this message translates to:
  /// **'Add a note about what you see in the image'**
  String get addImageNote;

  /// No description provided for @captureLocation.
  ///
  /// In en, this message translates to:
  /// **'Capture location'**
  String get captureLocation;

  /// No description provided for @sendImageQuestion.
  ///
  /// In en, this message translates to:
  /// **'Send image + question'**
  String get sendImageQuestion;

  /// No description provided for @voiceNoteReady.
  ///
  /// In en, this message translates to:
  /// **'Voice note ready'**
  String get voiceNoteReady;

  /// No description provided for @voiceNoteFailed.
  ///
  /// In en, this message translates to:
  /// **'The voice note could not be transcribed. It was not sent to AI.'**
  String get voiceNoteFailed;

  /// No description provided for @micPermissionHelp.
  ///
  /// In en, this message translates to:
  /// **'Microphone access is needed for voice chat.'**
  String get micPermissionHelp;

  /// No description provided for @photoPermissionHelp.
  ///
  /// In en, this message translates to:
  /// **'Camera or photo access is needed to send a banana leaf image.'**
  String get photoPermissionHelp;

  /// No description provided for @playVoice.
  ///
  /// In en, this message translates to:
  /// **'Play voice note'**
  String get playVoice;

  /// No description provided for @stopVoice.
  ///
  /// In en, this message translates to:
  /// **'Stop audio'**
  String get stopVoice;

  /// No description provided for @aiThinking.
  ///
  /// In en, this message translates to:
  /// **'Banana Expert is checking trusted sources...'**
  String get aiThinking;

  /// No description provided for @noReliableAnswer.
  ///
  /// In en, this message translates to:
  /// **'No reliable answer was returned. Try a clearer question or contact an agriculture expert.'**
  String get noReliableAnswer;

  /// No description provided for @shareLocation.
  ///
  /// In en, this message translates to:
  /// **'Share current location'**
  String get shareLocation;

  /// No description provided for @chatContextNote.
  ///
  /// In en, this message translates to:
  /// **'Messages in this chat stay in the same context and are stored in your Firebase account.'**
  String get chatContextNote;

  /// No description provided for @farmerProfile.
  ///
  /// In en, this message translates to:
  /// **'Farmer profile'**
  String get farmerProfile;

  /// No description provided for @farmRecords.
  ///
  /// In en, this message translates to:
  /// **'Farm records'**
  String get farmRecords;

  /// No description provided for @noFarms.
  ///
  /// In en, this message translates to:
  /// **'No farms saved yet.'**
  String get noFarms;

  /// No description provided for @farmAddress.
  ///
  /// In en, this message translates to:
  /// **'Farm address'**
  String get farmAddress;

  /// No description provided for @farmSaved.
  ///
  /// In en, this message translates to:
  /// **'Farm saved.'**
  String get farmSaved;

  /// No description provided for @profileImagePick.
  ///
  /// In en, this message translates to:
  /// **'Choose profile photo'**
  String get profileImagePick;

  /// No description provided for @saveChanges.
  ///
  /// In en, this message translates to:
  /// **'Save changes'**
  String get saveChanges;

  /// No description provided for @notificationPermissionEnabled.
  ///
  /// In en, this message translates to:
  /// **'Notification permission requested and this device was registered.'**
  String get notificationPermissionEnabled;

  /// No description provided for @markRead.
  ///
  /// In en, this message translates to:
  /// **'Mark as read'**
  String get markRead;

  /// No description provided for @aboutTitle.
  ///
  /// In en, this message translates to:
  /// **'Banana Lifeline'**
  String get aboutTitle;

  /// No description provided for @aboutSubtitle.
  ///
  /// In en, this message translates to:
  /// **'AI-assisted banana disease early warning and source-grounded farmer support.'**
  String get aboutSubtitle;

  /// No description provided for @whatAppDoes.
  ///
  /// In en, this message translates to:
  /// **'What this app does'**
  String get whatAppDoes;

  /// No description provided for @scientificScope.
  ///
  /// In en, this message translates to:
  /// **'Scientific scope'**
  String get scientificScope;

  /// No description provided for @scientificScopeBody.
  ///
  /// In en, this message translates to:
  /// **'The supplied classifier is trained on banana leaf images. Panama predictions are screening signals only and should be confirmed using field signs and expert or laboratory review.'**
  String get scientificScopeBody;

  /// No description provided for @privacyTitle.
  ///
  /// In en, this message translates to:
  /// **'Privacy & permissions'**
  String get privacyTitle;

  /// No description provided for @logoutConfirm.
  ///
  /// In en, this message translates to:
  /// **'Log out of Banana Lifeline?'**
  String get logoutConfirm;

  /// No description provided for @yesLogout.
  ///
  /// In en, this message translates to:
  /// **'Log out'**
  String get yesLogout;

  /// No description provided for @latestFirst.
  ///
  /// In en, this message translates to:
  /// **'Latest first'**
  String get latestFirst;

  /// No description provided for @errorTryAgain.
  ///
  /// In en, this message translates to:
  /// **'Something went wrong. Please try again.'**
  String get errorTryAgain;

  /// No description provided for @refresh.
  ///
  /// In en, this message translates to:
  /// **'Refresh'**
  String get refresh;

  /// No description provided for @noInternetAi.
  ///
  /// In en, this message translates to:
  /// **'AI requests need internet. Firebase may still show previously cached scans and chats.'**
  String get noInternetAi;

  /// No description provided for @apiHealth.
  ///
  /// In en, this message translates to:
  /// **'AI service status'**
  String get apiHealth;

  /// No description provided for @checkApi.
  ///
  /// In en, this message translates to:
  /// **'Check AI service'**
  String get checkApi;

  /// No description provided for @visionReady.
  ///
  /// In en, this message translates to:
  /// **'Vision model ready'**
  String get visionReady;

  /// No description provided for @ragReady.
  ///
  /// In en, this message translates to:
  /// **'RAG knowledge ready'**
  String get ragReady;

  /// No description provided for @generationReady.
  ///
  /// In en, this message translates to:
  /// **'Answer generation ready'**
  String get generationReady;

  /// No description provided for @notReady.
  ///
  /// In en, this message translates to:
  /// **'Not ready'**
  String get notReady;

  /// No description provided for @ready.
  ///
  /// In en, this message translates to:
  /// **'Ready'**
  String get ready;

  /// No description provided for @farmRiskHigh.
  ///
  /// In en, this message translates to:
  /// **'A recent high-risk scan needs attention.'**
  String get farmRiskHigh;

  /// No description provided for @farmRiskMedium.
  ///
  /// In en, this message translates to:
  /// **'A recent scan needs review or monitoring.'**
  String get farmRiskMedium;

  /// No description provided for @farmRiskLow.
  ///
  /// In en, this message translates to:
  /// **'No high-risk diagnosis is currently stored.'**
  String get farmRiskLow;

  /// No description provided for @recentCheckCount.
  ///
  /// In en, this message translates to:
  /// **'{count} recent checks'**
  String recentCheckCount(int count);

  /// No description provided for @noProfile.
  ///
  /// In en, this message translates to:
  /// **'Farmer profile not found.'**
  String get noProfile;

  /// No description provided for @created.
  ///
  /// In en, this message translates to:
  /// **'Created'**
  String get created;

  /// No description provided for @openSettings.
  ///
  /// In en, this message translates to:
  /// **'Open settings'**
  String get openSettings;

  /// No description provided for @locationSettingsHelp.
  ///
  /// In en, this message translates to:
  /// **'If permission is permanently denied, enable location from your phone settings.'**
  String get locationSettingsHelp;

  /// No description provided for @healthCheckFailed.
  ///
  /// In en, this message translates to:
  /// **'Could not reach the AI server.'**
  String get healthCheckFailed;

  /// No description provided for @chatSendFailed.
  ///
  /// In en, this message translates to:
  /// **'Your message could not be sent. It remains in the text box so you can retry.'**
  String get chatSendFailed;

  /// No description provided for @audioTranscribing.
  ///
  /// In en, this message translates to:
  /// **'Transcribing voice note...'**
  String get audioTranscribing;

  /// No description provided for @uploading.
  ///
  /// In en, this message translates to:
  /// **'Uploading...'**
  String get uploading;

  /// No description provided for @processingImage.
  ///
  /// In en, this message translates to:
  /// **'Analyzing your banana leaf...'**
  String get processingImage;

  /// No description provided for @viewDetails.
  ///
  /// In en, this message translates to:
  /// **'View details'**
  String get viewDetails;

  /// No description provided for @sourcePage.
  ///
  /// In en, this message translates to:
  /// **'Page {page}'**
  String sourcePage(int page);

  /// No description provided for @chatImageLeafOnly.
  ///
  /// In en, this message translates to:
  /// **'The current vision classifier accepts banana leaf images only.'**
  String get chatImageLeafOnly;

  /// No description provided for @deleteFarm.
  ///
  /// In en, this message translates to:
  /// **'Delete farm'**
  String get deleteFarm;

  /// No description provided for @farmNameRequired.
  ///
  /// In en, this message translates to:
  /// **'Farm name is required.'**
  String get farmNameRequired;

  /// No description provided for @permissions.
  ///
  /// In en, this message translates to:
  /// **'Permissions'**
  String get permissions;

  /// No description provided for @notificationPermission.
  ///
  /// In en, this message translates to:
  /// **'Notification permission'**
  String get notificationPermission;

  /// No description provided for @cameraPermission.
  ///
  /// In en, this message translates to:
  /// **'Camera permission'**
  String get cameraPermission;

  /// No description provided for @microphonePermission.
  ///
  /// In en, this message translates to:
  /// **'Microphone permission'**
  String get microphonePermission;

  /// No description provided for @locationPermissionInfo.
  ///
  /// In en, this message translates to:
  /// **'Location is used only when you choose to attach a farm place to a scan or chat question.'**
  String get locationPermissionInfo;

  /// No description provided for @edit.
  ///
  /// In en, this message translates to:
  /// **'Edit'**
  String get edit;

  /// No description provided for @add.
  ///
  /// In en, this message translates to:
  /// **'Add'**
  String get add;

  /// No description provided for @done.
  ///
  /// In en, this message translates to:
  /// **'Done'**
  String get done;

  /// No description provided for @back.
  ///
  /// In en, this message translates to:
  /// **'Back'**
  String get back;

  /// No description provided for @next.
  ///
  /// In en, this message translates to:
  /// **'Next'**
  String get next;

  /// No description provided for @viewOnMap.
  ///
  /// In en, this message translates to:
  /// **'Map coordinates'**
  String get viewOnMap;

  /// No description provided for @serviceUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Service unavailable'**
  String get serviceUnavailable;

  /// No description provided for @relatedScan.
  ///
  /// In en, this message translates to:
  /// **'Related scan'**
  String get relatedScan;

  /// No description provided for @conversationSources.
  ///
  /// In en, this message translates to:
  /// **'Sources used for this answer'**
  String get conversationSources;

  /// No description provided for @emptyNote.
  ///
  /// In en, this message translates to:
  /// **'No note added'**
  String get emptyNote;

  /// No description provided for @profileEmail.
  ///
  /// In en, this message translates to:
  /// **'Account email'**
  String get profileEmail;

  /// No description provided for @farmSizeHint.
  ///
  /// In en, this message translates to:
  /// **'e.g. 5 acres'**
  String get farmSizeHint;

  /// No description provided for @cropInfoHint.
  ///
  /// In en, this message translates to:
  /// **'e.g. Banana, Cavendish'**
  String get cropInfoHint;

  /// No description provided for @districtHint.
  ///
  /// In en, this message translates to:
  /// **'e.g. Tando Allahyar'**
  String get districtHint;

  /// No description provided for @provinceHint.
  ///
  /// In en, this message translates to:
  /// **'e.g. Sindh'**
  String get provinceHint;

  /// No description provided for @processingWarning.
  ///
  /// In en, this message translates to:
  /// **'Keep this screen open while the image uploads and the AI service responds.'**
  String get processingWarning;

  /// No description provided for @notificationInfo.
  ///
  /// In en, this message translates to:
  /// **'Notifications are created only from real backend events such as a completed high-risk diagnosis.'**
  String get notificationInfo;

  /// No description provided for @authInvalidEmail.
  ///
  /// In en, this message translates to:
  /// **'Please enter a valid email address.'**
  String get authInvalidEmail;

  /// No description provided for @authWrongCredentials.
  ///
  /// In en, this message translates to:
  /// **'Email or password is incorrect.'**
  String get authWrongCredentials;

  /// No description provided for @authEmailInUse.
  ///
  /// In en, this message translates to:
  /// **'An account already exists with this email.'**
  String get authEmailInUse;

  /// No description provided for @authWeakPassword.
  ///
  /// In en, this message translates to:
  /// **'Please use a stronger password.'**
  String get authWeakPassword;

  /// No description provided for @authTooMany.
  ///
  /// In en, this message translates to:
  /// **'Too many attempts. Please try again later.'**
  String get authTooMany;

  /// No description provided for @authGeneric.
  ///
  /// In en, this message translates to:
  /// **'Authentication could not be completed. Please try again.'**
  String get authGeneric;

  /// No description provided for @farmerFallback.
  ///
  /// In en, this message translates to:
  /// **'Farmer'**
  String get farmerFallback;

  /// No description provided for @diagnosisStatusProcessing.
  ///
  /// In en, this message translates to:
  /// **'Processing'**
  String get diagnosisStatusProcessing;

  /// No description provided for @diagnosisStatusFailed.
  ///
  /// In en, this message translates to:
  /// **'Failed'**
  String get diagnosisStatusFailed;

  /// No description provided for @diagnosisStatusCompleted.
  ///
  /// In en, this message translates to:
  /// **'Completed'**
  String get diagnosisStatusCompleted;

  /// No description provided for @diagnosisStatusPending.
  ///
  /// In en, this message translates to:
  /// **'Pending'**
  String get diagnosisStatusPending;

  /// No description provided for @severityUnknown.
  ///
  /// In en, this message translates to:
  /// **'Unknown'**
  String get severityUnknown;

  /// No description provided for @retryDiagnosis.
  ///
  /// In en, this message translates to:
  /// **'Retry diagnosis'**
  String get retryDiagnosis;

  /// No description provided for @retryingDiagnosis.
  ///
  /// In en, this message translates to:
  /// **'Retrying diagnosis...'**
  String get retryingDiagnosis;

  /// No description provided for @retryStarted.
  ///
  /// In en, this message translates to:
  /// **'Diagnosis retry started.'**
  String get retryStarted;

  /// No description provided for @retryFailed.
  ///
  /// In en, this message translates to:
  /// **'Could not retry diagnosis. Please check the AI service and internet connection.'**
  String get retryFailed;

  /// No description provided for @manualFarmPlace.
  ///
  /// In en, this message translates to:
  /// **'Manual farm place'**
  String get manualFarmPlace;

  /// No description provided for @imageLocation.
  ///
  /// In en, this message translates to:
  /// **'Image location'**
  String get imageLocation;

  /// No description provided for @realServiceOnly.
  ///
  /// In en, this message translates to:
  /// **'Real service only'**
  String get realServiceOnly;

  /// No description provided for @scanAgain.
  ///
  /// In en, this message translates to:
  /// **'Start a new scan'**
  String get scanAgain;

  /// No description provided for @savedOfflineTitle.
  ///
  /// In en, this message translates to:
  /// **'Saved on this phone'**
  String get savedOfflineTitle;

  /// No description provided for @savedOfflineBody.
  ///
  /// In en, this message translates to:
  /// **'The upload could not be completed. Your photo, farm place and note were saved locally so you can retry without losing them.'**
  String get savedOfflineBody;

  /// No description provided for @pendingUploads.
  ///
  /// In en, this message translates to:
  /// **'Pending uploads'**
  String get pendingUploads;

  /// No description provided for @pendingUploadsHelp.
  ///
  /// In en, this message translates to:
  /// **'These real scan drafts are stored on this device until Firebase upload succeeds.'**
  String get pendingUploadsHelp;

  /// No description provided for @retryUpload.
  ///
  /// In en, this message translates to:
  /// **'Retry upload'**
  String get retryUpload;

  /// No description provided for @removePending.
  ///
  /// In en, this message translates to:
  /// **'Remove'**
  String get removePending;

  /// No description provided for @pendingUploadRetrying.
  ///
  /// In en, this message translates to:
  /// **'Retrying upload…'**
  String get pendingUploadRetrying;

  /// No description provided for @pendingUploadSuccess.
  ///
  /// In en, this message translates to:
  /// **'Upload completed. The scan is now in your Firebase history.'**
  String get pendingUploadSuccess;

  /// No description provided for @pendingUploadFailed.
  ///
  /// In en, this message translates to:
  /// **'Upload still could not be completed. The draft remains safely on this phone.'**
  String get pendingUploadFailed;

  /// No description provided for @noPendingUploads.
  ///
  /// In en, this message translates to:
  /// **'No pending uploads.'**
  String get noPendingUploads;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'ur'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'ur':
      return AppLocalizationsUr();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
