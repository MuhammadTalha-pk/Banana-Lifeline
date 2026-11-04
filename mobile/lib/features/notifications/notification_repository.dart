import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

import '../../core/models/models.dart';

class NotificationRepository {
  NotificationRepository(this._db, this._auth, this._messaging);

  final FirebaseFirestore _db;
  final FirebaseAuth _auth;
  final FirebaseMessaging _messaging;

  Stream<List<AppNotification>> watchNotifications() {
    final uid = _auth.currentUser?.uid;
    if (uid == null) return Stream.value(const []);
    return _db
        .collection('notifications')
        .where('ownerId', isEqualTo: uid)
        .orderBy('createdAt', descending: true)
        .snapshots()
        .map((snapshot) => snapshot.docs.map(AppNotification.fromDoc).toList());
  }

  Future<void> registerDevice() async {
    final user = _auth.currentUser;
    if (user == null) return;
    await _messaging.requestPermission(alert: true, badge: true, sound: true);
    final token = await _messaging.getToken();
    if (token == null) return;
    await _db.collection('users').doc(user.uid).set({
      'fcmTokens': FieldValue.arrayUnion([token]),
      'updatedAt': FieldValue.serverTimestamp(),
    }, SetOptions(merge: true));
  }

  Future<void> markRead(String id) async {
    await _db.collection('notifications').doc(id).update({'read': true});
  }
}
