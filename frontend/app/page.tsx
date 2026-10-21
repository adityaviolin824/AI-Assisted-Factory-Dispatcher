import Link from "next/link";

// The introduction: one real request and Python's answers to the Factory Primer's three questions,
// copied from saved run 2026-10-19_11-25-25 (row T:L0011:J1), then the flow and what works today.
export default function IntroductionPage() {
  return (
    <div className="intro">
      <h1>Decide where each batch is sewn</h1>
      <p className="lede">
        Staff ask for work in a shared chat. An AI reads each request, Python checks all eight workshops, and the
        dispatcher makes the final choice.
      </p>

      <section className="example" aria-label="Worked example">
        <div>
          <h2>A request from the chat</h2>
          <p className="muted">R09, 08:33, Boss</p>
          <blockquote className="spoken">
            ORD-045 — 150 vests for Cotton Club, due Apr 09. It&apos;s urgent. Cost doesn&apos;t matter, just the
            fastest turnaround.
          </blockquote>
        </div>
        <div>
          <h2>What Python worked out</h2>
          <dl className="questions">
            <dt>Can the workshop make the batch?</dt>
            <dd>ORD-045 is 150 tops. W4 Little Loom makes only accessories, so it is out.</dd>
            <dt>Can it take the batch, given its capacity and queue?</dt>
            <dd>
              W3 BudgetWorks would deliver after 9 April, so it is out. W6 Nimble Needle delivers in 3.18 of the 8
              days available: 1.00 day of queue, 1.15 of production, 0.03 of expected rework and 1 pickup day.
            </dd>
            <dt>Is it allowed to take it?</dt>
            <dd>W7 OldMill is suspended, so it is out.</dd>
          </dl>
          <p className="run-state">
            <strong>Suggested: W6 Nimble Needle</strong>, first for the fastest delivery. The dispatcher can approve
            it or choose another workshop.
          </p>
        </div>
      </section>

      <h2>How a request moves</h2>
      <ol className="steps">
        <li>
          <span>
            <strong>Send it in Chat.</strong> Sending saves the message. Nothing is processed yet.
          </span>
        </li>
        <li>
          <span>
            <strong>Process the conversation.</strong> The AI turns messages into requests. Python checks each
            workshop, ranks them and reserves queue time.
          </span>
        </li>
        <li>
          <span>
            <strong>Review it in Dispatcher.</strong> Check each request against its original message, change
            what needs changing and approve the plan once.
          </span>
        </li>
      </ol>
      <p className="toolbar">
        <Link href="/operations">Open Chat</Link>
        <Link href="/dispatcher">Open Dispatcher</Link>
      </p>

      <h2>What works today</h2>
      <ul className="status-list">
        <li>Dispatcher reads saved runs: worklist, original messages, request facts, workshop comparison and queues.</li>
        <li>In progress: sending and processing chat messages, and the dispatcher&apos;s choices with one final approval.</li>
        <li>Not built yet: reallocation, sending work to workshops and sign-in.</li>
      </ul>
    </div>
  );
}
