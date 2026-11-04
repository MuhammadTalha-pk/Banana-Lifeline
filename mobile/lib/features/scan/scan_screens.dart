import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/errors/app_exception.dart';
import '../../core/firebase/providers.dart';
import '../../core/models/models.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/app_localizations.dart';
import '../../shared/widgets/app_async.dart';
import '../../shared/widgets/brand_mark.dart';

class ScanDraft {
  const ScanDraft({
    required this.image,
    required this.location,
    required this.note,
    required this.capturedAt,
  });

  final File image;
  final GeoData location;
  final String note;
  final DateTime capturedAt;
}

class ScanScreen extends ConsumerStatefulWidget {
  const ScanScreen({super.key});

  @override
  ConsumerState<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends ConsumerState<ScanScreen> {
  final _imagePicker = ImagePicker();
  final _farmName = TextEditingController();
  final _plot = TextEditingController();
  final _row = TextEditingController();
  final _plant = TextEditingController();
  final _note = TextEditingController();
  final _manualAddress = TextEditingController();

  File? _image;
  GeoData? _gps;
  bool _locating = false;
  String? _selectedFarmId;

  @override
  void dispose() {
    for (final controller in [
      _farmName,
      _plot,
      _row,
      _plant,
      _note,
      _manualAddress,
    ]) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> _pick(ImageSource source) async {
    final l = AppLocalizations.of(context);
    try {
      final picked = await _imagePicker.pickImage(
        source: source,
        imageQuality: 90,
        maxWidth: 2200,
      );
      if (picked == null || !mounted) return;
      setState(() => _image = File(picked.path));
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l.photoPermissionHelp)),
      );
    }
  }

  Future<void> _captureLocation() async {
    final l = AppLocalizations.of(context);
    setState(() => _locating = true);
    try {
      final result = await ref.read(locationServiceProvider).current(
            farmName: _farmName.text.trim(),
            plotSector: _plot.text.trim(),
            row: _row.text.trim(),
            plantNumber: _plant.text.trim(),
          );
      if (!mounted) return;
      setState(() {
        _gps = result;
        if ((result.address ?? '').trim().isNotEmpty) {
          _manualAddress.text = result.address!.trim();
        }
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l.locationCaptured)),
      );
    } on AppException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_localizedLocationError(l, e.message))),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l.locationUnavailable)),
      );
    } finally {
      if (mounted) setState(() => _locating = false);
    }
  }

  void _useFarm(Farm? farm) {
    if (farm == null) return;
    setState(() {
      _selectedFarmId = farm.id;
      _farmName.text = farm.name;
      _manualAddress.text = farm.address ?? '';
      if (farm.latitude != null || farm.longitude != null) {
        _gps = GeoData(
          latitude: farm.latitude,
          longitude: farm.longitude,
          address: farm.address,
          farmName: farm.name,
          plotSector: _plot.text.trim(),
          row: _row.text.trim(),
          plantNumber: _plant.text.trim(),
        );
      }
    });
  }

  void _review() {
    final l = AppLocalizations.of(context);
    if (_image == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l.imageRequired)),
      );
      return;
    }
    if (_farmName.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l.farmNameRequired)),
      );
      return;
    }

    final location = GeoData(
      latitude: _gps?.latitude,
      longitude: _gps?.longitude,
      address: _manualAddress.text.trim().isNotEmpty
          ? _manualAddress.text.trim()
          : _gps?.address,
      farmName: _farmName.text.trim(),
      plotSector: _plot.text.trim(),
      row: _row.text.trim(),
      plantNumber: _plant.text.trim(),
    );

    context.push(
      '/scan/preview',
      extra: ScanDraft(
        image: _image!,
        location: location,
        note: _note.text.trim(),
        capturedAt: DateTime.now(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final farms = ref.watch(farmsProvider);

    return SafeArea(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 112),
        children: [
          const BrandMark(compact: true),
          const SizedBox(height: 24),
          Text(l.newScan, style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 7),
          Text(l.leafPhotoGuidance, style: const TextStyle(color: AppColors.muted)),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(15),
            decoration: BoxDecoration(
              color: AppColors.bananaSoft,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppColors.banana.withValues(alpha: .35)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.science_outlined, color: AppColors.forest),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(l.leafOnlyTitle, style: const TextStyle(fontWeight: FontWeight.w900)),
                      const SizedBox(height: 4),
                      Text(l.leafOnlyBody, style: const TextStyle(color: AppColors.muted, fontSize: 11, height: 1.45)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          _ImagePanel(
            file: _image,
            onCamera: () => _pick(ImageSource.camera),
            onGallery: () => _pick(ImageSource.gallery),
          ),
          const SizedBox(height: 22),
          Text(l.farmLocationDetails, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 5),
          Text(l.farmLocationHelp, style: const TextStyle(color: AppColors.muted, fontSize: 12)),
          const SizedBox(height: 14),
          farms.when(
            loading: () => const LinearProgressIndicator(minHeight: 2),
            error: (_, _) => const SizedBox.shrink(),
            data: (items) {
              if (items.isEmpty) return const SizedBox.shrink();
              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: DropdownButtonFormField<String>(
                  initialValue: items.any((e) => e.id == _selectedFarmId) ? _selectedFarmId : null,
                  decoration: InputDecoration(
                    labelText: l.useSavedFarm,
                    prefixIcon: const Icon(Icons.agriculture_outlined),
                  ),
                  items: items
                      .map((farm) => DropdownMenuItem(value: farm.id, child: Text(farm.name)))
                      .toList(),
                  onChanged: (id) {
                    final farm = items.where((e) => e.id == id).firstOrNull;
                    _useFarm(farm);
                  },
                ),
              );
            },
          ),
          TextField(
            controller: _farmName,
            decoration: InputDecoration(labelText: l.farmName, prefixIcon: const Icon(Icons.agriculture_outlined)),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _plot,
            decoration: InputDecoration(labelText: l.plotSector, prefixIcon: const Icon(Icons.grid_view_rounded)),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(child: TextField(controller: _row, decoration: InputDecoration(labelText: l.row))),
              const SizedBox(width: 10),
              Expanded(child: TextField(controller: _plant, decoration: InputDecoration(labelText: l.plantNumber))),
            ],
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _manualAddress,
            maxLines: 2,
            decoration: InputDecoration(
              labelText: l.manualAddress,
              prefixIcon: const Icon(Icons.location_on_outlined),
            ),
          ),
          const SizedBox(height: 10),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  Container(
                    width: 46,
                    height: 46,
                    decoration: BoxDecoration(color: AppColors.leafSoft, borderRadius: BorderRadius.circular(15)),
                    child: const Icon(Icons.my_location_rounded, color: AppColors.forest),
                  ),
                  const SizedBox(width: 11),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(l.gpsLocation, style: const TextStyle(fontWeight: FontWeight.w900)),
                        const SizedBox(height: 3),
                        Text(
                          _gps?.latitude == null
                              ? l.locationOptional
                              : '${_gps!.latitude!.toStringAsFixed(5)}, ${_gps!.longitude!.toStringAsFixed(5)}',
                          style: const TextStyle(color: AppColors.muted, fontSize: 10.5),
                        ),
                      ],
                    ),
                  ),
                  IconButton.filledTonal(
                    onPressed: _locating ? null : _captureLocation,
                    icon: _locating
                        ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                        : const Icon(Icons.gps_fixed_rounded),
                    tooltip: l.captureGps,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _note,
            maxLines: 4,
            decoration: InputDecoration(
              labelText: l.note,
              hintText: l.noteHint,
              alignLabelWithHint: true,
              prefixIcon: const Padding(
                padding: EdgeInsets.only(bottom: 74),
                child: Icon(Icons.notes_rounded),
              ),
            ),
          ),
          const SizedBox(height: 18),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: _review,
              icon: const Icon(Icons.arrow_forward_rounded),
              label: Text(l.preview),
            ),
          ),
        ],
      ),
    );
  }

  String _localizedLocationError(AppLocalizations l, String raw) {
    final lower = raw.toLowerCase();
    if (lower.contains('permanently')) return '${l.locationPermissionDenied} ${l.locationSettingsHelp}';
    if (lower.contains('permission')) return l.locationPermissionDenied;
    if (lower.contains('gps')) return l.locationServicesOff;
    return l.locationUnavailable;
  }
}

