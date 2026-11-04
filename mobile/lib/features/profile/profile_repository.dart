import 'dart:io';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';

import '../../core/models/models.dart';
import '../../core/network/api_client.dart';

class ProfileRepository {
  ProfileRepository(this._db, this._auth, this._api);

  final FirebaseFirestore _db;
  final FirebaseAuth _auth;
  final ApiClient _api;

  Stream<FarmerProfile?> watchProfile() {
    final uid = _auth.currentUser?.uid;
    if (uid == null) return Stream.value(null);
    return _db.collection('users').doc(uid).snapshots().map((doc) {
      final data = doc.data();
      return data == null ? null : FarmerProfile.fromMap(data);
    });
  }

  Future<FarmerProfile?> getProfile() async {
    final uid = _auth.currentUser?.uid;
    if (uid == null) return null;
    final snap = await _db.collection('users').doc(uid).get();
    return snap.data() == null ? null : FarmerProfile.fromMap(snap.data()!);
  }

  Future<void> updateProfile({
    required String fullName,
    required String phone,
    required String language,
    required String district,
    required String province,
    required String farmSize,
    required String cropInfo,
    File? profileImage,
  }) async {
    final user = _auth.currentUser!;
    String? photoUrl;

    if (profileImage != null) {
      photoUrl = await _api.uploadProfilePhoto(profileImage);
      await user.updatePhotoURL(photoUrl);
    }

    await user.updateDisplayName(fullName.trim());
    await _db.collection('users').doc(user.uid).set({
      'uid': user.uid,
      'email': user.email ?? '',
      'fullName': fullName.trim(),
      'phone': phone.trim(),
      'preferredLanguage': language,
      'district': district.trim(),
      'province': province.trim(),
      'farmSize': farmSize.trim(),
      'cropInfo': cropInfo.trim(),
      'profilePhotoUrl': ?photoUrl,
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  Stream<List<Farm>> watchFarms() {
    final uid = _auth.currentUser?.uid;
    if (uid == null) return Stream.value(const []);
    return _db
        .collection('farms')
        .where('ownerId', isEqualTo: uid)
        .snapshots()
        .map((snapshot) => snapshot.docs.map(Farm.fromDoc).toList());
  }

  Future<void> saveFarm(Farm farm) async {
    final uid = _auth.currentUser!.uid;
    final ref = farm.id.isEmpty
        ? _db.collection('farms').doc()
        : _db.collection('farms').doc(farm.id);

    await ref.set(
      Farm(
        id: ref.id,
        ownerId: uid,
        name: farm.name,
        district: farm.district,
        province: farm.province,
        size: farm.size,
        address: farm.address,
        latitude: farm.latitude,
        longitude: farm.longitude,
        isPrimary: farm.isPrimary,
      ).toMap(),
      SetOptions(merge: true),
    );
  }

  Future<void> setPreferredLanguage(String language) async {
    final uid = _auth.currentUser?.uid;
    if (uid == null) return;
    await _db.collection('users').doc(uid).set({
      'preferredLanguage': language,
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  Future<void> deleteFarm(String farmId) async {
    final uid = _auth.currentUser?.uid;
    if (uid == null) return;
    final ref = _db.collection('farms').doc(farmId);
    final snap = await ref.get();
    if (snap.data()?['ownerId'] == uid) {
      await ref.delete();
    }
  }
}
