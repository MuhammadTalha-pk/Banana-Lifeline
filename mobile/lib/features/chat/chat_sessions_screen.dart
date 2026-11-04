import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/firebase/providers.dart';
import '../../core/models/models.dart';
import '../../core/theme/app_colors.dart';
import '../../l10n/app_localizations.dart';
import '../../shared/widgets/app_async.dart';
import '../../shared/widgets/brand_mark.dart';

class ChatSessionsScreen extends ConsumerWidget {
  const ChatSessionsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final sessions = ref.watch(chatSessionsProvider);

    return SafeArea(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 110),
        children: [
          const BrandMark(compact: true),
          const SizedBox(height: 24),
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(l.bananaExpert, style: Theme.of(context).textTheme.headlineMedium),
                    const SizedBox(height: 5),
                    Text(l.expertSubtitle, style: const TextStyle(color: AppColors.muted)),
                  ],
                ),
              ),
              IconButton.filled(
                onPressed: () => context.push('/chat/new'),
                icon: const Icon(Icons.add_comment_rounded),
                tooltip: l.newChat,
              ),
            ],
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [AppColors.forest, AppColors.leaf],
              ),
              borderRadius: BorderRadius.circular(24),
            ),
            child: Row(
              children: [
                Container(
                  width: 58,
                  height: 58,
                  decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle),
                  child: const Icon(Icons.support_agent_rounded, color: AppColors.forest, size: 30),
                ),
                const SizedBox(width: 13),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(l.newConversation, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
                      const SizedBox(height: 4),
                      Text(l.chatContextNote, style: const TextStyle(color: Colors.white70, fontSize: 10.5, height: 1.4)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          Text(l.chatSessions, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          sessions.when(
            loading: () => const AppLoading(),
            error: (_, _) => AppErrorCard(message: l.errorTryAgain),
            data: (items) {
              if (items.isEmpty) {
                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(26),
                    child: Column(
                      children: [
                        const Icon(Icons.forum_outlined, size: 42, color: AppColors.forest),
                        const SizedBox(height: 10),
                        Text(l.noChats, style: const TextStyle(fontWeight: FontWeight.w900)),
                        const SizedBox(height: 12),
                        FilledButton.icon(
                          onPressed: () => context.push('/chat/new'),
                          icon: const Icon(Icons.add_rounded),
                          label: Text(l.newChat),
                        ),
                      ],
                    ),
                  ),
                );
              }
              return Column(
                children: items
                    .map(
                      (session) => Padding(
                        padding: const EdgeInsets.only(bottom: 9),
                        child: _SessionTile(session: session),
                      ),
                    )
                    .toList(),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _SessionTile extends StatelessWidget {
  const _SessionTile({required this.session});
  final ChatSession session;

  @override
  Widget build(BuildContext context) {
    final date = session.updatedAt;
    final dateText = date == null
        ? ''
        : '${date.day.toString().padLeft(2, '0')}/${date.month.toString().padLeft(2, '0')} • ${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';

    return Card(
      child: ListTile(
        onTap: () => context.push('/chat/session/${session.id}'),
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        leading: Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(color: AppColors.leafSoft, borderRadius: BorderRadius.circular(15)),
          child: const Icon(Icons.chat_bubble_outline_rounded, color: AppColors.forest),
        ),
        title: Text(
          session.title,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13),
        ),
        subtitle: dateText.isEmpty ? null : Text(dateText, style: const TextStyle(fontSize: 10)),
        trailing: const Icon(Icons.chevron_right_rounded),
      ),
    );
  }
}
