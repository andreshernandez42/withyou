import 'package:geolocator/geolocator.dart';
import 'api_service.dart';

class LocationService {
  final ApiService api;
  LocationService(this.api);

  Future<bool> ensurePermission() async {
    if(!await Geolocator.isLocationServiceEnabled()) return false;
    var p=await Geolocator.checkPermission();
    if(p==LocationPermission.denied) p=await Geolocator.requestPermission();
    return p==LocationPermission.whileInUse || p==LocationPermission.always;
  }

  Future<Map<String,dynamic>?> captureAndUpload() async {
    if(!await ensurePermission()) return null;
    final pos=await Geolocator.getCurrentPosition(desiredAccuracy:LocationAccuracy.high);
    return api.postCheckpoint(pos.latitude,pos.longitude,accuracy:pos.accuracy,network:'mobile',movement:'UNKNOWN');
  }
}
