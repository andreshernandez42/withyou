import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiService {
  static const _storage = FlutterSecureStorage();
  static const String baseUrl = String.fromEnvironment('API_BASE_URL', defaultValue:'http://10.0.2.2:8000/api/v1');
  String? token;

  Future<void> restoreToken() async { token = await _storage.read(key:'access_token'); }
  Future<void> saveToken(String value) async { token=value; await _storage.write(key:'access_token',value:value); }
  Future<void> logout() async { token=null; await _storage.delete(key:'access_token'); }

  Map<String,String> get _headers => {'Content-Type':'application/json', if(token!=null) 'Authorization':'Bearer $token'};

  Future<dynamic> _handle(http.Response r) async {
    dynamic data;
    try { data=jsonDecode(utf8.decode(r.bodyBytes)); } catch(_) { data={'detail':r.body}; }
    if(r.statusCode<200 || r.statusCode>=300) {
      throw Exception(data is Map && data['detail']!=null ? data['detail'].toString() : 'Error HTTP ${r.statusCode}');
    }
    return data;
  }

  Future<Map<String,dynamic>> login(String email,String password) async {
    final r=await http.post(Uri.parse('$baseUrl/auth/login'),headers:_headers,body:jsonEncode({'email':email,'password':password}));
    final data=Map<String,dynamic>.from(await _handle(r));
    await saveToken(data['access_token']); return data;
  }
  Future<Map<String,dynamic>> me() async => Map<String,dynamic>.from(await _handle(await http.get(Uri.parse('$baseUrl/me'),headers:_headers)));
  Future<List<dynamic>> users() async => List<dynamic>.from(await _handle(await http.get(Uri.parse('$baseUrl/users'),headers:_headers)));
  Future<List<dynamic>> contacts() async => List<dynamic>.from(await _handle(await http.get(Uri.parse('$baseUrl/trusted-contacts'),headers:_headers)));
  Future<List<dynamic>> invitations() async => List<dynamic>.from(await _handle(await http.get(Uri.parse('$baseUrl/trusted-contacts/invitations'),headers:_headers)));
  Future<void> acceptInvitation(String id,bool accept) async { await _handle(await http.post(Uri.parse('$baseUrl/trusted-contacts/$id/accept'),headers:_headers,body:jsonEncode({'accept':accept}))); }
  Future<Map<String,dynamic>> addContact(String name,String email,{bool canView=true}) async => Map<String,dynamic>.from(await _handle(await http.post(Uri.parse('$baseUrl/trusted-contacts'),headers:_headers,body:jsonEncode({'contact_name':name,'contact_email':email,'can_view_checkpoint':canView}))));
  Future<List<dynamic>> notifications({bool pendingOnly=true}) async => List<dynamic>.from(await _handle(await http.get(Uri.parse('$baseUrl/notifications?pending_only=$pendingOnly'),headers:_headers)));
  Future<void> markRead(String id) async { await _handle(await http.post(Uri.parse('$baseUrl/notifications/$id/read'),headers:_headers)); }
  Future<Map<String,dynamic>> postCheckpoint(double lat,double lon,{double? accuracy,double? battery,String? network,String? movement}) async => Map<String,dynamic>.from(await _handle(await http.post(Uri.parse('$baseUrl/checkpoints'),headers:_headers,body:jsonEncode({'latitude':lat,'longitude':lon,'accuracy_m':accuracy,'battery_pct':battery,'network_type':network,'movement_state':movement}))));
  Future<Map<String,dynamic>> latestCheckpoint() async => Map<String,dynamic>.from(await _handle(await http.get(Uri.parse('$baseUrl/checkpoints/me/latest'),headers:_headers)));
  Future<Map<String,dynamic>> respondSafety(String status,{String? eventId,String? welfareCheckId}) async => Map<String,dynamic>.from(await _handle(await http.post(Uri.parse('$baseUrl/safety/respond'),headers:_headers,body:jsonEncode({'status':status,'event_id':eventId,'welfare_check_id':welfareCheckId}))));
  Future<Map<String,dynamic>> createTestEvent({String type='EARTHQUAKE',double magnitude=6.6,double lat=4.7110,double lon=-74.0721,double radius=80}) async => Map<String,dynamic>.from(await _handle(await http.post(Uri.parse('$baseUrl/test/emergency-events'),headers:_headers,body:jsonEncode({'type':type,'source':'TEST-$type','severity':'SEVERE','certainty':'OBSERVED','urgency':'IMMEDIATE','latitude':lat,'longitude':lon,'radius_km':radius,'magnitude':type=='EARTHQUAKE'?magnitude:null,'depth_km':20}))));
  Future<Map<String,dynamic>> requestWelfare(String subjectId,String reason) async => Map<String,dynamic>.from(await _handle(await http.post(Uri.parse('$baseUrl/welfare-checks'),headers:_headers,body:jsonEncode({'subject_user_id':subjectId,'reason':reason}))));
  Future<List<dynamic>> welfareChecks() async => List<dynamic>.from(await _handle(await http.get(Uri.parse('$baseUrl/welfare-checks'),headers:_headers)));
  Future<Map<String,dynamic>> confirmQuorum(String id,String response) async => Map<String,dynamic>.from(await _handle(await http.post(Uri.parse('$baseUrl/welfare-checks/$id/quorum'),headers:_headers,body:jsonEncode({'response':response}))));
  Future<Map<String,dynamic>> openCase(String subjectId,String notes) async => Map<String,dynamic>.from(await _handle(await http.post(Uri.parse('$baseUrl/cases'),headers:_headers,body:jsonEncode({'subject_user_id':subjectId,'notes':notes}))));
  Future<List<dynamic>> cases() async => List<dynamic>.from(await _handle(await http.get(Uri.parse('$baseUrl/cases'),headers:_headers)));
  Future<Map<String,dynamic>> startSafetyMode(List<String> contactIds) async => Map<String,dynamic>.from(await _handle(await http.post(Uri.parse('$baseUrl/personal-safety/start'),headers:_headers,body:jsonEncode({'notify_contact_ids':contactIds,'boost_minutes':30}))));
  Future<Map<String,dynamic>> sirdecPortal() async => Map<String,dynamic>.from(await _handle(await http.get(Uri.parse('$baseUrl/official/sirdec/public-portal'),headers:_headers)));
  Future<Map<String,dynamic>> sirdecPreview({int limit=20}) async => Map<String,dynamic>.from(await _handle(await http.get(Uri.parse('$baseUrl/official/sirdec/preview?limit=$limit'),headers:_headers)));
  Future<Map<String,dynamic>> syncSgc() async => Map<String,dynamic>.from(await _handle(await http.post(Uri.parse('$baseUrl/events/sync/sgc'),headers:_headers)));
}
