import 'package:geolocator/geolocator.dart';
import 'api_service.dart';

class LocationService {
  final ApiService api;
  LocationService(this.api);

  Future<bool> ensurePermission() async {
    if (!await Geolocator.isLocationServiceEnabled()) {
      throw StateError('Activa el GPS o los servicios de ubicación del dispositivo.');
    }
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.deniedForever) {
      throw StateError('La ubicación está bloqueada. Habilítala en Ajustes > Aplicaciones > WithYou > Permisos.');
    }
    return permission == LocationPermission.whileInUse || permission == LocationPermission.always;
  }

  Future<Map<String, dynamic>?> captureAndUpload() async {
    if (!await ensurePermission()) return null;
    final position = await Geolocator.getCurrentPosition(
      desiredAccuracy: LocationAccuracy.high,
    ).timeout(const Duration(seconds: 30));
    return api.postCheckpoint(position.latitude, position.longitude,
      accuracy: position.accuracy, network: 'mobile', movement: 'UNKNOWN');
  }
}
