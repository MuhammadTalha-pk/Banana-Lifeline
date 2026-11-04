import 'package:geocoding/geocoding.dart';
import 'package:geolocator/geolocator.dart';

import '../errors/app_exception.dart';
import '../models/models.dart';

class LocationService {
  Future<GeoData> current({
    String? farmName,
    String? plotSector,
    String? row,
    String? plantNumber,
  }) async {
    if (!await Geolocator.isLocationServiceEnabled()) {
      throw const AppException('GPS is disabled.');
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied) {
      throw const AppException('Location permission denied.');
    }
    if (permission == LocationPermission.deniedForever) {
      throw const AppException('Location permission permanently denied.');
    }

    final position = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
    );

    String? address;
    try {
      final places = await placemarkFromCoordinates(position.latitude, position.longitude);
      if (places.isNotEmpty) {
        final p = places.first;
        address = [p.name, p.locality, p.subAdministrativeArea, p.administrativeArea, p.country]
            .where((e) => (e ?? '').trim().isNotEmpty)
            .cast<String>()
            .join(', ');
      }
    } catch (_) {
      address = null;
    }

    return GeoData(
      latitude: position.latitude,
      longitude: position.longitude,
      address: address,
      farmName: farmName,
      plotSector: plotSector,
      row: row,
      plantNumber: plantNumber,
    );
  }
}
