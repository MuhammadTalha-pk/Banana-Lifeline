import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/firebase/providers.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/app_localizations.dart';
import '../../shared/widgets/app_async.dart';

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final notifications = ref.watch(notificationsProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l.notifications, style: const TextStyle(fontWeight: FontWeight.w900))),
      body: SafeArea(
        child: notifications.when(
          loading: () => const AppLoading(),
          error: (_, _) => AppErrorCard(message: l.errorTryAgain),
          data: (items) {
            if (items.isEmpty) {
              return Center(
                child: Padding(
                  padding: const EdgeInsets.all(28),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.notifications_none_rounded, size: 52, color: AppColors.forest),
                      const SizedBox(height: 12),
                      Text(l.notificationEmpty, style: const TextStyle(fontWeight: FontWeight.w900)),
                      const SizedBox(height: 6),
                      Text(l.notificationInfo, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.muted, fontSize: 11)),
                    ],
                  ),
                ),
              );
            }
            return ListView.separated(
              padding: const EdgeInsets.all(20),
              itemCount: items.length,
              separatorBuilder: (_, _) => const SizedBox(height: 9),
              itemBuilder: (_, index) {
                final item = items[index];
                return Card(
                  color: item.read ? Colors.white : AppColors.bananaSoft,
                  child: ListTile(
                    onTap: item.scanId == null
                        ? null
                        : () async {
                            if (!item.read) {
                              await ref
                                  .read(notificationRepositoryProvider)
                                  .markRead(item.id);
                            }
                            if (context.mounted) {
                              context.push('/diagnosis/${item.scanId}');
                            }
                          },
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                    leading: CircleAvatar(
                      backgroundColor: item.read ? AppColors.leafSoft : AppColors.banana,
                      child: Icon(item.read ? Icons.notifications_none_rounded : Icons.notification_important_rounded, color: AppColors.forest),
                    ),
                    title: Text(item.title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13)),
                    subtitle: Text(item.body, style: const TextStyle(fontSize: 11)),
                    trailing: item.read
                        ? null
                        : IconButton(
                            onPressed: () => ref.read(notificationRepositoryProvider).markRead(item.id),
                            icon: const Icon(Icons.done_rounded),
                            tooltip: l.markRead,
                          ),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
