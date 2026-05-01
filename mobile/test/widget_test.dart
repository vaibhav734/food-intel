import 'package:flutter_test/flutter_test.dart';

import 'package:food_intel_app/main.dart';

void main() {
  testWidgets('app renders home actions', (WidgetTester tester) async {
    await tester.pumpWidget(const FoodIntelApp());

    expect(find.text('Food Intelligence'), findsOneWidget);
    expect(find.text('Scan Barcode'), findsOneWidget);
    expect(find.text('Enter Manually'), findsOneWidget);
  });
}