class _ImagePanel extends StatelessWidget {
  const _ImagePanel({required this.file, required this.onCamera, required this.onGallery});

  final File? file;
  final VoidCallback onCamera;
  final VoidCallback onGallery;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(22),
            child: Container(
              height: 260,
              width: double.infinity,
              color: AppColors.leafSoft,
              child: file == null
                  ? const Center(child: Icon(Icons.eco_outlined, size: 64, color: AppColors.forest))
                  : Image.file(file!, fit: BoxFit.cover),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: FilledButton.tonalIcon(
                  onPressed: onCamera,
                  icon: const Icon(Icons.camera_alt_rounded),
                  label: Text(file == null ? l.takePhoto : l.changePhoto),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: onGallery,
                  icon: const Icon(Icons.photo_library_outlined),
                  label: Text(l.chooseGallery),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class ScanPreviewScreen extends ConsumerStatefulWidget {
  const ScanPreviewScreen({super.key, required this.draft});
  final ScanDraft draft;

  @override
  ConsumerState<ScanPreviewScreen> createState() => _ScanPreviewScreenState();
}

class _ScanPreviewScreenState extends ConsumerState<ScanPreviewScreen> {
  bool _submitting = false;

  Future<void> _submit() async {
    final l = AppLocalizations.of(context);
    setState(() => _submitting = true);
    try {
      final scanId = await ref.read(scanRepositoryProvider).submit(
            image: widget.draft.image,
            location: widget.draft.location,
            note: widget.draft.note,
            language: Localizations.localeOf(context).languageCode,
          );
      if (!mounted) return;
      context.go('/diagnosis/$scanId');
    } catch (_) {
      if (!mounted) return;
      try {
        await ref.read(pendingScanServiceProvider).enqueue(
              image: widget.draft.image,
              location: widget.draft.location,
              note: widget.draft.note,
              language: Localizations.localeOf(context).languageCode,
              createdAt: widget.draft.capturedAt,
            );
        if (!mounted) return;
        await showDialog<void>(
          context: context,
          builder: (context) => AlertDialog(
            icon: const Icon(Icons.cloud_off_rounded),
            title: Text(l.savedOfflineTitle),
            content: Text(l.savedOfflineBody),
            actions: [
              FilledButton(
                onPressed: () => Navigator.of(context).pop(),
                child: Text(l.close),
              ),
            ],
          ),
        );
        if (mounted) context.go('/history');
      } catch (_) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l.imageUploadFailed)),
        );
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final d = widget.draft;
    return Scaffold(
      appBar: AppBar(title: Text(l.preview, style: const TextStyle(fontWeight: FontWeight.w900))),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 34),
          children: [
            Text(l.reviewBeforeSubmit, style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 6),
            Text(l.realAiNotice, style: const TextStyle(color: AppColors.muted)),
            const SizedBox(height: 16),
            ClipRRect(
              borderRadius: BorderRadius.circular(28),
              child: Image.file(d.image, height: 280, width: double.infinity, fit: BoxFit.cover),
            ),
            const SizedBox(height: 14),
            _InfoCard(
              title: l.exactFarmPlace,
              icon: Icons.location_on_outlined,
              rows: [
                (l.farmName, d.location.farmName ?? '—'),
                (l.plotSector, d.location.plotSector ?? '—'),
                (l.row, d.location.row ?? '—'),
                (l.plantNumber, d.location.plantNumber ?? '—'),
                (l.address, d.location.address ?? '—'),
                (
                  l.coordinates,
                  d.location.latitude == null
                      ? l.noCoordinates
                      : '${d.location.latitude!.toStringAsFixed(5)}, ${d.location.longitude!.toStringAsFixed(5)}',
                ),
              ],
            ),
            const SizedBox(height: 12),
            _InfoCard(
              title: l.note,
              icon: Icons.notes_rounded,
              rows: [
                (l.note, d.note.isEmpty ? l.emptyNote : d.note),
                (l.dateTime, MaterialLocalizations.of(context).formatFullDate(d.capturedAt)),
              ],
            ),
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(color: AppColors.bananaSoft, borderRadius: BorderRadius.circular(18)),
              child: Row(
                children: [
                  const Icon(Icons.hourglass_top_rounded, color: AppColors.forest),
                  const SizedBox(width: 9),
                  Expanded(child: Text(l.processingWarning, style: const TextStyle(fontSize: 11, color: AppColors.muted))),
                ],
              ),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _submitting ? null : _submit,
              icon: _submitting
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.auto_awesome_rounded),
              label: Text(_submitting ? l.analyzing : l.submitForDiagnosis),
            ),
          ],
        ),
      ),
    );
  }
}

