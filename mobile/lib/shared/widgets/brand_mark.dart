import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';

class BrandMark extends StatelessWidget {
  const BrandMark({super.key, this.compact = false, this.light = false});

  final bool compact;
  final bool light;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: compact ? 38 : 56,
          height: compact ? 38 : 56,
          decoration: BoxDecoration(
            color: light ? Colors.white : AppColors.forest,
            borderRadius: BorderRadius.circular(compact ? 13 : 18),
          ),
          child: Icon(
            Icons.eco_rounded,
            color: light ? AppColors.forest : Colors.white,
            size: compact ? 22 : 30,
          ),
        ),
        const SizedBox(width: 10),
        Text(
          'Banana Lifeline',
          style: TextStyle(
            color: light ? Colors.white : AppColors.ink,
            fontWeight: FontWeight.w900,
            fontSize: compact ? 18 : 24,
          ),
        ),
      ],
    );
  }
}
