import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/firebase/providers.dart';
import '../../core/models/models.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/app_localizations.dart';
import '../../shared/widgets/app_async.dart';
import '../../shared/widgets/brand_mark.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  bool _registeredNotifications = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_registeredNotifications) {
      _registeredNotifications = true;
      Future<void>.microtask(() async {
        try {
          await ref.read(notificationRepositoryProvider).registerDevice();
        } catch (_) {
          // Notification permission/token failure must not block the dashboard.
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final profile = ref.watch(farmerProfileProvider);
    final scans = ref.watch(scansProvider);

    return SafeArea(
      child: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(farmerProfileProvider);
          ref.invalidate(scansProvider);
        },
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 18, 20, 110),
          children: [
            Row(
              children: [
                const Expanded(child: BrandMark(compact: true)),
                IconButton.filledTonal(
                  onPressed: () => context.push('/notifications'),
                  icon: const Icon(Icons.notifications_none_rounded),
                ),
              ],
            ),
            const SizedBox(height: 24),
            profile.when(
              data: (value) => Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l.goodMorning(value?.fullName.isNotEmpty == true ? value!.fullName : l.farmerFallback),
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const SizedBox(height: 6),
                  Text(l.dashboardSubtitle, style: const TextStyle(color: AppColors.muted)),
                ],
              ),
              loading: () => const LinearProgressIndicator(minHeight: 2),
              error: (_, _) => Text(l.dashboardSubtitle),
            ),
            const SizedBox(height: 20),
            scans.when(
              data: (items) => _RiskCard(scans: items),
              loading: () => const Card(child: Padding(padding: EdgeInsets.all(28), child: AppLoading())),
              error: (_, _) => AppErrorCard(message: l.noScansSubtitle),
            ),
            const SizedBox(height: 16),
            InkWell(
              borderRadius: BorderRadius.circular(26),
              onTap: () => context.go('/scan'),
              child: Ink(
                padding: const EdgeInsets.all(22),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [AppColors.leaf, AppColors.forest],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(26),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 62,
                      height: 62,
                      decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle),
                      child: const Icon(Icons.camera_alt_rounded, color: AppColors.forest, size: 30),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(l.scanNow, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 21)),
                          const SizedBox(height: 4),
                          Text(l.scanNowSubtitle, style: const TextStyle(color: Colors.white70, height: 1.35)),
                        ],
                      ),
                    ),
                    const Icon(Icons.arrow_forward_ios_rounded, color: AppColors.banana, size: 18),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: _QuickAction(
                    icon: Icons.support_agent_rounded,
                    title: l.askExpert,
                    onTap: () => context.go('/chat'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _QuickAction(
                    icon: Icons.history_rounded,
                    title: l.scanHistory,
                    onTap: () => context.go('/history'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 22),
            Row(
              children: [
                Text(l.recentChecks, style: Theme.of(context).textTheme.titleLarge),
                const Spacer(),
                TextButton(onPressed: () => context.go('/history'), child: Text(l.seeAll)),
              ],
            ),
            const SizedBox(height: 8),
            scans.when(
              data: (items) {
                if (items.isEmpty) {
                  return Card(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        children: [
                          const Icon(Icons.eco_outlined, color: AppColors.forest, size: 36),
                          const SizedBox(height: 8),
                          Text(l.noScans, style: const TextStyle(fontWeight: FontWeight.w900)),
                          const SizedBox(height: 4),
                          Text(l.noScansSubtitle, textAlign: TextAlign.center),
                        ],
                      ),
                    ),
                  );
                }
                return Column(
                  children: items.take(4).map((scan) => Padding(
                    padding: const EdgeInsets.only(bottom: 9),
                    child: _ScanTile(scan: scan),
                  )).toList(),
                );
              },
              loading: () => const SizedBox.shrink(),
              error: (_, _) => const SizedBox.shrink(),
            ),
          ],
        ),
      ),
    );
  }
}

