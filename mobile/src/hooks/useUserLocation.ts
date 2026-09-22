import * as Location from "expo-location";
import { useEffect, useState } from "react";

// Centre of Asaba — used when location permission is refused or unavailable.
export const ASABA = { lat: 6.2003, lng: 6.7331 };

// Never leave the Home screen waiting forever (e.g. weak GPS indoors).
function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("timeout")), ms);
    promise.then(
      (v) => {
        clearTimeout(timer);
        resolve(v);
      },
      (e) => {
        clearTimeout(timer);
        reject(e);
      },
    );
  });
}

export interface UserLocation {
  lat: number;
  lng: number;
  label: string; // e.g. "Okpanam Road, Asaba"
  approximate: boolean; // true when we fell back to central Asaba
  ready: boolean;
}

export function useUserLocation(): UserLocation {
  const [loc, setLoc] = useState<UserLocation>({
    ...ASABA,
    label: "Asaba",
    approximate: true,
    ready: false,
  });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { status } = await withTimeout(Location.requestForegroundPermissionsAsync(), 20000);
        if (status !== "granted") {
          if (!cancelled) setLoc((l) => ({ ...l, ready: true }));
          return;
        }
        // A recent cached fix is instant; otherwise ask the GPS, but give up after 10 s.
        const pos =
          (await Location.getLastKnownPositionAsync({ maxAge: 5 * 60_000 }).catch(() => null)) ??
          (await withTimeout(
            Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced }),
            10000,
          ));
        const { latitude: lat, longitude: lng } = pos.coords;
        let label = "Your location";
        try {
          const [place] = await withTimeout(Location.reverseGeocodeAsync({ latitude: lat, longitude: lng }), 6000);
          if (place) {
            const street = place.street || place.name || place.district;
            const town = place.city || place.subregion || place.region;
            label = [street, town].filter(Boolean).join(", ") || label;
          }
        } catch {
          // keep generic label
        }
        if (!cancelled) setLoc({ lat, lng, label, approximate: false, ready: true });
      } catch {
        if (!cancelled) setLoc((l) => ({ ...l, ready: true }));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return loc;
}
