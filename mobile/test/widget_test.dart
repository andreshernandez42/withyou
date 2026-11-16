import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:with_you/screens/home_screen.dart';
import 'package:with_you/services/api_service.dart';
import 'package:with_you/widgets/safety_check_card.dart';

class FakeApi extends ApiService {
  final String role;
  final bool hasPending;
  final List<String> responses = [];
  FakeApi({this.role = 'USER', this.hasPending = false});
  @override Future<Map<String, dynamic>> me() async => {'full_name': 'Lucía Torres', 'role': role};
  @override Future<List<dynamic>> notifications({bool pendingOnly = true}) async => [];
  @override Future<List<dynamic>> pendingSafety() async => hasPending && responses.isEmpty ? [{'id': 'check1', 'event_id': 'event1', 'event_type': 'EARTHQUAKE', 'is_test': true, 'expires_at': DateTime.now().add(const Duration(minutes: 2)).toUtc().toIso8601String()}] : [];
  @override Future<Map<String, dynamic>> latestCheckpoint() async => {'location': {'lat': 4.7, 'lon': -74.0}, 'created_at': '2026-11-15T12:00:00Z'};
  @override Future<Map<String, dynamic>> respondSafety(String status, {String? eventId, String? welfareCheckId}) async {
    responses.add('$status:$eventId');
    return {'status': status};
  }
}

void main() {
  testWidgets('Three actions call their own callbacks and disable while saving', (tester) async {
    final actions = <String>[];
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: SafetyCheckCard(title: 'Sismo reportado', subtitle: '¿Estás bien?', onSafe: () => actions.add('safe'), onHelp: () => actions.add('help'), onEmergency: () => actions.add('sos')))));
    for (final key in ['safety-safe', 'safety-help', 'safety-emergency']) { await tester.tap(find.byKey(Key(key))); }
    expect(actions, ['safe', 'help', 'sos']);
    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: SafetyCheckCard(title: 'Sismo', subtitle: '¿Estás bien?', onSafe: null, onHelp: null, onEmergency: null))));
    expect(tester.widget<FilledButton>(find.byKey(const Key('safety-safe'))).onPressed, isNull);
    expect(tester.widget<OutlinedButton>(find.byKey(const Key('safety-emergency'))).onPressed, isNull);
  });

  testWidgets('Pending status survives an empty notification inbox', (tester) async {
    final api = FakeApi(hasPending: true);
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: HomeScreen(api: api))));
    await tester.pump(); await tester.pump();
    expect(find.text('Simulacro · Evento sísmico reportado'), findsOneWidget);
    await tester.ensureVisible(find.byKey(const Key('safety-safe')));
    await tester.tap(find.byKey(const Key('safety-safe'))); await tester.pump(); await tester.pump();
    expect(api.responses, ['SAFE:event1']);
    await tester.pumpWidget(const SizedBox()); api.dispose();
  });

  for (final role in ['USER', 'TESTER', 'ADMIN']) {
    testWidgets('Laboratory authorization for $role', (tester) async {
      final api = FakeApi(role: role);
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: HomeScreen(api: api))));
      await tester.pump(); await tester.pump();
      if (role == 'ADMIN') { await tester.scrollUntilVisible(find.text('Laboratorio de pruebas'), 300); }
      expect(find.text('Laboratorio de pruebas', skipOffstage: false), role == 'ADMIN' ? findsOneWidget : findsNothing);
      if (role != 'ADMIN') expect(find.byKey(const Key('safety-safe')), findsOneWidget);
      await tester.pumpWidget(const SizedBox()); api.dispose();
    });
  }
}
