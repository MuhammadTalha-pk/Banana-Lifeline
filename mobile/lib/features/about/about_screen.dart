import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../l10n/app_localizations.dart';
import '../../shared/widgets/brand_mark.dart';

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l.aboutHelp, style: const TextStyle(fontWeight: FontWeight.w900))),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 36),
          children: [
            const Center(child: BrandMark()),
            const SizedBox(height: 12),
            Text(l.aboutSubtitle, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.muted, height: 1.5)),
            const SizedBox(height: 22),
            _AboutCard(icon: Icons.eco_outlined, title: l.whatAppDoes, body: l.helpBody),
            const SizedBox(height: 10),
            _AboutCard(icon: Icons.science_outlined, title: l.scientificScope, body: l.scientificScopeBody),
            const SizedBox(height: 10),
            _AboutCard(icon: Icons.privacy_tip_outlined, title: l.privacyTitle, body: l.privacyBody),
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: AppColors.bananaSoft, borderRadius: BorderRadius.circular(20)),
              child: Text(l.modelNotReadyBody, style: const TextStyle(color: AppColors.muted, fontSize: 11, height: 1.45)),
            ),
          ],
        ),
      ),
    );
  }
}

class _AboutCard extends StatelessWidget {
  const _AboutCard({required this.icon, required this.title, required this.body});
  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(17),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 45,
              height: 45,
              decoration: BoxDecoration(color: AppColors.leafSoft, borderRadius: BorderRadius.circular(14)),
              child: Icon(icon, color: AppColors.forest),
            ),
            const SizedBox(width: 11),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontWeight: FontWeight.w900)),
                  const SizedBox(height: 5),
                  Text(body, style: const TextStyle(color: AppColors.muted, fontSize: 11, height: 1.45)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