class _RiskCard extends StatelessWidget {
  const _RiskCard({required this.scans});
  final List<PlantScan> scans;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final hasHigh = scans.any((s) => s.diagnosis?.severity == 'high');
    final hasMedium = scans.any((s) => s.diagnosis?.severity == 'medium');
    final level = hasHigh
        ? l.high
        : hasMedium
            ? l.medium
            : l.low;
    final color = hasHigh ? AppColors.danger : hasMedium ? AppColors.warning : AppColors.leaf;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          children: [
            SizedBox(
              width: 88,
              height: 88,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  CircularProgressIndicator(
                    value: hasHigh ? .88 : hasMedium ? .58 : .28,
                    strokeWidth: 9,
                    color: color,
                    backgroundColor: AppColors.border,
                  ),
                  Center(
                    child: Text(level, style: TextStyle(color: color, fontWeight: FontWeight.w900, fontSize: 17)),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 18),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [const Icon(Icons.health_and_safety_outlined, color: AppColors.forest), const SizedBox(width: 7), Text(l.farmRisk, style: const TextStyle(fontWeight: FontWeight.w900))]),
                  const SizedBox(height: 8),
                  Text(
                    scans.isEmpty
                        ? l.farmRiskEmpty
                        : l.recentCheckCount(scans.length),
                    style: const TextStyle(color: AppColors.muted),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _QuickAction extends StatelessWidget {
  const _QuickAction({required this.icon, required this.title, required this.onTap});
  final IconData icon;
  final String title;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(22),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 18),
          child: Column(
            children: [
              Icon(icon, color: AppColors.forest),
              const SizedBox(height: 7),
              Text(title, textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12)),
            ],
          ),
        ),
      ),
    );
  }
}

class _ScanTile extends StatelessWidget {
  const _ScanTile({required this.scan});
  final PlantScan scan;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final diagnosis = scan.diagnosis;
    final title = diagnosis?.displayName ?? _statusLabel(l, scan.status);
    final severity = diagnosis?.severity ?? 'unknown';
    final color = severity == 'high'
        ? AppColors.danger
        : severity == 'medium'
            ? AppColors.warning
            : AppColors.leaf;

    return Card(
      child: ListTile(
        onTap: () => context.push('/diagnosis/${scan.id}'),
        leading: ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: scan.imageUrl.isEmpty
              ? Container(
                  width: 54,
                  height: 54,
                  color: AppColors.leafSoft,
                  child: const Icon(Icons.eco_rounded),
                )
              : Image.network(
                  scan.imageUrl,
                  width: 54,
                  height: 54,
                  fit: BoxFit.cover,
                  errorBuilder: (_, _, _) => Container(
                    width: 54,
                    height: 54,
                    color: AppColors.leafSoft,
                    child: const Icon(Icons.eco_rounded),
                  ),
                ),
        ),
        title: Text(
          title,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(
            fontWeight: FontWeight.w800,
            fontSize: 13,
          ),
        ),
        subtitle: Text(
          scan.location.placeLabel.isEmpty
              ? (scan.location.address ?? l.manualFarmPlace)
              : scan.location.placeLabel,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
          decoration: BoxDecoration(
            color: color.withValues(alpha: .10),
            borderRadius: BorderRadius.circular(99),
          ),
          child: Text(
            _severityLabel(l, severity),
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.w900,
              fontSize: 10,
            ),
          ),
        ),
      ),
    );
  }

  String _severityLabel(AppLocalizations l, String value) => switch (value) {
        'high' => l.high,
        'medium' => l.medium,
        'low' => l.low,
        _ => l.severityUnknown,
      };

  String _statusLabel(AppLocalizations l, String value) => switch (value) {
        'processing' => l.diagnosisStatusProcessing,
        'failed' => l.diagnosisStatusFailed,
        'completed' => l.diagnosisStatusCompleted,
        'pending' => l.diagnosisStatusPending,
        _ => l.unknown,
      };
}
