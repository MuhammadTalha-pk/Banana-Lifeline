import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/firebase/providers.dart';
import '../../core/models/models.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/app_localizations.dart';
import '../../shared/widgets/app_async.dart';
import '../../shared/widgets/brand_mark.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final profile = ref.watch(farmerProfileProvider);
    final farms = ref.watch(farmsProvider);

    return SafeArea(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 110),
        children: [
          const BrandMark(compact: true),
          const SizedBox(height: 24),
          profile.when(
            loading: () => const AppLoading(),
            error: (_, _) => AppErrorCard(message: l.errorTryAgain),
            data: (value) {
              if (value == null) return AppErrorCard(message: l.noProfile);
              return _ProfileHeader(profile: value);
            },
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Text(l.farmRecords, style: Theme.of(context).textTheme.titleLarge),
              const Spacer(),
              TextButton.icon(
                onPressed: () => _showFarmEditor(context, ref),
                icon: const Icon(Icons.add_rounded),
                label: Text(l.addFarm),
              ),
            ],
          ),
          const SizedBox(height: 8),
          farms.when(
            loading: () => const LinearProgressIndicator(minHeight: 2),
            error: (_, _) => AppErrorCard(message: l.errorTryAgain),
            data: (items) {
              if (items.isEmpty) {
                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(22),
                    child: Column(
                      children: [
                        const Icon(Icons.agriculture_outlined, color: AppColors.forest, size: 38),
                        const SizedBox(height: 8),
                        Text(l.noFarms, style: const TextStyle(fontWeight: FontWeight.w900)),
                        const SizedBox(height: 10),
                        FilledButton.tonalIcon(
                          onPressed: () => _showFarmEditor(context, ref),
                          icon: const Icon(Icons.add_rounded),
                          label: Text(l.addFarm),
                        ),
                      ],
                    ),
                  ),
                );
              }
              return Column(
                children: items.map((farm) => Padding(
                  padding: const EdgeInsets.only(bottom: 9),
                  child: _FarmTile(
                    farm: farm,
                    onEdit: () => _showFarmEditor(context, ref, farm: farm),
                    onDelete: () async {
                      await ref.read(profileRepositoryProvider).deleteFarm(farm.id);
                    },
                  ),
                )).toList(),
              );
            },
          ),
          const SizedBox(height: 18),
          Card(
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.edit_outlined, color: AppColors.forest),
                  title: Text(l.editProfile, style: const TextStyle(fontWeight: FontWeight.w800)),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () => context.push('/profile/edit'),
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.settings_outlined, color: AppColors.forest),
                  title: Text(l.settings, style: const TextStyle(fontWeight: FontWeight.w800)),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () => context.push('/settings'),
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.help_outline_rounded, color: AppColors.forest),
                  title: Text(l.aboutHelp, style: const TextStyle(fontWeight: FontWeight.w800)),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () => context.push('/about'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _showFarmEditor(BuildContext context, WidgetRef ref, {Farm? farm}) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (_) => _FarmEditor(farm: farm),
    );
  }
}

