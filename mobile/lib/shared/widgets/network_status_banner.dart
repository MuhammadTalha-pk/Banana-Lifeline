import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../l10n/app_localizations.dart';

class NetworkStatusBanner extends StatefulWidget {
  const NetworkStatusBanner({super.key});

  @override
  State<NetworkStatusBanner> createState() => _NetworkStatusBannerState();
}

class _NetworkStatusBannerState extends State<NetworkStatusBanner> {
  final Connectivity _connectivity = Connectivity();
  StreamSubscription<List<ConnectivityResult>>? _subscription;
  bool _offline = false;

  @override
  void initState() {
    super.initState();
    _refresh();
    _subscription = _connectivity.onConnectivityChanged.listen(_apply);
  }

  Future<void> _refresh() async {
    try {
      _apply(await _connectivity.checkConnectivity());
    } catch (_) {
      // Network requests still have their own timeout/error handling.
    }
  }

  void _apply(List<ConnectivityResult> result) {
    final offline = result.isEmpty || result.contains(ConnectivityResult.none);
    if (!mounted || offline == _offline) return;
    setState(() => _offline = offline);
  }

  @override
  void dispose() {
    _subscription?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_offline) return const SizedBox.shrink();
    final l = AppLocalizations.of(context);

    return Material(
      color: AppColors.warning.withValues(alpha: .14),
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          child: Row(
            children: [
              const Icon(
                Icons.wifi_off_rounded,
                size: 18,
                color: AppColors.warning,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  l.noInternetAi,
                  style: const TextStyle(
                    fontSize: 10,
                    height: 1.35,
                    color: AppColors.ink,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
