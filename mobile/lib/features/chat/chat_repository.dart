import 'dart:io';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';

import '../../core/models/models.dart';
import '../../core/network/api_client.dart';

class ChatRepository {
  ChatRepository(this._db, this._auth, this._api);

  final FirebaseFirestore _db;
  final FirebaseAuth _auth;
  final ApiClient _api;

  Stream<List<ChatSession>> watchSessions() {
    final uid = _auth.currentUser?.uid;
    if (uid == null) return Stream.value(const []);
    return _db
        .collection('chat_sessions')
        .where('ownerId', isEqualTo: uid)
        .orderBy('updatedAt', descending: true)
        .snapshots()
        .map((snapshot) => snapshot.docs.map(ChatSession.fromDoc).toList());
  }

  Stream<List<ChatMessage>> watchMessages(String sessionId) {
    if (sessionId.isEmpty) return Stream.value(const []);
    return _db
        .collection('chat_sessions')
        .doc(sessionId)
        .collection('messages')
        .orderBy('createdAt')
        .snapshots()
        .map((snapshot) => snapshot.docs.map(ChatMessage.fromDoc).toList());
  }

  Future<Map<String, dynamic>> send({
    String? sessionId,
    required String text,
    required String language,
    String? relatedScanId,
    File? image,
    File? audio,
    GeoData? location,
    String? note,
  }) {
    return _api.chat(
      sessionId: sessionId,
      message: text,
      language: language,
      relatedScanId: relatedScanId,
      image: image,
      audio: audio,
      location: location,
      note: note,
    );
  }

  Future<String> transcribe(File file, String language) {
    return _api.transcribe(wavFile: file, language: language);
  }
}
