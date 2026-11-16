import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:with_you/widgets/safety_check_card.dart';

void main() {
  testWidgets('Las tres acciones principales de verificación están visibles', (tester) async {
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: SingleChildScrollView(
      child: SafetyCheckCard(
        title: 'Sismo reportado', subtitle: '¿Estás bien?',
        onSafe: () {}, onHelp: () {}, onReport: () {}, onUnable: () {},
      ),
    ))));
    expect(find.text('Estoy a salvo'), findsOneWidget);
    expect(find.text('Necesito ayuda'), findsOneWidget);
    expect(find.text('Reportar emergencia'), findsOneWidget);
  });
}
