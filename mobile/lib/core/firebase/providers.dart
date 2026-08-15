import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/auth/auth_repository.dart';
import '../../features/chat/chat_repository.dart';
import '../../features/notifications/notification_repository.dart';
import '../../features/profile/profile_repository.dart';
import '../../features/scan/scan_repository.dart';
import '../network/api_client.dart';
import '../services/location_service.dart';
import '../services/pending_scan_service.dart';
import '../services/speech_services.dart';

final firebaseAuthProvider =
    Provider<FirebaseAuth>((ref) => FirebaseAuth.instance);
final firestoreProvider =
    Provider<FirebaseFirestore>((ref) => FirebaseFirestore.instance);
final firebaseMessagingProvider =
    Provider<FirebaseMessaging>((ref) => FirebaseMessaging.instance);

final apiClientProvider = Provider<ApiClient>(
  (ref) => ApiClient(ref.watch(firebaseAuthProvider)),
);
final locationServiceProvider =
    Provider<LocationService>((ref) => LocationService());
final pendingScanServiceProvider =
    Provider<PendingScanService>((ref) => PendingScanService());
final liveSpeechProvider =
    Provider<LiveSpeechService>((ref) => LiveSpeechService());
final ttsProvider = Provider<TtsService>((ref) => TtsService());

final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => AuthRepository(
    ref.watch(firebaseAuthProvider),
    ref.watch(firestoreProvider),
  ),
);

final profileRepositoryProvider = Provider<ProfileRepository>(
  (ref) => ProfileRepository(
    ref.watch(firestoreProvider),
    ref.watch(firebaseAuthProvider),
    ref.watch(apiClientProvider),
  ),
);

final scanRepositoryProvider = Provider<ScanRepository>(
  (ref) => ScanRepository(
    ref.watch(firestoreProvider),
    ref.watch(firebaseAuthProvider),
    ref.watch(apiClientProvider),
  ),
);

final chatRepositoryProvider = Provider<ChatRepository>(
  (ref) => ChatRepository(
    ref.watch(firestoreProvider),
    ref.watch(firebaseAuthProvider),
    ref.watch(apiClientProvider),
  ),
);

final notificationRepositoryProvider = Provider<NotificationRepository>(
  (ref) => NotificationRepository(
    ref.watch(firestoreProvider),
    ref.watch(firebaseAuthProvider),
    ref.watch(firebaseMessagingProvider),
  ),
);

final authStateProvider = StreamProvider<User?>(
  (ref) => ref.watch(authRepositoryProvider).authChanges(),
);
final farmerProfileProvider = StreamProvider(
  (ref) => ref.watch(profileRepositoryProvider).watchProfile(),
);
final farmsProvider = StreamProvider(
  (ref) => ref.watch(profileRepositoryProvider).watchFarms(),
);
final scansProvider = StreamProvider(
  (ref) => ref.watch(scanRepositoryProvider).watchScans(),
);
final chatSessionsProvider = StreamProvider(
  (ref) => ref.watch(chatRepositoryProvider).watchSessions(),
);
final chatMessagesProvider = StreamProvider.family(
  (ref, String sessionId) =>
      ref.watch(chatRepositoryProvider).watchMessages(sessionId),
);
final notificationsProvider = StreamProvider(
  (ref) => ref.watch(notificationRepositoryProvider).watchNotifications(),
);

class LocaleController extends Notifier<Locale?> {
  @override
  Locale? build() => null;

  void setLanguage(String code) => state = Locale(code);
}

final localeControllerProvider =
    NotifierProvider<LocaleController, Locale?>(LocaleController.new);
