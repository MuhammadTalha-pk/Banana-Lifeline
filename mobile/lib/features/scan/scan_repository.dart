import 'dart:io';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:uuid/uuid.dart';

import '../../core/models/models.dart';
import '../../core/network/api_client.dart';

class ScanRepository {
  ScanRepository(this._db, this._auth, this._api);

  final FirebaseFirestore _db;
  final FirebaseAuth _auth;
  final ApiClient _api;
  final _uuid = const Uuid();

  Stream<List<PlantScan>> watchScans({int limit = 100}) {
    final uid = _auth.currentUser?.uid;
    if (uid == null) return Stream.value(const []);
    return _db
        .collection('plant_scans')
        .where('ownerId', isEqualTo: uid)
        .orderBy('createdAt', descending: true)
        .limit(limit)
        .snapshots()
        .map((snapshot) => snapshot.docs.map(PlantScan.fromDoc).toList());
  }

  Stream<PlantScan?> watchScan(String id) {
    return _db.collection('plant_scans').doc(id).snapshots().map((doc) {
      if (!doc.exists) return null;
      return PlantScan.fromDoc(doc);
    });
  }

  Future<void> retry(String scanId) async {
    final user = _auth.currentUser;
    if (user == null) {
      throw StateError('No authenticated user.');
    }

    final ref = _db.collection('plant_scans').doc(scanId);
    final snapshot = await ref.get();
    final data = snapshot.data();

    if (!snapshot.exists || data?['ownerId'] != user.uid) {
      throw StateError('Scan not found for this account.');
    }

    await ref.update({
      'status': 'processing',
      'errorMessage': FieldValue.delete(),
      'updatedAt': FieldValue.serverTimestamp(),
    });

    try {
      await _api.retryDiagnosis(scanId: scanId);
    } catch (error) {
      await ref.update({
        'status': 'failed',
        'errorMessage': error.toString(),
        'updatedAt': FieldValue.serverTimestamp(),
      });
      rethrow;
    }
  }

  Future<String> submit({
    required File image,
    required GeoData location,
    required String note,
    required String language,
  }) async {
    final user = _auth.currentUser;
    if (user == null) throw StateError('No authenticated user.');

    final scanId = _uuid.v4();
    final ref = _db.collection('plant_scans').doc(scanId);

    // Create only trusted metadata from the farmer. The authenticated FastAPI
    // service stores the real image locally, writes imageUrl/mediaPath through
    // Firebase Admin, runs the real AI model, and writes the diagnosis.
    await ref.set({
      'ownerId': user.uid,
      'imageUrl': '',
      'storagePath': '',
      'location': location.toMap(),
      'note': note.trim(),
      'language': language,
      'status': 'processing',
      'createdAt': FieldValue.serverTimestamp(),
      'updatedAt': FieldValue.serverTimestamp(),
    });

    try {
      await _api.diagnose(
        scanId: scanId,
        image: image,
        language: language,
        note: note,
        location: location,
      );
    } catch (error) {
      await ref.update({
        'status': 'failed',
        'errorMessage': error.toString(),
        'updatedAt': FieldValue.serverTimestamp(),
      });
    }

    return scanId;
  }
}
