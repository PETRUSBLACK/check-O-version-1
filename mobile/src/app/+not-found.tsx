import { Redirect } from "expo-router";

import { useAuth } from "../store/auth";

/**
 * Where the app lands when the address it is on no longer exists.
 *
 * Found on 2026-10-16: a brand-new shopper finished "Create account", the app
 * signed them in, and the screen they were on (/register) stopped existing —
 * it only exists for signed-out people — so expo-router showed its built-in
 * "nothing here" page with a back arrow. The account was fine; only the
 * landing was wrong.
 *
 * The rule is simple and has no way to loop: signed in, go Home (the shopper's
 * tabs or the seller's orders, whichever the guards in _layout allow);
 * signed out, go to sign in.
 */
export default function NotFound() {
  const status = useAuth((s) => s.status);
  const role = useAuth((s) => s.user?.role);

  if (status !== "signedIn") return <Redirect href="/sign-in" />;
  return <Redirect href={role === "vendor" ? "/(vendor)" : "/"} />;
}
