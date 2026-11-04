import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:go_router/go_router.dart';

import '../../core/firebase/providers.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/app_localizations.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  bool _checkingApi = false;
  Map<String, dynamic>? _health;

  Future<void> _setLanguage(String code) async {
    ref.read(localeControllerProvider.notifier).setLanguage(code);
    try {
      await ref.read(profileRepositoryProvider).setPreferredLanguage(code);
    } catch (_) {
      // Locale can still change locally; Firestore sync can be retried later.
    }
  }

  Future<void> _registerNotifications() async {
    final l = AppLocalizations.of(context);
    try {
      await ref.read(notificationRepositoryProvider).registerDevice();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l.notificationPermissionEnabled)),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l.errorTryAgain)),
      );
    }
  }

  Future<void> _locationPermission() async {
    final l = AppLocalizations.of(context);
    try {
      await ref.read(locationServiceProvider).current();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l.locationCaptured)),
      );
    } catch (_) {
      if (!mounted) return;
      final open = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(l.locationPermission),
          content: Text('${l.locationPermissionDenied}\n\n${l.locationSettingsHelp}'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: Text(l.cancel)),
            FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(l.openSettings)),
          ],
        ),
      );
      if (open == true) await Geolocator.openAppSettings();
    }
  }

  Future<void> _checkApi() async {
    final l = AppLocalizations.of(context);
    setState(() => _checkingApi = true);
    try {
      final health = await ref.read(apiClientProvider).health();
      if (!mounted) return;
      setState(() => _health = health);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l.healthCheckFailed)),
      );
    } finally {
      if (mounted) setState(() => _checkingApi = false);
    }
  }

  Future<void> _logout() async {
    final l = AppLocalizations.of(context);
    final yes = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l.logout),
        content: Text(l.logoutConfirm),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text(l.cancel)),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(l.yesLogout)),
        ],
      ),
    );
    if (yes == true) await ref.read(authRepositoryProvider).logout();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    return Scaffold(
      appBar: AppBar(title: Text(l.settings, style: const TextStyle(fontWeight: FontWeight.w900))),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 36),
          children: [
            Text(l.language, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: SegmentedButton<String>(
                  segments: [
                    ButtonSegment(value: 'en', label: Text(l.english)),
                    ButtonSegment(value: 'ur', label: Text(l.urdu)),
                  ],
                  selected: {lang},
                  onSelectionChanged: (value) => _setLanguage(value.first),
                ),
              ),
            ),
            const SizedBox(height: 18),
            Text(l.permissions, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Card(
              child: Column(
                children: [
                  ListTile(
                    leading: const Icon(Icons.notifications_active_outlined, color: AppColors.forest),
                    title: Text(l.notificationPermission, style: const TextStyle(fontWeight: FontWeight.w800)),
                    subtitle: Text(l.notificationInfo, style: const TextStyle(fontSize: 10)),
                    trailing: const Icon(Icons.chevron_right_rounded),
                    onTap: _registerNotifications,
                  ),
                  const Divider(height: 1),
                  ListTile(
                    leading: const Icon(Icons.location_on_outlined, color: AppColors.forest),
                    title: Text(l.locationPermission, style: const TextStyle(fontWeight: FontWeight.w800)),
                    subtitle: Text(l.locationPermissionInfo, style: const TextStyle(fontSize: 10)),
                    trailing: const Icon(Icons.chevron_right_rounded),
                    onTap: _locationPermission,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            Text(l.apiHealth, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton.icon(
                        onPressed: _checkingApi ? null : _checkApi,
                        icon: _checkingApi
                            ? const SizedBox(width: 17, height: 17, child: CircularProgressIndicator(strokeWidth: 2))
                            : const Icon(Icons.monitor_heart_outlined),
                        label: Text(l.checkApi),
                      ),
                    ),
                    if (_health != null) ...[
                      const SizedBox(height: 10),
                      _ReadyRow(label: l.visionReady, ready: _health!['vision_ready'] == true),
                      _ReadyRow(label: l.ragReady, ready: _health!['rag_ready'] == true),
                      _ReadyRow(label: l.generationReady, ready: _health!['generation_ready'] == true),
                    ],
                  ],
                ),
              ),
            ),
            const SizedBox(height: 18),
            Card(
              child: Column(
                children: [
                  ListTile(
                    leading: const Icon(Icons.person_outline, color: AppColors.forest),
                    title: Text(l.editProfile, style: const TextStyle(fontWeight: FontWeight.w800)),
                    trailing: const Icon(Icons.chevron_right_rounded),
                    onTap: () => context.push('/profile/edit'),
                  ),
                  const Divider(height: 1),
                  ListTile(
                    leading: const Icon(Icons.notifications_none_rounded, color: AppColors.forest),
                    title: Text(l.notifications, style: const TextStyle(fontWeight: FontWeight.w800)),
                    trailing: const Icon(Icons.chevron_right_rounded),
                    onTap: () => context.push('/notifications'),
                  ),
                  const Divider(height: 1),
                  ListTile(
                    leading: const Icon(Icons.info_outline_rounded, color: AppColors.forest),
                    title: Text(l.aboutHelp, style: const TextStyle(fontWeight: FontWeight.w800)),
                    trailing: const Icon(Icons.chevron_right_rounded),
                    onTap: () => context.push('/about'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            OutlinedButton.icon(
              onPressed: _logout,
              icon: const Icon(Icons.logout_rounded),
              label: Text(l.logout),
            ),
          ],
        ),
      ),
    );
  }
}

class _ReadyRow extends StatelessWidget {
  const _ReadyRow({required this.label, required this.ready});
  final String label;
  final bool ready;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final color = ready ? AppColors.leaf : AppColors.warning;
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          Icon(ready ? Icons.check_circle_rounded : Icons.warning_amber_rounded, color: color, size: 18),
          const SizedBox(width: 7),
          Expanded(child: Text(label, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700))),
          Text(ready ? l.ready : l.notReady, style: TextStyle(color: color, fontWeight: FontWeight.w900, fontSize: 10)),
        ],
      ),
    );
  }
}
