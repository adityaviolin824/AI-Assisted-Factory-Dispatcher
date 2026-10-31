"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ROLE_LABELS, signOut, useIdentity } from "@/lib/identity";

// Who is signed in in this tab, with Switch user, or a Sign in link before anyone has signed in.
export default function SignInStatus() {
  const router = useRouter();
  const identity = useIdentity();

  function switchUser() {
    signOut();
    router.push("/sign-in");
  }

  // The server cannot read this tab's sign-in, so nothing is drawn until the browser has.
  if (identity === undefined) {
    return null;
  }
  if (identity === null) {
    return (
      <Link href="/sign-in" className="sign-in-link">
        Sign in
      </Link>
    );
  }
  return (
    <span className="signed-in">
      <strong>{identity.name}</strong>
      {ROLE_LABELS[identity.role]}
      <button type="button" className="link-button" onClick={switchUser}>
        Switch user
      </button>
    </span>
  );
}
