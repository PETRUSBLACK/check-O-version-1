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

/** A place on the map, broken up the way the backend stores a shop's location. */
export interface ReadPlace {
  lat: number;
  lng: number;
  street: string;
  city: string;
  state: string;
  /** Everything joined up, for showing back to the person. */
  label: string;
}

/**
 * Read where the phone is, once, on demand — for the shop owner standing in
 * their own shop tapping "Use my location".
 *
 * Deliberately not the hook below: that one fires on mount and quietly falls
 * back to the centre of Asaba, which is right for a shopper's "near me" list and
 * wrong here. A shop pinned to the middle of Asaba when it is actually on
 * Okpanam Road sends customers to the wrong place, so this returns null rather
 * than guessing, and the caller asks them to type the address instead.
 *
 * Throws nothing. `null` means "could not get a fix", with no explanation,
 * because there is nothing the vendor could do with one.
 */
export async function readCurrentPlace(): Promise<ReadPlace | null> {
  try {
    const { status } = await withTimeout(Location.requestForegroundPermissionsAsync(), 20000);
    if (status !== "granted") return null;

    const pos = await withTimeout(
      Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High }),
      15000,
    );
    const { latitude: lat, longitude: lng } = pos.coords;

    let street = "";
    let city = "";
    let state = "";
    try {
      const [place] = await withTimeout(
        Location.reverseGeocodeAsync({ latitude: lat, longitude: lng }),
        6000,
      );
      if (place) {
        street = place.street || place.name || place.district || "";
        city = place.city || place.subregion || "";
        state = place.region || "";
      }
    } catch {
      // Coordinates are the part that matters — the vendor can type the street.
    }

    return {
      lat,
      lng,
      street,
      city,
      state,
      label: [street, city, state].filter(Boolean).join(", "),
    };
  } catch {
    return null;
  }
}

/**
 * Turn an address the shop owner typed into a point on the map.
 *
 * This is the other half of `readCurrentPlace`, and the more important one. A
 * trader is far more likely to set her shop up at home in the evening than
 * standing behind her counter at midday — and if she taps "use my location"
 * from her sitting room, her shop is quietly pinned to her house and nobody
 * finds out until a customer knocks on the wrong door.
 *
 * So: she answers "where is your shop?" once, in words, and the app works out
 * the coordinates. Returns null when the address cannot be found, which is
 * common for an unnamed street — the caller then asks her to use her location
 * instead rather than pretending it knows.
 */
export async function findPlaceFromAddress(address: string): Promise<ReadPlace | null> {
  const typed = address.trim();
  if (typed.length < 5) return null;

  try {
    // Android refuses to geocode without location permission, even though this
    // never reads the device's own position.
    const { status } = await withTimeout(Location.requestForegroundPermissionsAsync(), 20000);
    if (status !== "granted") return null;

    // "12 Nnebisi Road" could be anywhere on earth. Nigeria is where Check-O is.
    const query = /nigeria/i.test(typed) ? typed : `${typed}, Nigeria`;
    const [hit] = await withTimeout(Location.geocodeAsync(query), 12000);
    if (!hit) return null;

    // Read it back as an address so the shop's location row carries a city and
    // state, and so she can see which place the app actually picked.
    let street = "";
    let city = "";
    let state = "";
    try {
      const [place] = await withTimeout(
        Location.reverseGeocodeAsync({ latitude: hit.latitude, longitude: hit.longitude }),
        6000,
      );
      if (place) {
        street = place.street || place.name || place.district || "";
        city = place.city || place.subregion || "";
        state = place.region || "";
      }
    } catch {
      // The coordinates are the part that matters.
    }

    return {
      lat: hit.latitude,
      lng: hit.longitude,
      street,
      city,
      state,
      label: [street, city, state].filter(Boolean).join(", ") || typed,
    };
  } catch {
    return null;
  }
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
