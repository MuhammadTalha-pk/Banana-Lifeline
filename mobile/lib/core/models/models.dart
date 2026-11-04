import 'package:cloud_firestore/cloud_firestore.dart';

DateTime? _date(dynamic value) {
  if (value is Timestamp) return value.toDate();
  if (value is String) return DateTime.tryParse(value);
  return null;
}

class GeoData {
  const GeoData({
    this.latitude,
    this.longitude,
    this.address,
    this.farmName,
    this.plotSector,
    this.row,
    this.plantNumber,
  });

  final double? latitude;
  final double? longitude;
  final String? address;
  final String? farmName;
  final String? plotSector;
  final String? row;
  final String? plantNumber;

  Map<String, dynamic> toMap() => {
        'latitude': latitude,
        'longitude': longitude,
        'address': address,
        'farmName': farmName,
        'plotSector': plotSector,
        'row': row,
        'plantNumber': plantNumber,
      };

  factory GeoData.fromMap(Map<String, dynamic>? map) {
    final data = map ?? const <String, dynamic>{};
    return GeoData(
      latitude: (data['latitude'] as num?)?.toDouble(),
      longitude: (data['longitude'] as num?)?.toDouble(),
      address: data['address'] as String?,
      farmName: data['farmName'] as String?,
      plotSector: data['plotSector'] as String?,
      row: data['row'] as String?,
      plantNumber: data['plantNumber'] as String?,
    );
  }

  String get placeLabel {
    final parts = [
      farmName,
      plotSector,
      row,
      plantNumber,
    ].where((value) => (value ?? '').trim().isNotEmpty).cast<String>().toList();
    if (parts.isNotEmpty) return parts.join(' • ');
    return address?.trim().isNotEmpty == true ? address!.trim() : '';
  }
}

class FarmerProfile {
  const FarmerProfile({
    required this.uid,
    required this.email,
    required this.fullName,
    this.phone,
    this.preferredLanguage = 'en',
    this.district,
    this.province,
    this.farmSize,
    this.cropInfo,
    this.profilePhotoUrl,
    this.createdAt,
  });

  final String uid;
  final String email;
  final String fullName;
  final String? phone;
  final String preferredLanguage;
  final String? district;
  final String? province;
  final String? farmSize;
  final String? cropInfo;
  final String? profilePhotoUrl;
  final DateTime? createdAt;

  Map<String, dynamic> toMap() => {
        'uid': uid,
        'email': email,
        'fullName': fullName,
        'phone': phone,
        'preferredLanguage': preferredLanguage,
        'district': district,
        'province': province,
        'farmSize': farmSize,
        'cropInfo': cropInfo,
        'profilePhotoUrl': profilePhotoUrl,
        'createdAt': createdAt == null ? FieldValue.serverTimestamp() : Timestamp.fromDate(createdAt!),
      };

  factory FarmerProfile.fromMap(Map<String, dynamic> map) => FarmerProfile(
        uid: map['uid'] as String? ?? '',
        email: map['email'] as String? ?? '',
        fullName: map['fullName'] as String? ?? '',
        phone: map['phone'] as String?,
        preferredLanguage: map['preferredLanguage'] as String? ?? 'en',
        district: map['district'] as String?,
        province: map['province'] as String?,
        farmSize: map['farmSize'] as String?,
        cropInfo: map['cropInfo'] as String?,
        profilePhotoUrl: map['profilePhotoUrl'] as String?,
        createdAt: _date(map['createdAt']),
      );
}

class Farm {
  const Farm({
    required this.id,
    required this.ownerId,
    required this.name,
    this.district,
    this.province,
    this.size,
    this.address,
    this.latitude,
    this.longitude,
    this.isPrimary = false,
  });

  final String id;
  final String ownerId;
  final String name;
  final String? district;
  final String? province;
  final String? size;
  final String? address;
  final double? latitude;
  final double? longitude;
  final bool isPrimary;

