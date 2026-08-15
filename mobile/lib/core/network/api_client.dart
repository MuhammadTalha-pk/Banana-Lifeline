import 'dart:io';

import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';

import '../config/app_config.dart';
import '../errors/app_exception.dart';
import '../models/models.dart';

class ApiClient {
  ApiClient(this._auth)
    : _dio = Dio(
        BaseOptions(
          baseUrl: AppConfig.hasAiBaseUrl
              ? AppConfig.apiBase
              : 'http://127.0.0.1:1/api/v1',
          connectTimeout: const Duration(seconds: 20),
          sendTimeout: const Duration(seconds: 90),
          receiveTimeout: const Duration(seconds: 120),
          headers: const {'Accept': 'application/json'},
        ),
      ) {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final user = _auth.currentUser;
          if (user == null) {
            handler.reject(
              DioException(
                requestOptions: options,
                type: DioExceptionType.cancel,
                error: const AppException('Please sign in again.'),
              ),
            );
            return;
          }
          final token = await user.getIdToken();
          options.headers['Authorization'] = 'Bearer $token';
          handler.next(options);
        },
      ),
    );
  }

  final FirebaseAuth _auth;
  final Dio _dio;

  Future<Map<String, dynamic>> health() async {
    _requireAiUrl();
    return _json((await _dio.get('/health')).data);
  }

  void _requireAiUrl() {
    if (!AppConfig.hasAiBaseUrl) {
      throw const AppException('AI_BASE_URL is not configured.');
    }
  }

  Future<Diagnosis> diagnose({
    required String scanId,
    required File image,
    required String language,
    required String note,
    required GeoData location,
  }) async {
    _requireAiUrl();
    try {
      final data = FormData.fromMap({
        'image': await MultipartFile.fromFile(
          image.path,
          filename: image.uri.pathSegments.last,
        ),
        'scan_id': scanId,
        'language': language,
        'scan_target': 'leaf',
        'note': note,
        if (location.latitude != null) 'latitude': location.latitude,
        if (location.longitude != null) 'longitude': location.longitude,
        'address': location.address ?? '',
      });
      final response = await _dio.post('/diagnose', data: data);
      return Diagnosis.fromMap(_json(response.data));
    } on DioException catch (error) {
      throw _friendly(error);
    }
  }

  Future<Diagnosis> retryDiagnosis({required String scanId}) async {
    _requireAiUrl();
    try {
      final response = await _dio.post('/diagnose/retry/$scanId');
      return Diagnosis.fromMap(_json(response.data));
    } on DioException catch (error) {
      throw _friendly(error);
    }
  }

  Future<Map<String, dynamic>> chat({
    String? sessionId,
    required String message,
    required String language,
    String? relatedScanId,
    File? image,
    File? audio,
    GeoData? location,
    String? note,
  }) async {
    _requireAiUrl();

    try {
      if (image != null || audio != null) {
        final data = FormData.fromMap({
          'message': message,
          'language': language,
          'session_id': ?sessionId,
          'related_scan_id': ?relatedScanId,
          if (image != null)
            'image': await MultipartFile.fromFile(
              image.path,
              filename: image.uri.pathSegments.last,
            ),
          if (audio != null)
            'audio': await MultipartFile.fromFile(
              audio.path,
              filename: audio.uri.pathSegments.last,
            ),
          'latitude': ?location?.latitude,
          'longitude': ?location?.longitude,
          if ((location?.address ?? '').isNotEmpty)
            'address': location!.address,
          if ((location?.farmName ?? '').isNotEmpty)
            'farm_name': location!.farmName,
          if ((location?.plotSector ?? '').isNotEmpty)
            'plot_sector': location!.plotSector,
          if ((location?.row ?? '').isNotEmpty) 'row': location!.row,
          if ((location?.plantNumber ?? '').isNotEmpty)
            'plant_number': location!.plantNumber,
          if ((note ?? '').isNotEmpty) 'note': note,
        });
        final response = await _dio.post('/chat/media', data: data);
        return _json(response.data);
      }

      final response = await _dio.post(
        '/chat',
        data: {
          'session_id': sessionId,
          'message': message,
          'language': language,
          'related_scan_id': relatedScanId,
          'latitude': location?.latitude,
          'longitude': location?.longitude,
          'address': location?.address,
          'farm_name': location?.farmName,
          'plot_sector': location?.plotSector,
          'row': location?.row,
          'plant_number': location?.plantNumber,
          'note': note,
        },
      );
      return _json(response.data);
    } on DioException catch (error) {
      throw _friendly(error);
    }
  }

  Future<String> transcribe({
    required File wavFile,
    required String language,
  }) async {
    _requireAiUrl();
    try {
      final data = FormData.fromMap({
        'audio': await MultipartFile.fromFile(
          wavFile.path,
          filename: wavFile.uri.pathSegments.last,
        ),
        'language': language,
      });
      final response = await _dio.post('/transcribe', data: data);
      return _json(response.data)['transcript'] as String? ?? '';
    } on DioException catch (error) {
      throw _friendly(error);
    }
  }

  Future<String> uploadProfilePhoto(File image) async {
    _requireAiUrl();
    try {
      final data = FormData.fromMap({
        'image': await MultipartFile.fromFile(
          image.path,
          filename: image.uri.pathSegments.last,
        ),
      });
      final response = await _dio.post('/profile/photo', data: data);
      final json = _json(response.data);
      final url = json['media_url']?.toString() ?? '';
      if (url.isEmpty) {
        throw const AppException('Profile image URL was not returned.');
      }
      return url;
    } on DioException catch (error) {
      throw _friendly(error);
    }
  }

  Map<String, dynamic> _json(dynamic data) {
    if (data is Map<String, dynamic>) return data;
    if (data is Map) return Map<String, dynamic>.from(data);
    throw const AppException('Unexpected response from the AI service.');
  }

  AppException _friendly(DioException error) {
    final status = error.response?.statusCode;
    final body = error.response?.data;
    String? detail;
    if (body is Map && body['detail'] != null) {
      detail = body['detail'].toString();
    }

    if (status == 401) {
      return const AppException('Your session expired. Please sign in again.');
    }
    if (status == 422) {
      return AppException(
        detail ?? 'This image or audio type is not supported.',
      );
    }
    if (status == 503) {
      return AppException(detail ?? 'The AI service is not ready.');
    }
    if (error.type == DioExceptionType.connectionError ||
        error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.receiveTimeout) {
      return const AppException(
        'Unable to reach the AI service. Check your internet and server address.',
      );
    }
    return AppException(
      detail ?? 'The request could not be completed. Please try again.',
    );
  }
}
