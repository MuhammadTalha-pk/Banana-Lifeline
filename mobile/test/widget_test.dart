import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:banana_lifeline/app/app.dart';

void main() {
  testWidgets('Banana Lifeline app builds', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: BananaLifelineApp()));

    expect(find.byType(BananaLifelineApp), findsOneWidget);
  });
}
