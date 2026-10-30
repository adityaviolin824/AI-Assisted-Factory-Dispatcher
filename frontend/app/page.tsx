import Link from "next/link";

// The introduction: recorded results, one real request and Python's answers to the Factory Primer's three
// questions, copied from saved run 2026-10-19_11-25-25 (row T:L0011:J1), then the flow, what works today,
// how the results were measured and the team.
// The figures are copied from backend/eval_harness/results/harness_results_2026-10-15.md (normal replay)
// and the root README's "Testing and recorded results"; nothing here is calculated.
export default function IntroductionPage() {
  return (
    <div className="intro">
      <h1>Dispatching at your fingertips</h1>
      <p className="lede">
        Staff post requests in a shared chat. An AI reads each request, Python checks all eight workshops, and the
        dispatcher makes the final choice.
      </p>

      <ul className="metrics" aria-label="Recorded results">
        <li>
          <strong className="figure">2 of 120</strong>
          <span>Late batches, versus 41 with a random choice</span>
        </li>
        <li>
          <strong className="figure">8.1 days</strong>
          <span>Mean delivery time, versus 21.5 with a random choice</span>
        </li>
        <li>
          <strong className="figure">100 cases</strong>
          <span>Chat test set, hand-reviewed by our team</span>
        </li>
      </ul>
      <p className="metrics-note">
        Recorded results from a replay of 120 historical orders and a separate 100-case chat test set. Our policy
        costs about 3% more than a random choice. <a href="#how-we-measured">See how we measured</a>
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
            <dd>ORD-045 is 150 vests, which count as tops. W4 Little Loom makes only accessories, so it is out.</dd>
            <dt>Can it take the batch, given its capacity and queue?</dt>
            <dd>
              W3 BudgetWorks would deliver after 9 April, so it is out. W6 Nimble Needle delivers in 3.18 of the 8
              days available: 1.00 day of queue, 1.15 of production, 0.03 of expected rework and 1 pickup day.
            </dd>
            <dt>Is it allowed to take it?</dt>
            <dd>W7 OldMill is suspended, so it is out.</dd>
          </dl>
          <p className="run-state">
            <strong>Suggested: W6 Nimble Needle</strong>, ranked first for the fastest delivery. The dispatcher can
            approve it or choose another workshop.
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
            <strong>Start the dispatch workflow.</strong> The AI turns messages into requests. Python checks each
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
      <p className="motto">Measure twice. Dispatch once.</p>

      <h2>What works today</h2>
      <ul className="status-list">
        <li>
          Chat saves messages, captures a fixed copy of the conversation and sends it for processing. Processing calls
          paid AI models, so the server must be started with permission.
        </li>
        <li>
          Dispatcher shows each run&apos;s worklist, original messages, request facts, workshop comparison and queues.
          Choices stay on the page until one Approve all, which keeps them fixed and plans the other work around them.
          Check workshop options and Review again also work.
        </li>
        <li>Not built yet: sending work to workshops and sign-in.</li>
      </ul>

      <section className="measured" aria-labelledby="how-we-measured">
        <h2 id="how-we-measured">How we measured</h2>
        <p>
          The scheduling rules were replayed on 120 historical orders with the supplied simulator and compared with
          choosing a random eligible workshop. These are the simulator&apos;s six measures, unchanged.
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Normal historical replay</th>
                <th className="number">Mean days</th>
                <th className="number">p90 days</th>
                <th className="number">Late</th>
                <th className="number">Defective</th>
                <th className="number">Cost</th>
                <th className="number">Maximum workshop share</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Random eligible workshop</td>
                <td className="number">21.5</td>
                <td className="number">45.6</td>
                <td className="number">34%</td>
                <td className="number">4%</td>
                <td className="number">111,780</td>
                <td className="number">23%</td>
              </tr>
              <tr>
                <td>Our policy: reduce lateness</td>
                <td className="number">8.1</td>
                <td className="number">13.7</td>
                <td className="number">2%</td>
                <td className="number">6%</td>
                <td className="number">115,360</td>
                <td className="number">25%</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p>
          Our policy delivered sooner and had fewer late batches, but cost more and had more defective batches. The
          replay measures the scheduling rules, not how well the AI reads a conversation.
        </p>
        <p>
          The chat test set has 100 synthetic cases in 149 messages: 85 that should be allocated and 15 deliberate
          exceptions, such as a cancelled order. Three team members shared the hand review of every case before any
          run. In three fresh runs, 73 to 81 of the 85 were allocated correctly before the dispatcher&apos;s review, and
          the cancelled order was wrongly given a workshop each time. A Python check added on 24 October now sends it
          to the dispatcher instead, which a replay of the third run&apos;s saved answers confirmed. The full reports
          are in the{" "}
          <a href="https://github.com/adityaviolin824/AI-Assisted-Factory-Dispatcher#testing-and-recorded-results">
            project README
          </a>
          .
        </p>
      </section>

      <p className="credits">
        Brought to you by Cheng Shiqi, Song Zhuoyan, Zhang Chang, Zhang Hongyi and Aditya Bhattacharyya.
      </p>
    </div>
  );
}
