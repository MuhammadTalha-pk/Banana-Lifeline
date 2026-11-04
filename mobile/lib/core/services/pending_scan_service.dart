import 'dart:convert';
import 'dart:io';

import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

import '../models/models.dart';

class PendingScan {
  const PendingScan({
    required this.id,
    required this.imagePath,
    required this.location,
    required this.note,
    required this.language,
    required this.createdAt,
  });

  final String id;
  final String imagePath;
  final GeoData location;
  final String note;
  final String language;
  final DateTime createdAt;

  Map<String, dynamic> toMap() => {
        'id': id,
        'imagePath': imagePath,
        'location': location.toMap(),
        'note': note,
        'language': language,
        'createdAt': createdAt.toIso8601String(),
      };

  factory PendingScan.fromMap(Map<String, dynamic> map) => PendingScan(
        id: map['id'] as String? ?? '',
        imagePath: map['imagePath'] as String? ?? '',
        location: GeoData.fromMap(
          map['location'] is Map
              ? Map<String, dynamic>.from(map['location'] as Map)
              : null,
        ),
        note: map['note'] as String? ?? '',
        language: map['language'] as String? ?? 'en',
        createdAt: DateTime.tryParse(map['createdAt'] as String? ?? '') ??
            DateTime.now(),
      );
}

class PendingScanService {
  static const _key = 'banana_lifeline_pending_scans_v1';
  final _uuid = const Uuid();

  Future<List<PendingScan>> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null || raw.trim().isEmpty) return [];
    try {
      final list = jsonDecode(raw) as List<dynamic>;
      final items = list
          .whereType<Map>()
          .map((item) => PendingScan.fromMap(Map<String, dynamic>.from(item)))
          .where((item) => item.id.isNotEmpty && File(item.imagePath).existsSync())
          .toList()
        ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
      if (items.length != list.length) await _save(items);
      return items;
    } catch (_) {
      return [];
    }
  }

  Future<PendingScan> enqueue({
    required File image,
    required GeoData location,
    required String note,
    required String language,
    required DateTime createdAt,
  }) async {
    final docs = await getApplicationDocumentsDirectory();
    final folder = Directory('${docs.path}/pending_scans');
    await folder.create(recursive: true);

    final id = _uuid.v4();
    final lower = image.path.toLowerCase();
    final extension = lower.endsWith('.png')
        ? 'png'
        : lower.endsWith('.webp')
            ? 'webp'
            : 'jpg';
    final saved = await image.copy('${folder.path}/$id.$extension');

    final item = PendingScan(
      id: id,
      imagePath: saved.path,
      location: location,
      note: note,
      language: language,
      createdAt: createdAt,
    );
    final items = await load();
    items.insert(0, item);
    await _save(items);
    return item;
  }

  Future<void> remove(String id) async {
    final items = await load();
    PendingScan? removed;
    final kept = <PendingScan>[];
    for (final item in items) {
      if (item.id == id) {
        removed = item;
      } else {
        kept.add(item);
      }
    }
    if (removed != null) {
      try {
        final file = File(removed.imagePath);
        if (await file.exists()) await file.delete();
      } catch (_) {}
    }
    await _save(kept);
  }

  Future<void> _save(List<PendingScan> items) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, jsonEncode(items.map((e) => e.toMap()).toList()));
  }
}
