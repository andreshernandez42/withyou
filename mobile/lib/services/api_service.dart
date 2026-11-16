import 'dart:convert';
import 'dart:async';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiException implements Exception {
  final int? statusCode;
  final String message;
  const ApiException(this.message, {this.statusCode});
  @override String toString() => message;
}

class ApiService {
  final http.Client _client;
  final FlutterSecureStorage _storage;
  Future<void>? _refreshing;
  Future<void> _sessionWrites = Future<void>.value();
  int _sessionGeneration = 0;
  String? token, refreshToken;
  void Function()? onSessionExpired;

  ApiService({http.Client? client, FlutterSecureStorage? storage})
      : _client = client ?? http.Client(),
        _storage = storage ?? const FlutterSecureStorage();
  void dispose() => _client.close();
  static const String baseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:8000/api/v1');
  Map<String, String> get _headers => {'Content-Type': 'application/json', if (token != null) 'Authorization': 'Bearer $token'};

  Future<http.Response> _get(Uri uri, {Map<String, String>? headers}) =>
      _authorized(uri, () => _client.get(uri, headers: _headers));
  Future<http.Response> _post(Uri uri, {Map<String, String>? headers, Object? body}) =>
      _authorized(uri, () => _client.post(uri, headers: _headers, body: body));

  Future<http.Response> _authorized(Uri uri, Future<http.Response> Function() send) async {
    final generation = _sessionGeneration;
    final usedToken = token;
    final response = await _request(send);
    if (generation != _sessionGeneration) throw const ApiException('La sesión cambió. Vuelve a intentarlo.');
    if (response.statusCode != 401 || uri.path.contains('/auth/')) return response;
    if (refreshToken == null) {
      await _clearSession();
      onSessionExpired?.call();
      return response;
    }
    // Concurrent requests reuse the same rotation. A late 401 from the old token
    // retries with the already rotated session instead of rotating it again.
    if (token == usedToken) await _refreshOnce();
    if (generation != _sessionGeneration) throw const ApiException('La sesión cambió. Vuelve a intentarlo.');
    if (token == null) throw const ApiException('Tu sesión venció. Vuelve a iniciar sesión.', statusCode: 401);
    final retried = await _request(send);
    if (retried.statusCode == 401) {
      await _clearSession();
      onSessionExpired?.call();
    }
    return retried;
  }

  Future<http.Response> _request(Future<http.Response> Function() action) async {
    try {
      return await action().timeout(const Duration(seconds: 30));
    } on TimeoutException {
      throw const ApiException('La conexión tardó demasiado. Inténtalo de nuevo.');
    } on http.ClientException {
      throw const ApiException('No pudimos conectar. Revisa tu conexión e inténtalo de nuevo.');
    }
  }

  Future<void> restoreToken() async {
    final saved = await _storage.read(key: 'session');
    if (saved != null) {
      final data = Map<String, dynamic>.from(jsonDecode(saved));
      token = data['access_token'] as String?;
      refreshToken = data['refresh_token'] as String?;
    } else {
      token = await _storage.read(key: 'access_token');
    }
  }

  Future<void> _writeSession(Future<void> Function() action) {
    final task = _sessionWrites.then((_) => action());
    _sessionWrites = task.then<void>((_) {}, onError: (Object error, StackTrace stack) {});
    return task;
  }

  Future<void> _saveSession(Map<String, dynamic> data, int generation) => _writeSession(() async {
    if (generation != _sessionGeneration) return;
    final access = data['access_token'];
    final refresh = data['refresh_token'];
    if (access is! String || access.isEmpty || refresh is! String || refresh.isEmpty) {
      throw const ApiException('No pudimos validar la sesión. Vuelve a iniciar sesión.');
    }
    // Persist the rotated pair in one storage write, never a mixed old/new pair.
    await _storage.write(key: 'session', value: jsonEncode({'access_token': access, 'refresh_token': refresh}));
    if (generation != _sessionGeneration) return;
    token = access;
    refreshToken = refresh;
    await _storage.delete(key: 'access_token');
  });

  Future<void> _refreshOnce() {
    final existing = _refreshing;
    if (existing != null) return existing;
    final task = _rotateSession();
    _refreshing = task;
    return task.whenComplete(() { if (identical(_refreshing, task)) _refreshing = null; });
  }

