import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

class ApiService {
  static const _storage = FlutterSecureStorage();
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL', defaultValue: 'http://10.0.2.2:8000/api/v1',
  );
  String? token;
  String? _refreshToken;
  Future<bool>? _refreshing;

  Future<void> restoreToken() async {
    token = await _storage.read(key: 'access_token');
    _refreshToken = await _storage.read(key: 'refresh_token');
  }

  Future<void> _saveTokens(Map<String, dynamic> data) async {
    token = data['access_token']?.toString();
    _refreshToken = data['refresh_token']?.toString();
    if (token != null) await _storage.write(key: 'access_token', value: token);
    if (_refreshToken != null) await _storage.write(key: 'refresh_token', value: _refreshToken);
  }

  Future<void> logout() async {
    token = null;
    _refreshToken = null;
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');
  }

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    if (token != null) 'Authorization': 'Bearer $token',
  };

  dynamic _decode(http.Response response) {
    dynamic data;
    try {
      data = jsonDecode(utf8.decode(response.bodyBytes));
    } catch (_) {
      data = {'detail': 'Respuesta no válida del servidor'};
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final message = data is Map ? data['detail'] : null;
      throw Exception(message?.toString() ?? 'Error HTTP ${response.statusCode}');
    }
    return data;
  }

  Future<bool> _refreshSession() async {
    if (_refreshToken == null) return false;
    try {
      final r = await http.post(Uri.parse('$baseUrl/auth/refresh'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'refresh_token': _refreshToken}),
      ).timeout(const Duration(seconds: 15));
      if (r.statusCode != 200) return false;
      await _saveTokens(Map<String, dynamic>.from(_decode(r)));
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<dynamic> _send(Future<http.Response> Function(Map<String, String>) request) async {
    var response = await request(_headers).timeout(const Duration(seconds: 30));
    if (response.statusCode == 401 && _refreshToken != null) {
      _refreshing ??= _refreshSession();
      final success = await _refreshing!;
      _refreshing = null;
      if (success) response = await request(_headers).timeout(const Duration(seconds: 30));
    }
    return _decode(response);
  }

  Future<dynamic> _get(String path) => _send((headers) =>
      http.get(Uri.parse('$baseUrl$path'), headers: headers));
  Future<dynamic> _post(String path, [Object? body]) => _send((headers) =>
      http.post(Uri.parse('$baseUrl$path'), headers: headers,
        body: body == null ? null : jsonEncode(body)));

  Future<Map<String, dynamic>> login(String email, String password) async {
    final r = await http.post(Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    ).timeout(const Duration(seconds: 20));
    final data = Map<String, dynamic>.from(_decode(r));
    await _saveTokens(data);
    return data;
  }

  Future<void> registerDevice({String? pushToken}) async {
    var uid = await _storage.read(key: 'device_uid');
    if (uid == null) {
      uid = 'withyou-${DateTime.now().microsecondsSinceEpoch.toRadixString(36)}';
      await _storage.write(key: 'device_uid', value: uid);
    }
    await _post('/devices', {
      'device_uid': uid, 'platform': 'android',
      'device_name': 'WithYou Android', 'push_token': pushToken,
    });
  }

  Future<Map<String, dynamic>> me() async => Map<String, dynamic>.from(await _get('/me'));
  Future<List<dynamic>> users() async => List<dynamic>.from(await _get('/users'));
  Future<List<dynamic>> contacts() async => List<dynamic>.from(await _get('/trusted-contacts'));
  Future<List<dynamic>> invitations() async => List<dynamic>.from(await _get('/trusted-contacts/invitations'));
  Future<void> acceptInvitation(String id, bool accept) async { await _post('/trusted-contacts/$id/accept', {'accept': accept}); }
  Future<Map<String, dynamic>> addContact(String name, String email, {bool canView = true}) async =>
    Map<String, dynamic>.from(await _post('/trusted-contacts', {
      'contact_name': name, 'contact_email': email, 'can_view_checkpoint': canView,
    }));
  Future<List<dynamic>> notifications({bool pendingOnly = true}) async =>
    List<dynamic>.from(await _get('/notifications?pending_only=$pendingOnly'));
  Future<void> markRead(String id) async { await _post('/notifications/$id/read'); }
  Future<List<dynamic>> pendingSafety() async => List<dynamic>.from(await _get('/safety/pending'));
  Future<List<dynamic>> officialEvents() async => List<dynamic>.from(await _get('/events?limit=10'));
  Future<Map<String, dynamic>> sgcStatus() async => Map<String, dynamic>.from(await _get('/official/sgc/status'));

  Future<Map<String, dynamic>> postCheckpoint(double lat, double lon, {
    double? accuracy, double? battery, String? network, String? movement,
  }) async => Map<String, dynamic>.from(await _post('/checkpoints', {
    'latitude': lat, 'longitude': lon, 'accuracy_m': accuracy,
    'battery_pct': battery, 'network_type': network, 'movement_state': movement,
  }));
  Future<Map<String, dynamic>> latestCheckpoint() async => Map<String, dynamic>.from(await _get('/checkpoints/me/latest'));
  Future<Map<String, dynamic>> respondSafety(String status, {String? eventId, String? welfareCheckId}) async =>
    Map<String, dynamic>.from(await _post('/safety/respond', {
      'status': status, 'event_id': eventId, 'welfare_check_id': welfareCheckId,
    }));
  Future<Map<String, dynamic>> startSos({String? message}) async =>
    Map<String, dynamic>.from(await _post('/sos', {'message': message}));
  Future<Map<String, dynamic>> createTestEvent({
    String type = 'EARTHQUAKE', double magnitude = 6.6,
    double lat = 4.7110, double lon = -74.0721, double radius = 80,
  }) async => Map<String, dynamic>.from(await _post('/test/emergency-events', {
    'type': type, 'source': 'TEST-$type', 'severity': 'SEVERE',
    'certainty': 'OBSERVED', 'urgency': 'IMMEDIATE',
    'latitude': lat, 'longitude': lon, 'radius_km': radius,
    'magnitude': type == 'EARTHQUAKE' ? magnitude : null, 'depth_km': 20,
  }));
  Future<Map<String, dynamic>> requestWelfare(String subjectId, String reason) async =>
    Map<String, dynamic>.from(await _post('/welfare-checks', {'subject_user_id': subjectId, 'reason': reason}));
  Future<List<dynamic>> welfareChecks() async => List<dynamic>.from(await _get('/welfare-checks'));
  Future<Map<String, dynamic>> confirmQuorum(String id, String response) async =>
    Map<String, dynamic>.from(await _post('/welfare-checks/$id/quorum', {'response': response}));
  Future<Map<String, dynamic>> openCase(String subjectId, String notes) async =>
    Map<String, dynamic>.from(await _post('/cases', {'subject_user_id': subjectId, 'notes': notes}));
  Future<List<dynamic>> cases() async => List<dynamic>.from(await _get('/cases'));
  Future<Map<String, dynamic>> startSafetyMode(List<String> contactIds) async =>
    Map<String, dynamic>.from(await _post('/personal-safety/start', {
      'notify_contact_ids': contactIds, 'boost_minutes': 30,
    }));
  Future<Map<String, dynamic>> sirdecPortal() async => Map<String, dynamic>.from(await _get('/official/sirdec/public-portal'));
  Future<Map<String, dynamic>> sirdecPreview({int limit = 20}) async => Map<String, dynamic>.from(await _get('/official/sirdec/preview?limit=$limit'));
  Future<Map<String, dynamic>> syncSgc() async => Map<String, dynamic>.from(await _post('/events/sync/sgc'));
}
