import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../l10n/app_localizations.dart';

class AppLoading extends StatelessWidget {
  const AppLoading({super.key, this.message});
  final String? message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(color: AppColors.forest),
            if (message != null) ...[
              const SizedBox(height: 14),
              Text(message!, textAlign: TextAlign.center),
            ],
          ],
        ),
      ),
    );
  }
}

class AppErrorCard extends StatelessWidget {
  const AppErrorCard({super.key, required this.message, this.onRetry});
  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline_rounded, color: AppColors.danger, size: 34),
            const SizedBox(height: 10),
            Text(message, textAlign: TextAlign.center),
            if (onRetry != null) ...[
              const SizedBox(height: 12),
              FilledButton(onPressed: onRetry, child: Text(AppLocalizations.of(context).retry)),
            ],
          ],
        ),
      ),
    );
  }
}