  Future<void> _rotateSession() async {
    final generation = _sessionGeneration;
    final refresh = refreshToken;
    if (refresh == null) throw const ApiException('Vuelve a iniciar sesión.', statusCode: 401);
    try {
      final response = await _request(() => _client.post(Uri.parse('$baseUrl/auth/refresh'),
          headers: {'Content-Type': 'application/json'}, body: jsonEncode({'refresh_token': refresh})));
      final data = Map<String, dynamic>.from(await _handle(response));
      await _saveSession(data, generation);
    } on ApiException catch (e) {
      if (e.statusCode == 401 && generation == _sessionGeneration) {
        await _clearSession();
        onSessionExpired?.call();
      }
      rethrow;
    }
  }

  Future<void> _clearSession() async {
    _sessionGeneration++;
    token = null;
    refreshToken = null;
    await _writeSession(() async {
      await _storage.delete(key: 'session');
      await _storage.delete(key: 'access_token');
    });
  }

  Future<void> logout() async {
    final access = token;
    final refresh = refreshToken;
    await _clearSession();
    if (access != null && refresh != null) {
      try {
        await _request(() => _client.post(Uri.parse('$baseUrl/auth/logout'),
          headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer $access'},
          body: jsonEncode({'refresh_token': refresh})));
      } on ApiException catch (_) {
        // Local logout succeeds without connectivity; server sessions expire normally.
      }
    }
  }

  Future<dynamic> _handle(http.Response r) async {
    dynamic data;
    try { data=jsonDecode(utf8.decode(r.bodyBytes)); } catch(_) {
      throw const ApiException('La respuesta no pudo procesarse. Inténtalo de nuevo.');
    }
    if(r.statusCode<200 || r.statusCode>=300) {
      throw ApiException(r.statusCode == 401 ? 'Tu sesión venció. Vuelve a iniciar sesión.' : r.statusCode == 403 ? 'No tienes autorización para realizar esta acción.' : r.statusCode == 404 ? 'No hay información disponible todavía.' : 'No pudimos completar la solicitud. Inténtalo de nuevo.', statusCode: r.statusCode);
    }
    return data;
  }

