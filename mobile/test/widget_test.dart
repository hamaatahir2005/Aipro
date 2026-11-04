import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:trademind/main.dart';
void main(){
  testWidgets('Login protects dashboard and language selector supports RTL',(tester)async{
    await tester.pumpWidget(const TradeMind());
    expect(find.text('Login'),findsOneWidget);
    expect(find.textContaining('TradeMind'),findsWidgets);
    expect(find.byType(NavigationBar),findsNothing);
    await tester.tap(find.byType(DropdownButton<String>));await tester.pumpAndSettle();
    await tester.tap(find.text('عربي').last);await tester.pumpAndSettle();
    expect(find.text('دخول'),findsOneWidget);
  });
}
