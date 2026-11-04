import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../l10n/app_localizations.dart';
import '../shared/widgets/network_status_banner.dart';

class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final path = GoRouterState.of(context).uri.path;
    final paths = ['/home', '/scan', '/chat', '/history', '/profile'];
    var index = paths.indexWhere((item) => path == item || path.startsWith('$item/'));
    if (index < 0) index = 0;
    final l = AppLocalizations.of(context);

    return Scaffold(
      body: Column(
        children: [
          const NetworkStatusBanner(),
          Expanded(child: child),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (value) => context.go(paths[value]),
        destinations: [
          NavigationDestination(icon: const Icon(Icons.home_outlined), selectedIcon: const Icon(Icons.home), label: l.home),
          NavigationDestination(icon: const Icon(Icons.camera_alt_outlined), selectedIcon: const Icon(Icons.camera_alt), label: l.scan),
          NavigationDestination(icon: const Icon(Icons.support_agent_outlined), selectedIcon: const Icon(Icons.support_agent), label: l.aiChat),
          NavigationDestination(icon: const Icon(Icons.history_rounded), label: l.history),
          NavigationDestination(icon: const Icon(Icons.person_outline), selectedIcon: const Icon(Icons.person), label: l.profile),
        ],
      ),
    );
  }
}
