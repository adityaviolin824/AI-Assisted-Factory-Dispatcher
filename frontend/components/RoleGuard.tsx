"use client";

import { redirect } from "next/navigation";
import { HOME_PAGE, type Role, useIdentity } from "@/lib/identity";

type Props = { allow: Role[]; children: React.ReactNode };

// Shows a page only to the roles allowed on it: before sign-in it opens the sign-in page, and someone
// signed in with another role goes to their own page. Nothing is drawn, and the page reads nothing from
// the backend, until this tab's sign-in has been read. This sorts the demo's users; it is not security,
// because the backend does not check who is asking.
export default function RoleGuard({ allow, children }: Props) {
  const identity = useIdentity();
  if (identity === undefined) {
    return null;
  }
  if (identity === null) {
    redirect("/sign-in");
  }
  if (!allow.includes(identity.role)) {
    redirect(HOME_PAGE[identity.role]);
  }
  return children;
}