  Future<Map<String,dynamic>> login(String email,String password) async {
    final r=await _post(Uri.parse('$baseUrl/auth/login'),headers:_headers,body:jsonEncode({'email':email,'password':password}));
    final data=Map<String,dynamic>.from(await _handle(r));
    _sessionGeneration++; await _saveSession(data, _sessionGeneration); return data;
  }
  Future<Map<String,dynamic>> me() async => Map<String,dynamic>.from(await _handle(await _get(Uri.parse('$baseUrl/me'),headers:_headers)));
  Future<List<dynamic>> users() async => List<dynamic>.from(await _handle(await _get(Uri.parse('$baseUrl/users'),headers:_headers)));
  Future<List<dynamic>> contacts() async => List<dynamic>.from(await _handle(await _get(Uri.parse('$baseUrl/trusted-contacts'),headers:_headers)));
  Future<List<dynamic>> invitations() async => List<dynamic>.from(await _handle(await _get(Uri.parse('$baseUrl/trusted-contacts/invitations'),headers:_headers)));
  Future<void> acceptInvitation(String id,bool accept) async { await _handle(await _post(Uri.parse('$baseUrl/trusted-contacts/$id/accept'),headers:_headers,body:jsonEncode({'accept':accept}))); }
  Future<Map<String,dynamic>> addContact(String name,String email,{bool canView=true}) async => Map<String,dynamic>.from(await _handle(await _post(Uri.parse('$baseUrl/trusted-contacts'),headers:_headers,body:jsonEncode({'contact_name':name,'contact_email':email,'can_view_checkpoint':canView}))));
  Future<List<dynamic>> notifications({bool pendingOnly=true}) async => List<dynamic>.from(await _handle(await _get(Uri.parse('$baseUrl/notifications?pending_only=$pendingOnly'),headers:_headers)));
  Future<void> markRead(String id) async { await _handle(await _post(Uri.parse('$baseUrl/notifications/$id/read'),headers:_headers)); }
  Future<Map<String,dynamic>> postCheckpoint(double lat,double lon,{double? accuracy,double? battery,String? network,String? movement}) async => Map<String,dynamic>.from(await _handle(await _post(Uri.parse('$baseUrl/checkpoints'),headers:_headers,body:jsonEncode({'latitude':lat,'longitude':lon,'accuracy_m':accuracy,'battery_pct':battery,'network_type':network,'movement_state':movement}))));
  Future<Map<String,dynamic>> latestCheckpoint() async => Map<String,dynamic>.from(await _handle(await _get(Uri.parse('$baseUrl/checkpoints/me/latest'),headers:_headers)));
  Future<Map<String,dynamic>> respondSafety(String status,{String? eventId,String? welfareCheckId}) async => Map<String,dynamic>.from(await _handle(await _post(Uri.parse('$baseUrl/safety/respond'),headers:_headers,body:jsonEncode({'status':status,'event_id':eventId,'welfare_check_id':welfareCheckId}))));
  Future<Map<String,dynamic>> createTestEvent({String type='EARTHQUAKE',double magnitude=6.6,double lat=4.7110,double lon=-74.0721,double radius=80}) async => Map<String,dynamic>.from(await _handle(await _post(Uri.parse('$baseUrl/test/emergency-events'),headers:_headers,body:jsonEncode({'type':type,'source':'TEST-$type','severity':'SEVERE','certainty':'OBSERVED','urgency':'IMMEDIATE','latitude':lat,'longitude':lon,'radius_km':radius,'magnitude':type=='EARTHQUAKE'?magnitude:null,'depth_km':20}))));
  Future<Map<String,dynamic>> requestWelfare(String subjectId,String reason) async => Map<String,dynamic>.from(await _handle(await _post(Uri.parse('$baseUrl/welfare-checks'),headers:_headers,body:jsonEncode({'subject_user_id':subjectId,'reason':reason}))));
  Future<List<dynamic>> welfareChecks() async => List<dynamic>.from(await _handle(await _get(Uri.parse('$baseUrl/welfare-checks'),headers:_headers)));
  Future<Map<String,dynamic>> confirmQuorum(String id,String response) async => Map<String,dynamic>.from(await _handle(await _post(Uri.parse('$baseUrl/welfare-checks/$id/quorum'),headers:_headers,body:jsonEncode({'response':response}))));
  Future<Map<String,dynamic>> openCase(String subjectId,String notes) async => Map<String,dynamic>.from(await _handle(await _post(Uri.parse('$baseUrl/cases'),headers:_headers,body:jsonEncode({'subject_user_id':subjectId,'notes':notes}))));
  Future<List<dynamic>> cases() async => List<dynamic>.from(await _handle(await _get(Uri.parse('$baseUrl/cases'),headers:_headers)));
  Future<Map<String,dynamic>> startSafetyMode(List<String> contactIds) async => Map<String,dynamic>.from(await _handle(await _post(Uri.parse('$baseUrl/personal-safety/start'),headers:_headers,body:jsonEncode({'notify_contact_ids':contactIds,'boost_minutes':30}))));
  Future<Map<String,dynamic>> sirdecPortal() async => Map<String,dynamic>.from(await _handle(await _get(Uri.parse('$baseUrl/official/sirdec/public-portal'),headers:_headers)));
  Future<Map<String,dynamic>> sirdecPreview({int limit=20}) async => Map<String,dynamic>.from(await _handle(await _get(Uri.parse('$baseUrl/official/sirdec/preview?limit=$limit'),headers:_headers)));
  Future<Map<String,dynamic>> syncSgc() async => Map<String,dynamic>.from(await _handle(await _post(Uri.parse('$baseUrl/events/sync/sgc'),headers:_headers)));
  Future<Map<String,dynamic>> sgcStatus() async => Map<String,dynamic>.from(await _handle(await _get(Uri.parse('$baseUrl/official/sgc/status'),headers:_headers)));
  Future<List<dynamic>> pendingSafety() async => List<dynamic>.from(await _handle(await _get(Uri.parse('$baseUrl/safety/pending'), headers: _headers)));
  Future<Map<String, dynamic>> reportEmergency({String? eventId}) async => Map<String, dynamic>.from(await _handle(await _post(Uri.parse('$baseUrl/sos'), headers: _headers, body: jsonEncode({'message': 'Emergencia reportada desde With You', if (eventId != null) 'event_id': eventId}))));
}