  Map<String, dynamic> toMap() => {
        'ownerId': ownerId,
        'name': name,
        'district': district,
        'province': province,
        'size': size,
        'address': address,
        'latitude': latitude,
        'longitude': longitude,
        'isPrimary': isPrimary,
        'updatedAt': FieldValue.serverTimestamp(),
      };

  factory Farm.fromDoc(DocumentSnapshot<Map<String, dynamic>> doc) {
    final map = doc.data() ?? {};
    return Farm(
      id: doc.id,
      ownerId: map['ownerId'] as String? ?? '',
      name: map['name'] as String? ?? '',
      district: map['district'] as String?,
      province: map['province'] as String?,
      size: map['size'] as String?,
      address: map['address'] as String?,
      latitude: (map['latitude'] as num?)?.toDouble(),
      longitude: (map['longitude'] as num?)?.toDouble(),
      isPrimary: map['isPrimary'] as bool? ?? false,
    );
  }
}

class SourceRef {
  const SourceRef({required this.title, required this.source, this.page, this.score});
  final String title;
  final String source;
  final int? page;
  final double? score;

  factory SourceRef.fromMap(Map<String, dynamic> map) => SourceRef(
        title: map['title'] as String? ?? 'Source',
        source: map['source'] as String? ?? '',
        page: (map['page'] as num?)?.toInt(),
        score: (map['score'] as num?)?.toDouble(),
      );

  Map<String, dynamic> toMap() => {
        'title': title,
        'source': source,
        'page': page,
        'score': score,
      };
}

class Diagnosis {
  const Diagnosis({
    required this.label,
    required this.displayName,
    required this.confidence,
    required this.severity,
    required this.status,
    this.description,
    this.treatment = const [],
    this.prevention = const [],
    this.additionalAdvice = const [],
    this.expertRecommended = false,
    this.warning,
    this.sources = const [],
    this.requestId,
  });

  final String label;
  final String displayName;
  final double confidence;
  final String severity;
  final String status;
  final String? description;
  final List<String> treatment;
  final List<String> prevention;
  final List<String> additionalAdvice;
  final bool expertRecommended;
  final String? warning;
  final List<SourceRef> sources;
  final String? requestId;

  factory Diagnosis.fromMap(Map<String, dynamic> map) => Diagnosis(
        label: map['label'] as String? ?? 'unknown',
        displayName: map['display_name'] as String? ?? map['displayName'] as String? ?? 'Unknown',
        confidence: (map['confidence'] as num? ?? 0).toDouble(),
        severity: map['severity'] as String? ?? 'unknown',
        status: map['status'] as String? ?? 'completed',
        description: map['description'] as String?,
        treatment: (map['treatment'] as List? ?? const []).map((e) => e.toString()).toList(),
        prevention: (map['prevention'] as List? ?? const []).map((e) => e.toString()).toList(),
        additionalAdvice: (map['additional_advice'] as List? ?? map['additionalAdvice'] as List? ?? const [])
            .map((e) => e.toString())
            .toList(),
        expertRecommended: map['expert_recommended'] as bool? ?? map['expertRecommended'] as bool? ?? false,
        warning: map['warning'] as String?,
        sources: (map['sources'] as List? ?? const [])
            .whereType<Map>()
            .map((e) => SourceRef.fromMap(Map<String, dynamic>.from(e)))
            .toList(),
        requestId: map['request_id'] as String? ?? map['requestId'] as String?,
      );

  Map<String, dynamic> toMap() => {
        'label': label,
        'displayName': displayName,
        'confidence': confidence,
        'severity': severity,
        'status': status,
        'description': description,
        'treatment': treatment,
        'prevention': prevention,
        'additionalAdvice': additionalAdvice,
        'expertRecommended': expertRecommended,
        'warning': warning,
        'sources': sources.map((e) => e.toMap()).toList(),
        'requestId': requestId,
      };
}

class PlantScan {
  const PlantScan({
    required this.id,
    required this.ownerId,
    required this.imageUrl,
    required this.storagePath,
    required this.location,
    required this.note,
    required this.language,
    required this.status,
    this.diagnosis,
    this.errorMessage,
    this.createdAt,
    this.updatedAt,
  });

