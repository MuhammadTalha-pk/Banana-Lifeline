import 'dart:async';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/firebase/providers.dart';
import '../features/about/about_screen.dart';
import '../features/auth/auth_screens.dart';
import '../features/chat/chat_screen.dart';
import '../features/chat/chat_sessions_screen.dart';
import '../features/history/history_screen.dart';
import '../features/home/home_screen.dart';
import '../features/notifications/notifications_screen.dart';
import '../features/profile/profile_screens.dart';
import '../features/scan/scan_screens.dart';
import '../features/settings/settings_screen.dart';
import 'shell.dart';

class AuthRefresh extends ChangeNotifier {
  AuthRefresh(Stream<User?> stream) {
    _subscription = stream.listen((_) => notifyListeners());
  }
  late final StreamSubscription<User?> _subscription;
  @override
  void dispose() {
    _subscription.cancel();
    super.dispose();
  }
}

final routerProvider = Provider<GoRouter>((ref) {
  final auth = ref.watch(firebaseAuthProvider);
  final refresh = AuthRefresh(auth.authStateChanges());
  ref.onDispose(refresh.dispose);

  return GoRouter(
    initialLocation: '/onboarding',
    refreshListenable: refresh,
    redirect: (context, state) {
      final loggedIn = auth.currentUser != null;
      final path = state.uri.path;
      final public = path == '/onboarding' ||
          path == '/login' ||
          path == '/register' ||
          path == '/forgot';
      if (!loggedIn && !public) return '/login';
      if (loggedIn && public) return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/onboarding', builder: (_, _) => const OnboardingScreen()),
      GoRoute(path: '/login', builder: (_, _) => const LoginScreen()),
      GoRoute(path: '/register', builder: (_, _) => const RegisterScreen()),
      GoRoute(path: '/forgot', builder: (_, _) => const ForgotPasswordScreen()),
      ShellRoute(
        builder: (context, state, child) => AppShell(child: child),
        routes: [
          GoRoute(path: '/home', builder: (_, _) => const HomeScreen()),
          GoRoute(path: '/scan', builder: (_, _) => const ScanScreen()),
          GoRoute(path: '/chat', builder: (_, _) => const ChatSessionsScreen()),
          GoRoute(path: '/history', builder: (_, _) => const HistoryScreen()),
          GoRoute(path: '/profile', builder: (_, _) => const ProfileScreen()),
        ],
      ),
      GoRoute(
        path: '/scan/preview',
        builder: (_, state) => ScanPreviewScreen(draft: state.extra! as ScanDraft),
      ),
      GoRoute(
        path: '/diagnosis/:id',
        builder: (_, state) => DiagnosisDetailScreen(scanId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/chat/session/:id',
        builder: (_, state) => ChatScreen(sessionId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/chat/new',
        builder: (_, state) => ChatScreen(relatedScanId: state.uri.queryParameters['scan']),
      ),
      GoRoute(path: '/profile/edit', builder: (_, _) => const EditProfileScreen()),
      GoRoute(path: '/settings', builder: (_, _) => const SettingsScreen()),
      GoRoute(path: '/notifications', builder: (_, _) => const NotificationsScreen()),
      GoRoute(path: '/about', builder: (_, _) => const AboutScreen()),
    ],
  );
});