class DiagnosisDetailScreen extends ConsumerWidget {
  const DiagnosisDetailScreen({super.key, required this.scanId});
  final String scanId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l.diagnosis, style: const TextStyle(fontWeight: FontWeight.w900))),
      body: StreamBuilder<PlantScan?>(
        stream: ref.watch(scanRepositoryProvider).watchScan(scanId),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) return const AppLoading();
          if (snapshot.hasError) return Padding(padding: const EdgeInsets.all(20), child: AppErrorCard(message: l.errorTryAgain));
          final scan = snapshot.data;
          if (scan == null) return Padding(padding: const EdgeInsets.all(20), child: AppErrorCard(message: l.errorTryAgain));
          return _DiagnosisBody(
            scan: scan,
            onRetry: () => ref.read(scanRepositoryProvider).retry(scanId),
          );
        },
      ),
    );
  }
}

class _DiagnosisBody extends StatelessWidget {
  const _DiagnosisBody({
    required this.scan,
    required this.onRetry,
  });

  final PlantScan scan;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final diagnosis = scan.diagnosis;

    if (scan.status == 'processing' || scan.status == 'pending') {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const CircularProgressIndicator(),
              const SizedBox(height: 18),
              Text(l.processingImage, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 7),
              Text(l.analyzingSubtitle, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.muted)),
            ],
          ),
        ),
      );
    }

    if (scan.status == 'failed' || diagnosis == null) {
      return ListView(
        padding: const EdgeInsets.all(20),
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: Image.network(scan.imageUrl, height: 220, fit: BoxFit.cover, errorBuilder: (_, _, _) => Container(height: 220, color: AppColors.leafSoft)),
          ),
          const SizedBox(height: 14),
          AppErrorCard(message: scan.errorMessage?.contains('not configured') == true ? l.modelServiceNotReady : l.scanFailedReason),
          const SizedBox(height: 12),
          Text(l.backendNotReady, style: const TextStyle(fontWeight: FontWeight.w900)),
          const SizedBox(height: 5),
          Text(l.modelNotReadyBody, style: const TextStyle(color: AppColors.muted)),
          const SizedBox(height: 18),
          FilledButton.icon(
            onPressed: () async {
              try {
                await onRetry();
                if (!context.mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text(l.retryStarted)),
                );
              } catch (_) {
                if (!context.mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(content: Text(l.retryFailed)),
                );
              }
            },
            icon: const Icon(Icons.refresh_rounded),
            label: Text(l.retryDiagnosis),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () => context.go('/scan'),
            icon: const Icon(Icons.add_a_photo_outlined),
            label: Text(l.scanAgain),
          ),
        ],
      );
    }

    final severityColor = switch (diagnosis.severity) {
      'high' => AppColors.danger,
      'medium' => AppColors.warning,
      _ => AppColors.leaf,
    };

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 38),
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(28),
          child: Image.network(
            scan.imageUrl,
            height: 260,
            fit: BoxFit.cover,
            errorBuilder: (_, _, _) => Container(height: 260, color: AppColors.leafSoft, child: const Icon(Icons.eco_rounded, size: 54)),
          ),
        ),
        const SizedBox(height: 14),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    _Pill(text: _statusLabel(l, diagnosis.severity), color: severityColor),
                    const Spacer(),
                    Text('${(diagnosis.confidence * 100).round()}%', style: TextStyle(color: severityColor, fontWeight: FontWeight.w900, fontSize: 19)),
                  ],
                ),
                const SizedBox(height: 14),
                Text(diagnosis.displayName, style: Theme.of(context).textTheme.headlineMedium),
                const SizedBox(height: 7),
                if ((diagnosis.description ?? '').trim().isNotEmpty)
                  Text(diagnosis.description!, style: const TextStyle(color: AppColors.muted, height: 1.5))
                else
                  Text(l.noGuidanceAvailable, style: const TextStyle(color: AppColors.muted)),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        if ((diagnosis.warning ?? '').trim().isNotEmpty)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.warning.withValues(alpha: .10),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppColors.warning.withValues(alpha: .30)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.warning_amber_rounded, color: AppColors.warning),
                const SizedBox(width: 9),
                Expanded(child: Text(diagnosis.warning!, style: const TextStyle(fontSize: 11.5, height: 1.45))),
              ],
            ),
          ),
        const SizedBox(height: 12),
        _InfoCard(
          title: l.exactFarmPlace,
          icon: Icons.location_on_outlined,
          rows: [
            (l.farmName, scan.location.farmName ?? '—'),
            (l.plotSector, scan.location.plotSector ?? '—'),
            (l.row, scan.location.row ?? '—'),
            (l.plantNumber, scan.location.plantNumber ?? '—'),
            (l.address, scan.location.address ?? '—'),
            (
              l.coordinates,
              scan.location.latitude == null
                  ? l.noCoordinates
                  : '${scan.location.latitude!.toStringAsFixed(5)}, ${scan.location.longitude!.toStringAsFixed(5)}',
            ),
            (l.note, scan.note.isEmpty ? l.emptyNote : scan.note),
          ],
        ),
        const SizedBox(height: 12),
        _GuidanceSection(title: l.treatment, icon: Icons.healing_outlined, items: diagnosis.treatment),
        const SizedBox(height: 10),
        _GuidanceSection(title: l.prevention, icon: Icons.shield_outlined, items: diagnosis.prevention),
        const SizedBox(height: 10),
        _GuidanceSection(title: l.additionalAdvice, icon: Icons.tips_and_updates_outlined, items: diagnosis.additionalAdvice),
        if (diagnosis.sources.isNotEmpty) ...[
          const SizedBox(height: 14),
          Text(l.aiSources, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          ...diagnosis.sources.map(
            (source) => Card(
              child: ListTile(
                leading: const Icon(Icons.menu_book_outlined, color: AppColors.forest),
                title: Text(source.title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12)),
                subtitle: Text([
                  source.source,
                  if (source.page != null) l.sourcePage(source.page!),
                ].where((e) => e.trim().isNotEmpty).join(' • ')),
              ),
            ),
          ),
        ],
        const SizedBox(height: 18),
        FilledButton.icon(
          onPressed: () => context.push('/chat/new?scan=${Uri.encodeComponent(scan.id)}'),
          icon: const Icon(Icons.support_agent_rounded),
          label: Text(l.askAboutThisScan),
        ),
      ],
    );
  }

  static String _statusLabel(AppLocalizations l, String value) {
    return switch (value) {
      'high' => l.high,
      'medium' => l.medium,
      'low' => l.low,
      _ => l.unknown,
    };
  }
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.title, required this.icon, required this.rows});
  final String title;
  final IconData icon;
  final List<(String, String)> rows;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(17),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [Icon(icon, color: AppColors.forest), const SizedBox(width: 8), Text(title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16))]),
            const SizedBox(height: 12),
            for (final row in rows)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(width: 108, child: Text(row.$1, style: const TextStyle(color: AppColors.muted, fontSize: 10.5))),
                    Expanded(child: Text(row.$2.trim().isEmpty ? '—' : row.$2, textAlign: TextAlign.end, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 10.5))),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _GuidanceSection extends StatelessWidget {
  const _GuidanceSection({required this.title, required this.icon, required this.items});
  final String title;
  final IconData icon;
  final List<String> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const SizedBox.shrink();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(17),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [Icon(icon, color: AppColors.forest), const SizedBox(width: 8), Expanded(child: Text(title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)))]),
            const SizedBox(height: 12),
            for (var i = 0; i < items.length; i++)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(color: AppColors.leafSoft, borderRadius: BorderRadius.circular(9)),
                      child: Text('${i + 1}', style: const TextStyle(color: AppColors.forest, fontWeight: FontWeight.w900)),
                    ),
                    const SizedBox(width: 9),
                    Expanded(child: Text(items[i], style: const TextStyle(fontSize: 12, height: 1.45))),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill({required this.text, required this.color});
  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
      decoration: BoxDecoration(color: color.withValues(alpha: .10), borderRadius: BorderRadius.circular(99)),
      child: Text(text, style: TextStyle(color: color, fontWeight: FontWeight.w900, fontSize: 10)),
    );
  }
}

extension _FirstOrNull<E> on Iterable<E> {
  E? get firstOrNull => isEmpty ? null : first;
}
