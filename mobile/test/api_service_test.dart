import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:with_you/services/api_service.dart';

void main() {
  test('Safety response carries the event ID and authenticated status', () async {
    final api = ApiService(client: MockClient((request) async {
      expect(request.url.path.endsWith('/safety/respond'), isTrue);
      expect(request.headers['Authorization'], 'Bearer test-token');
      expect(jsonDecode(request.body), {'status': 'HELP_REQUIRED', 'event_id': 'event-1', 'welfare_check_id': null});
      return http.Response('{"status":"HELP_REQUIRED"}', 200);
    }))..token = 'test-token';
    expect((await api.respondSafety('HELP_REQUIRED', eventId: 'event-1'))['status'], 'HELP_REQUIRED');
    api.dispose();
  });
  test('Server failure does not expose technical details', () async {
    final api = ApiService(client: MockClient((_) async => http.Response('{"detail":"database internal secret"}', 500)));
    await expectLater(api.me(), throwsA(isA<ApiException>().having((e) => e.message, 'friendly message', isNot(contains('secret')))));
    api.dispose();
  });
}
