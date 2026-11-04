import 'package:flutter/foundation.dart';

class AppConfig {
  static const aiBaseUrl = String.fromEnvironment('AI_BASE_URL');
  static const apiPrefix = String.fromEnvironment(
    'API_PREFIX',
    defaultValue: '/api/v1',
  );

  static bool get hasAiBaseUrl =>
      aiBaseUrl.trim().isNotEmpty && !aiBaseUrl.contains('YOUR_PC');

  static String get apiBase {
    final root = aiBaseUrl.endsWith('/')
        ? aiBaseUrl.substring(0, aiBaseUrl.length - 1)
        : aiBaseUrl;
    final prefix = apiPrefix.startsWith('/') ? apiPrefix : '/$apiPrefix';
    return '$root$prefix';
  }

  static String platformLabel() {
    if (kIsWeb) return 'web';
    return defaultTargetPlatform.name;
  }

  const AppConfig._();
}
