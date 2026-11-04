"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { errorText, listWorkshops } from "@/lib/api";
import { HOME_PAGE, nameProblem, ROLE_LABELS, type Role, signIn } from "@/lib/identity";
import type { Workshop } from "@/lib/types";

const ROLE_HINTS: Record<Role, string> = {
  team: "Sends requests in the shared chat.",
  dispatcher: "Turns the chat into workshop plans, reviews and approves them, and can read the chat.",
  workshop: "Reports your workshop's current capacity and availability for the next dispatch run.",
};

// Name and role for this browser tab. A demo label, not an account: there is no password.
export default function SignInPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [role, setRole] = useState<Role | null>(null);
  // The workshops are read only when the Workshop role is chosen, for its list.
  const [workshops, setWorkshops] = useState<Workshop[] | null>(null);
  const [workshopId, setWorkshopId] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);
  // The form's problem is shown only after a first attempt, not while the person is still typing.
  const [tried, setTried] = useState(false);

  // What still stops Enter, in the order the form is filled in; null when nothing does.
  function formProblem() {
    const problemWithName = nameProblem(name);
    if (problemWithName) {
      return problemWithName;
    }
    if (!role) {
      return "Choose a role.";
    }
    if (role === "workshop" && !workshopId) {
      return "Choose your workshop.";
    }
    return null;
  }
  const problem = formProblem();

  function chooseRole(option: Role) {
    setRole(option);
    setLoadError(null);
    if (option === "workshop" && workshops === null) {
      listWorkshops().then(setWorkshops, (caught) => {
        // Un-choose Workshop, so choosing it again reads the list again (a sleeping backend can fail once).
        setRole((current) => (current === "workshop" ? null : current));
        setLoadError(`Could not load the workshops; choose Workshop again to retry. ${errorText(caught)}`);
      });
    }
  }

  function enter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTried(true);
    if (problem || !role) {
      return;
    }
    const workshop = workshops?.find((option) => option.workshop_id === workshopId);
    signIn(role === "workshop" && workshop
      ? { name, role, workshopId: workshop.workshop_id, workshopName: workshop.name }
      : { name, role });
    router.push(HOME_PAGE[role]);
  }

  return (
    <div className="sign-in">
      <h1>Sign in</h1>
      <p className="muted">
        Your name appears on the messages and reports you send. There is no password: anyone can choose any role in this
        demo.
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
              <input type="radio" name="role" checked={role === option} onChange={() => chooseRole(option)} />
              <span>
                <strong>{ROLE_LABELS[option]}</strong>
                <span className="hint">{ROLE_HINTS[option]}</span>
              </span>
            </label>
          ))}
        </fieldset>
        {role === "workshop" && (
          <label className="name-field">
            Your workshop
            <select value={workshopId} onChange={(event) => setWorkshopId(event.target.value)} disabled={!workshops}>
              <option value="">{workshops ? "Choose a workshop" : "Loading workshops..."}</option>
              {workshops?.map((workshop) => (
                <option key={workshop.workshop_id} value={workshop.workshop_id}>
                  {workshop.workshop_id} {workshop.name}
                </option>
              ))}
            </select>
          </label>
        )}
        {loadError && (
          <p className="error" role="alert">
            {loadError}
          </p>
        )}
        {tried && problem && (
          <p className="error" role="alert">
            {problem}
          </p>
        )}
        <button type="submit" className="primary">
          Enter
        </button>
      </form>
    </div>
  );
}
