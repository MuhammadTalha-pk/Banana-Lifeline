import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/firebase/providers.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/app_localizations.dart';
import '../../shared/widgets/brand_mark.dart';

class OnboardingScreen extends ConsumerWidget {
  const OnboardingScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Container(
                    width: 110,
                    height: 110,
                    decoration: BoxDecoration(
                      color: AppColors.leafSoft,
                      borderRadius: BorderRadius.circular(32),
                    ),
                    child: const Icon(Icons.eco_rounded, size: 58, color: AppColors.forest),
                  ),
                  const SizedBox(height: 24),
                  Text(l.appName, style: Theme.of(context).textTheme.headlineLarge),
                  const SizedBox(height: 10),
                  Text(l.tagline, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.muted, fontSize: 16)),
                  const SizedBox(height: 30),
                  SegmentedButton<String>(
                    segments: [
                      ButtonSegment(value: 'en', label: Text(l.english)),
                      ButtonSegment(value: 'ur', label: Text(l.urdu)),
                    ],
                    selected: {Localizations.localeOf(context).languageCode},
                    onSelectionChanged: (value) {
                      ref.read(localeControllerProvider.notifier).setLanguage(value.first);
                    },
                  ),
                  const SizedBox(height: 26),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      onPressed: () => context.go('/login'),
                      child: Text(l.getStarted),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(l.productCapabilities, style: const TextStyle(color: AppColors.muted, fontSize: 11)),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});
  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _loading = false;
  bool _obscure = true;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _loading = true);
    try {
      await ref.read(authRepositoryProvider).login(_email.text, _password.text);
    } on FirebaseAuthException catch (e) {
      if (mounted) _show(_authMessage(context, e));
    } catch (_) {
      if (mounted) _show(AppLocalizations.of(context).signInFailed);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _show(String text) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return _AuthFrame(
      title: l.welcomeBack,
      subtitle: l.authSubtitle,
      child: Column(
        children: [
          TextField(controller: _email, keyboardType: TextInputType.emailAddress, decoration: InputDecoration(labelText: l.email, prefixIcon: const Icon(Icons.email_outlined))),
          const SizedBox(height: 12),
          TextField(
            controller: _password,
            obscureText: _obscure,
            onSubmitted: (_) => _submit(),
            decoration: InputDecoration(
              labelText: l.password,
              prefixIcon: const Icon(Icons.lock_outline),
              suffixIcon: IconButton(onPressed: () => setState(() => _obscure = !_obscure), icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined)),
            ),
          ),
          Align(alignment: AlignmentDirectional.centerEnd, child: TextButton(onPressed: () => context.push('/forgot'), child: Text(l.forgotPassword))),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _loading ? null : _submit,
              child: _loading ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : Text(l.login),
            ),
          ),
          const SizedBox(height: 14),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(l.noAccount),
              TextButton(onPressed: () => context.push('/register'), child: Text(l.register)),
            ],
          ),
        ],
      ),
    );
  }
}

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});
  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  bool _loading = false;

  @override
  void dispose() {
    for (final c in [_name, _phone, _email, _password, _confirm]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    if (_password.text != _confirm.text) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppLocalizations.of(context).passwordMismatch)));
      return;
    }
    setState(() => _loading = true);
    try {
      await ref.read(authRepositoryProvider).register(
            email: _email.text,
            password: _password.text,
            fullName: _name.text,
            phone: _phone.text,
            language: Localizations.localeOf(context).languageCode,
          );
      await ref.read(notificationRepositoryProvider).registerDevice();
    } on FirebaseAuthException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_authMessage(context, e))));
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppLocalizations.of(context).registerFailed)));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return _AuthFrame(
      title: l.createFarmerProfile,
      subtitle: l.tagline,
      child: Column(
        children: [
          TextField(controller: _name, decoration: InputDecoration(labelText: l.fullName, prefixIcon: const Icon(Icons.person_outline))),
          const SizedBox(height: 10),
          TextField(controller: _phone, keyboardType: TextInputType.phone, decoration: InputDecoration(labelText: l.phone, prefixIcon: const Icon(Icons.phone_outlined))),
          const SizedBox(height: 10),
          TextField(controller: _email, keyboardType: TextInputType.emailAddress, decoration: InputDecoration(labelText: l.email, prefixIcon: const Icon(Icons.email_outlined))),
          const SizedBox(height: 10),
          TextField(controller: _password, obscureText: true, decoration: InputDecoration(labelText: l.password, prefixIcon: const Icon(Icons.lock_outline))),
          const SizedBox(height: 10),
          TextField(controller: _confirm, obscureText: true, decoration: InputDecoration(labelText: l.confirmPassword, prefixIcon: const Icon(Icons.lock_reset_outlined))),
          const SizedBox(height: 18),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _loading ? null : _submit,
              child: _loading ? const CircularProgressIndicator(color: Colors.white) : Text(l.register),
            ),
          ),
          const SizedBox(height: 10),
          TextButton(onPressed: () => context.pop(), child: Text(l.haveAccount)),
        ],
      ),
    );
  }
}

class ForgotPasswordScreen extends ConsumerStatefulWidget {
  const ForgotPasswordScreen({super.key});
  @override
  ConsumerState<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends ConsumerState<ForgotPasswordScreen> {
  final _email = TextEditingController();
  bool _loading = false;

  @override
  void dispose() {
    _email.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _loading = true);
    try {
      await ref.read(authRepositoryProvider).sendPasswordReset(_email.text);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(AppLocalizations.of(context).resetEmailSent)));
    } on FirebaseAuthException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(_authMessage(context, e))));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return _AuthFrame(
      title: l.resetPassword,
      subtitle: l.email,
      child: Column(
        children: [
          TextField(controller: _email, keyboardType: TextInputType.emailAddress, decoration: InputDecoration(labelText: l.email, prefixIcon: const Icon(Icons.email_outlined))),
          const SizedBox(height: 16),
          SizedBox(width: double.infinity, child: FilledButton(onPressed: _loading ? null : _submit, child: Text(l.resetPassword))),
        ],
      ),
    );
  }
}

class _AuthFrame extends StatelessWidget {
  const _AuthFrame({required this.title, required this.subtitle, required this.child});
  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(22),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 480),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const BrandMark(),
                  const SizedBox(height: 30),
                  Text(title, style: Theme.of(context).textTheme.headlineMedium),
                  const SizedBox(height: 6),
                  Text(subtitle, style: const TextStyle(color: AppColors.muted)),
                  const SizedBox(height: 22),
                  Card(child: Padding(padding: const EdgeInsets.all(18), child: child)),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

String _authMessage(BuildContext context, FirebaseAuthException error) {
  final l = AppLocalizations.of(context);
  return switch (error.code) {
    'invalid-email' => l.authInvalidEmail,
    'invalid-credential' || 'wrong-password' || 'user-not-found' => l.authWrongCredentials,
    'email-already-in-use' => l.authEmailInUse,
    'weak-password' => l.authWeakPassword,
    'too-many-requests' => l.authTooMany,
    _ => l.authGeneric,
  };
}
