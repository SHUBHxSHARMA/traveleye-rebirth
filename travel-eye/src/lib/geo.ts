const EARTH_RADIUS_M = 6371000;

export function haversineDistanceMeters(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return EARTH_RADIUS_M * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export function formatDistance(meters: number): string {
  if (meters < 1000) return `${Math.round(meters)} m`;
  return `${(meters / 1000).toFixed(1)} km`;
}

export interface GeoPosition {
  latitude: number;
  longitude: number;
  accuracy?: number;
}

export function watchPosition(
  onUpdate: (position: GeoPosition) => void,
  onError: (message: string) => void,
): () => void {
  if (!navigator.geolocation) {
    onError("Geolocation is not supported on this device.");
    return () => undefined;
  }

  const id = navigator.geolocation.watchPosition(
    (pos) => {
      onUpdate({
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
        accuracy: pos.coords.accuracy,
      });
    },
    (err) => {
      if (err.code === err.PERMISSION_DENIED) {
        onError("Location is off for this site. You can still scan a photograph or read the list.");
        return;
      }
      onError("Location could not be found. Scanning and reading still work.");
    },
    { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 },
  );

  return () => navigator.geolocation.clearWatch(id);
}