class _ProfileHeader extends StatelessWidget {
  const _ProfileHeader({required this.profile});
  final FarmerProfile profile;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [AppColors.forest, AppColors.leaf]),
        borderRadius: BorderRadius.circular(28),
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 36,
            backgroundColor: Colors.white,
            backgroundImage: (profile.profilePhotoUrl ?? '').trim().isEmpty ? null : NetworkImage(profile.profilePhotoUrl!),
            child: (profile.profilePhotoUrl ?? '').trim().isEmpty
                ? const Icon(Icons.person_rounded, size: 36, color: AppColors.forest)
                : null,
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(profile.fullName, style: const TextStyle(color: Colors.white, fontSize: 21, fontWeight: FontWeight.w900)),
                const SizedBox(height: 4),
                Text(profile.email, style: const TextStyle(color: Colors.white70, fontSize: 11)),
                if ((profile.district ?? '').trim().isNotEmpty || (profile.province ?? '').trim().isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      const Icon(Icons.location_on_outlined, size: 14, color: Colors.white70),
                      const SizedBox(width: 4),
                      Expanded(
                        child: Text(
                          [profile.district, profile.province].where((e) => (e ?? '').trim().isNotEmpty).join(', '),
                          style: const TextStyle(color: Colors.white70, fontSize: 10),
                        ),
                      ),
                    ],
                  ),
                ],
                const SizedBox(height: 7),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
                  decoration: BoxDecoration(color: Colors.white.withValues(alpha: .14), borderRadius: BorderRadius.circular(99)),
                  child: Text(l.farmerProfile, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 9)),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class EditProfileScreen extends ConsumerStatefulWidget {
  const EditProfileScreen({super.key});

  @override
  ConsumerState<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends ConsumerState<EditProfileScreen> {
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _district = TextEditingController();
  final _province = TextEditingController();
  final _farmSize = TextEditingController();
  final _cropInfo = TextEditingController();
  final _picker = ImagePicker();
  File? _photo;
  bool _loaded = false;
  bool _saving = false;

  @override
  void dispose() {
    for (final c in [_name, _phone, _district, _province, _farmSize, _cropInfo]) {
      c.dispose();
    }
    super.dispose();
  }

  void _load(FarmerProfile profile) {
    if (_loaded) return;
    _loaded = true;
    _name.text = profile.fullName;
    _phone.text = profile.phone ?? '';
    _district.text = profile.district ?? '';
    _province.text = profile.province ?? '';
    _farmSize.text = profile.farmSize ?? '';
    _cropInfo.text = profile.cropInfo ?? '';
  }

  Future<void> _pickPhoto() async {
    final picked = await _picker.pickImage(source: ImageSource.gallery, imageQuality: 85, maxWidth: 1200);
    if (picked != null && mounted) setState(() => _photo = File(picked.path));
  }

  Future<void> _save() async {
    final l = AppLocalizations.of(context);
    if (_name.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l.requiredField)));
      return;
    }
    setState(() => _saving = true);
    try {
      await ref.read(profileRepositoryProvider).updateProfile(
            fullName: _name.text,
            phone: _phone.text,
            language: Localizations.localeOf(context).languageCode,
            district: _district.text,
            province: _province.text,
            farmSize: _farmSize.text,
            cropInfo: _cropInfo.text,
            profileImage: _photo,
          );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l.profileUpdated)));
      context.pop();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l.errorTryAgain)));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final profile = ref.watch(farmerProfileProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l.editProfile, style: const TextStyle(fontWeight: FontWeight.w900))),
      body: profile.when(
        loading: () => const AppLoading(),
        error: (_, _) => AppErrorCard(message: l.errorTryAgain),
        data: (value) {
          if (value == null) return AppErrorCard(message: l.noProfile);
          _load(value);
          return ListView(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 34),
            children: [
              Center(
                child: Stack(
                  children: [
                    CircleAvatar(
                      radius: 54,
                      backgroundColor: AppColors.leafSoft,
                      backgroundImage: _photo != null
                          ? FileImage(_photo!)
                          : ((value.profilePhotoUrl ?? '').isNotEmpty ? NetworkImage(value.profilePhotoUrl!) as ImageProvider : null),
                      child: _photo == null && (value.profilePhotoUrl ?? '').isEmpty
                          ? const Icon(Icons.person_rounded, size: 48, color: AppColors.forest)
                          : null,
                    ),
                    PositionedDirectional(
                      end: 0,
                      bottom: 0,
                      child: IconButton.filled(
                        onPressed: _pickPhoto,
                        icon: const Icon(Icons.camera_alt_rounded, size: 18),
                        tooltip: l.profileImagePick,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              TextField(controller: _name, decoration: InputDecoration(labelText: l.fullName, prefixIcon: const Icon(Icons.person_outline))),
              const SizedBox(height: 10),
              TextField(controller: _phone, keyboardType: TextInputType.phone, decoration: InputDecoration(labelText: l.phone, prefixIcon: const Icon(Icons.phone_outlined))),
              const SizedBox(height: 10),
              TextField(controller: _district, decoration: InputDecoration(labelText: l.district, hintText: l.districtHint)),
              const SizedBox(height: 10),
              TextField(controller: _province, decoration: InputDecoration(labelText: l.province, hintText: l.provinceHint)),
              const SizedBox(height: 10),
              TextField(controller: _farmSize, decoration: InputDecoration(labelText: l.farmSize, hintText: l.farmSizeHint)),
              const SizedBox(height: 10),
              TextField(controller: _cropInfo, maxLines: 2, decoration: InputDecoration(labelText: l.cropInfo, hintText: l.cropInfoHint)),
              const SizedBox(height: 18),
              FilledButton.icon(
                onPressed: _saving ? null : _save,
                icon: _saving
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.save_outlined),
                label: Text(l.saveChanges),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _FarmTile extends StatelessWidget {
  const _FarmTile({required this.farm, required this.onEdit, required this.onDelete});
  final Farm farm;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Card(
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
        leading: Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(color: AppColors.leafSoft, borderRadius: BorderRadius.circular(15)),
          child: const Icon(Icons.agriculture_rounded, color: AppColors.forest),
        ),
        title: Row(
          children: [
            Expanded(child: Text(farm.name, style: const TextStyle(fontWeight: FontWeight.w900))),
            if (farm.isPrimary)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                decoration: BoxDecoration(color: AppColors.bananaSoft, borderRadius: BorderRadius.circular(99)),
                child: Text(l.primaryFarm, style: const TextStyle(fontSize: 8, fontWeight: FontWeight.w900)),
              ),
          ],
        ),
        subtitle: Text(
          [farm.address, farm.district, farm.province].where((e) => (e ?? '').trim().isNotEmpty).join(' • '),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
        trailing: PopupMenuButton<String>(
          onSelected: (value) => value == 'edit' ? onEdit() : onDelete(),
          itemBuilder: (_) => [
            PopupMenuItem(value: 'edit', child: Text(l.edit)),
            PopupMenuItem(value: 'delete', child: Text(l.deleteFarm)),
          ],
        ),
      ),
    );
  }
}

class _FarmEditor extends ConsumerStatefulWidget {
  const _FarmEditor({this.farm});
  final Farm? farm;

  @override
  ConsumerState<_FarmEditor> createState() => _FarmEditorState();
}

class _FarmEditorState extends ConsumerState<_FarmEditor> {
  late final TextEditingController _name;
  late final TextEditingController _district;
  late final TextEditingController _province;
  late final TextEditingController _size;
  late final TextEditingController _address;
  double? _latitude;
  double? _longitude;
  bool _primary = false;
  bool _saving = false;
  bool _locating = false;

  @override
  void initState() {
    super.initState();
    final f = widget.farm;
    _name = TextEditingController(text: f?.name ?? '');
    _district = TextEditingController(text: f?.district ?? '');
    _province = TextEditingController(text: f?.province ?? '');
    _size = TextEditingController(text: f?.size ?? '');
    _address = TextEditingController(text: f?.address ?? '');
    _latitude = f?.latitude;
    _longitude = f?.longitude;
    _primary = f?.isPrimary ?? false;
  }

  @override
  void dispose() {
    _name.dispose();
    _district.dispose();
    _province.dispose();
    _size.dispose();
    _address.dispose();
    super.dispose();
  }

  Future<void> _gps() async {
    final l = AppLocalizations.of(context);
    setState(() => _locating = true);
    try {
      final location = await ref.read(locationServiceProvider).current(farmName: _name.text.trim());
      if (!mounted) return;
      setState(() {
        _latitude = location.latitude;
        _longitude = location.longitude;
        if ((location.address ?? '').trim().isNotEmpty) _address.text = location.address!;
      });
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l.locationUnavailable)));
    } finally {
      if (mounted) setState(() => _locating = false);
    }
  }

  Future<void> _save() async {
    final l = AppLocalizations.of(context);
    if (_name.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l.farmNameRequired)));
      return;
    }
    setState(() => _saving = true);
    try {
      await ref.read(profileRepositoryProvider).saveFarm(
            Farm(
              id: widget.farm?.id ?? '',
              ownerId: widget.farm?.ownerId ?? '',
              name: _name.text.trim(),
              district: _district.text.trim(),
              province: _province.text.trim(),
              size: _size.text.trim(),
              address: _address.text.trim(),
              latitude: _latitude,
              longitude: _longitude,
              isPrimary: _primary,
            ),
          );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l.farmSaved)));
      Navigator.of(context).pop();
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(l.errorTryAgain)));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 18,
        bottom: MediaQuery.viewInsetsOf(context).bottom + 20,
      ),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(child: Text(widget.farm == null ? l.addFarm : l.editFarm, style: Theme.of(context).textTheme.headlineMedium)),
                IconButton(onPressed: () => Navigator.of(context).pop(), icon: const Icon(Icons.close_rounded)),
              ],
            ),
            const SizedBox(height: 14),
            TextField(controller: _name, decoration: InputDecoration(labelText: l.farmName, prefixIcon: const Icon(Icons.agriculture_outlined))),
            const SizedBox(height: 10),
            TextField(controller: _address, decoration: InputDecoration(labelText: l.farmAddress, prefixIcon: const Icon(Icons.location_on_outlined))),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(child: TextField(controller: _district, decoration: InputDecoration(labelText: l.district))),
                const SizedBox(width: 10),
                Expanded(child: TextField(controller: _province, decoration: InputDecoration(labelText: l.province))),
              ],
            ),
            const SizedBox(height: 10),
            TextField(controller: _size, decoration: InputDecoration(labelText: l.farmSize, hintText: l.farmSizeHint)),
            const SizedBox(height: 10),
            Card(
              child: ListTile(
                leading: const Icon(Icons.gps_fixed_rounded, color: AppColors.forest),
                title: Text(l.gpsLocation, style: const TextStyle(fontWeight: FontWeight.w900)),
                subtitle: Text(
                  _latitude == null ? l.noCoordinates : '${_latitude!.toStringAsFixed(5)}, ${_longitude!.toStringAsFixed(5)}',
                  style: const TextStyle(fontSize: 10),
                ),
                trailing: IconButton.filledTonal(
                  onPressed: _locating ? null : _gps,
                  icon: _locating
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.my_location_rounded),
                ),
              ),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: _primary,
              onChanged: (value) => setState(() => _primary = value),
              title: Text(l.primaryFarm),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: _saving ? null : _save,
                icon: _saving
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.save_outlined),
                label: Text(l.save),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
