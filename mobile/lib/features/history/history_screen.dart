import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/firebase/providers.dart';
import '../../core/models/models.dart';
import '../../core/services/pending_scan_service.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/app_localizations.dart';
import '../../shared/widgets/app_async.dart';

class HistoryScreen extends ConsumerStatefulWidget {
  const HistoryScreen({super.key});
  @override
  ConsumerState<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends ConsumerState<HistoryScreen> {
  String _filter = 'all';
  Future<List<PendingScan>>? _pendingFuture;

  void _refreshPending() {
    setState(() {
      _pendingFuture = ref.read(pendingScanServiceProvider).load();
    });
  }

  Future<void> _retryPending(PendingScan item) async {
    final l = AppLocalizations.of(context);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(l.pendingUploadRetrying)),
    );
    try {
      final scanId = await ref.read(scanRepositoryProvider).submit(
            image: File(item.imagePath),
            location: item.location,
            note: item.note,
            language: item.language,
          );
      await ref.read(pendingScanServiceProvider).remove(item.id);
      if (!mounted) return;
      _refreshPending();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l.pendingUploadSuccess)),
      );
      context.push('/diagnosis/$scanId');
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l.pendingUploadFailed)),
      );
      _refreshPending();
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final scans = ref.watch(scansProvider);
    return SafeArea(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 110),
        children: [
          Text(l.scanHistory, style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 6),
          Text(l.farmPlace, style: const TextStyle(color: AppColors.muted)),
          const SizedBox(height: 14),
          FutureBuilder<List<PendingScan>>(
            future: _pendingFuture ??= ref.read(pendingScanServiceProvider).load(),
            builder: (context, snapshot) {
              final items = snapshot.data ?? const <PendingScan>[];
              if (items.isEmpty) return const SizedBox.shrink();
              return Padding(
                padding: const EdgeInsets.only(bottom: 18),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.cloud_upload_outlined, color: AppColors.warning),
                        const SizedBox(width: 8),
                        Text(l.pendingUploads, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(l.pendingUploadsHelp, style: const TextStyle(color: AppColors.muted, fontSize: 10.5)),
                    const SizedBox(height: 9),
                    ...items.map(
                      (item) => Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: _PendingTile(
                          item: item,
                          onRetry: () => _retryPending(item),
                          onRemove: () async {
                            await ref.read(pendingScanServiceProvider).remove(item.id);
                            if (mounted) _refreshPending();
                          },
                        ),
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _chip('all', l.all),
              _chip('healthy', l.healthy),
              _chip('disease', l.diseaseDetected),
              _chip('severe', l.severe),
              _chip('latest', l.latest),
            ],
          ),
          const SizedBox(height: 18),
          scans.when(
            loading: () => const AppLoading(),
            error: (_, _) => AppErrorCard(message: l.diagnosisFailed),
            data: (items) {
              final filtered = items.where(_matches).toList();
              if (filtered.isEmpty) return AppErrorCard(message: l.noHistoryMatch);
              return Column(
                children: filtered.map((scan) => Padding(
                  padding: const EdgeInsets.only(bottom: 9),
                  child: _HistoryTile(scan: scan),
                )).toList(),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _chip(String value, String label) => ChoiceChip(
        label: Text(label),
        selected: _filter == value,
        selectedColor: AppColors.banana,
        side: BorderSide.none,
        onSelected: (_) => setState(() => _filter = value),
      );

  bool _matches(PlantScan scan) {
    final d = scan.diagnosis;
    return switch (_filter) {
      'healthy' => d?.label == 'healthy',
      'disease' => d != null && d.label != 'healthy' && d.label != 'unknown',
      'severe' => d?.severity == 'high',
      'latest' => true,
      _ => true,
    };
  }
}

class _PendingTile extends StatelessWidget {
  const _PendingTile({
    required this.item,
    required this.onRetry,
    required this.onRemove,
  });

  final PendingScan item;
  final VoidCallback onRetry;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final file = File(item.imagePath);
    final place = item.location.placeLabel.isNotEmpty
        ? item.location.placeLabel
        : (item.location.address ?? l.manualFarmPlace);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(13),
              child: file.existsSync()
                  ? Image.file(file, width: 58, height: 58, fit: BoxFit.cover)
                  : Container(
                      width: 58,
                      height: 58,
                      color: AppColors.leafSoft,
                      child: const Icon(Icons.eco_rounded),
                    ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(l.savedOfflineTitle, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12)),
                  const SizedBox(height: 3),
                  Text(place, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: AppColors.muted, fontSize: 10)),
                  if (item.note.trim().isNotEmpty) ...[
                    const SizedBox(height: 3),
                    Text(item.note, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: AppColors.muted, fontSize: 9.5)),
                  ],
                ],
              ),
            ),
            Column(
              children: [
                IconButton.filledTonal(
                  onPressed: onRetry,
                  icon: const Icon(Icons.cloud_upload_outlined, size: 18),
                  tooltip: l.retryUpload,
                ),
                IconButton(
                  onPressed: onRemove,
                  icon: const Icon(Icons.delete_outline_rounded, size: 18),
                  tooltip: l.removePending,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _HistoryTile extends StatelessWidget {
  const _HistoryTile({required this.scan});
  final PlantScan scan;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final d = scan.diagnosis;
    final date = scan.createdAt == null
        ? ''
        : '${scan.createdAt!.day.toString().padLeft(2, '0')}/'
          '${scan.createdAt!.month.toString().padLeft(2, '0')}/'
          '${scan.createdAt!.year}';
    final severity = d?.severity ?? 'unknown';
    final color = severity == 'high'
        ? AppColors.danger
        : severity == 'medium'
            ? AppColors.warning
            : AppColors.leaf;
    final title = d?.displayName ?? _statusLabel(l, scan.status);
    final place = scan.location.placeLabel.isNotEmpty
        ? scan.location.placeLabel
        : (scan.location.address ?? l.manualFarmPlace);

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(22),
        onTap: () => context.push('/diagnosis/${scan.id}'),
        child: Padding(
          padding: const EdgeInsets.all(13),
          child: Row(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(14),
                child: scan.imageUrl.isEmpty
                    ? Container(
                        width: 64,
                        height: 64,
                        color: AppColors.leafSoft,
                        child: const Icon(Icons.eco_rounded),
                      )
                    : Image.network(
                        scan.imageUrl,
                        width: 64,
                        height: 64,
                        fit: BoxFit.cover,
                        errorBuilder: (_, _, _) => Container(
                          width: 64,
                          height: 64,
                          color: AppColors.leafSoft,
                          child: const Icon(Icons.eco_rounded),
                        ),
                      ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontWeight: FontWeight.w900,
                        fontSize: 13,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      place,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: AppColors.muted,
                        fontSize: 11,
                      ),
                    ),
                    if (date.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(
                        date,
                        style: const TextStyle(
                          color: AppColors.muted,
                          fontSize: 10,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Column(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 9,
                      vertical: 5,
                    ),
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
                  if (d != null) ...[
                    const SizedBox(height: 7),
                    Text(
                      '${(d.confidence * 100).round()}%',
                      style: const TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 10,
                      ),
                    ),
                  ],
                ],
              ),
            ],
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
