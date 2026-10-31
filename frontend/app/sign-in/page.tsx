"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { HOME_PAGE, nameProblem, ROLE_LABELS, type Role, signIn } from "@/lib/identity";

const ROLE_HINTS: Record<Role, string> = {
  team: "Sends requests in the shared chat.",
  dispatcher: "Turns the chat into workshop plans, reviews and approves them, and can read the chat.",
};

// Name and role for this browser tab. A demo label, not an account: there is no password.
export default function SignInPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [role, setRole] = useState<Role | null>(null);
  // The name's problem is shown only after a first attempt, not while the person is still typing.
  const [tried, setTried] = useState(false);
  const problem = nameProblem(name);

  function enter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTried(true);
    if (problem || !role) {
      return;
    }
    signIn({ name, role });
    router.push(HOME_PAGE[role]);
  }

  return (
    <div className="sign-in">
      <h1>Sign in</h1>
      <p className="muted">
        Your name appears on the messages you send. There is no password: anyone can choose either role in this demo.
      </p>
      <form onSubmit={enter} noValidate>
        <label className="name-field">
          Your name
          <input value={name} onChange={(event) => setName(event.target.value)} autoComplete="name" autoFocus />
        </label>
        <fieldset>
          <legend>Role</legend>
          {(Object.keys(ROLE_LABELS) as Role[]).map((option) => (
            <label key={option} className="role-option">
              <input type="radio" name="role" checked={role === option} onChange={() => setRole(option)} />
              <span>
                <strong>{ROLE_LABELS[option]}</strong>
                <span className="hint">{ROLE_HINTS[option]}</span>
              </span>
            </label>
          ))}
        </fieldset>
        {tried && (problem || !role) && (
          <p className="error" role="alert">
            {problem ?? "Choose a role."}
          </p>
        )}
        <button type="submit" className="primary">
          Enter
        </button>
      </form>
    </div>
  );
}