  final String id;
  final String ownerId;
  final String imageUrl;
  final String storagePath;
  final GeoData location;
  final String note;
  final String language;
  final String status;
  final Diagnosis? diagnosis;
  final String? errorMessage;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  factory PlantScan.fromDoc(DocumentSnapshot<Map<String, dynamic>> doc) {
    final map = doc.data() ?? {};
    return PlantScan(
      id: doc.id,
      ownerId: map['ownerId'] as String? ?? '',
      imageUrl: map['imageUrl'] as String? ?? '',
      storagePath: map['storagePath'] as String? ?? '',
      location: GeoData.fromMap(
        map['location'] is Map ? Map<String, dynamic>.from(map['location'] as Map) : null,
      ),
      note: map['note'] as String? ?? '',
      language: map['language'] as String? ?? 'en',
      status: map['status'] as String? ?? 'pending',
      diagnosis: map['diagnosis'] is Map
          ? Diagnosis.fromMap(Map<String, dynamic>.from(map['diagnosis'] as Map))
          : null,
      errorMessage: map['errorMessage'] as String?,
      createdAt: _date(map['createdAt']),
      updatedAt: _date(map['updatedAt']),
    );
  }
}

class ChatSession {
  const ChatSession({required this.id, required this.title, required this.language, this.updatedAt});
  final String id;
  final String title;
  final String language;
  final DateTime? updatedAt;

  factory ChatSession.fromDoc(DocumentSnapshot<Map<String, dynamic>> doc) {
    final map = doc.data() ?? {};
    return ChatSession(
      id: doc.id,
      title: map['title'] as String? ?? 'Banana Expert',
      language: map['language'] as String? ?? 'en',
      updatedAt: _date(map['updatedAt']),
    );
  }
}

class ChatMessage {
  const ChatMessage({
    required this.id,
    required this.sender,
    required this.text,
    required this.messageType,
    this.imageUrl,
    this.audioUrl,
    this.note,
    this.location,
    this.aiConfidence,
    this.sources = const [],
    this.createdAt,
  });

  final String id;
  final String sender;
  final String text;
  final String messageType;
  final String? imageUrl;
  final String? audioUrl;
  final String? note;
  final GeoData? location;
  final double? aiConfidence;
  final List<SourceRef> sources;
  final DateTime? createdAt;

  factory ChatMessage.fromDoc(DocumentSnapshot<Map<String, dynamic>> doc) {
    final map = doc.data() ?? {};
    return ChatMessage(
      id: doc.id,
      sender: map['sender'] as String? ?? 'user',
      text: map['text'] as String? ?? '',
      messageType: map['messageType'] as String? ?? 'text',
      imageUrl: map['imageUrl'] as String?,
      audioUrl: map['audioUrl'] as String?,
      note: map['note'] as String?,
      location: map['location'] is Map ? GeoData.fromMap(Map<String, dynamic>.from(map['location'] as Map)) : null,
      aiConfidence: (map['aiConfidence'] as num?)?.toDouble(),
      sources: (map['sources'] as List? ?? const [])
          .whereType<Map>()
          .map((e) => SourceRef.fromMap(Map<String, dynamic>.from(e)))
          .toList(),
      createdAt: _date(map['createdAt']),
    );
  }
}

class AppNotification {
  const AppNotification({
    required this.id,
    required this.title,
    required this.body,
    required this.read,
    this.scanId,
    this.type,
    this.createdAt,
  });

  final String id;
  final String title;
  final String body;
  final bool read;
  final String? scanId;
  final String? type;
  final DateTime? createdAt;

  factory AppNotification.fromDoc(
    DocumentSnapshot<Map<String, dynamic>> doc,
  ) {
    final map = doc.data() ?? {};
    return AppNotification(
      id: doc.id,
      title: map['title'] as String? ?? '',
      body: map['body'] as String? ?? '',
      read: map['read'] as bool? ?? false,
      scanId: map['scanId'] as String?,
      type: map['type'] as String?,
      createdAt: _date(map['createdAt']),
    );
  }
}
