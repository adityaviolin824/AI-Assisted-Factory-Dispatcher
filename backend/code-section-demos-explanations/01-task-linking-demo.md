# 01. Task linking walkthrough

Prepared: 13 October 2026.

Checked against the current Python modules: 19 October 2026. The linking examples still apply; unresolved follow-ups now produce provisional warnings for potentially affected tasks rather than automatically holding them.

The main code is [create_and_link_tasks.py](../order_processing_into_tasks/create_and_link_tasks.py). Message reading is in [read_chat_messages.py](../order_intake_from_chat/read_chat_messages.py), and item extraction is in [extract_items.py](../order_processing_into_tasks/extract_items.py).

## Part 1: Initial explanation

This walkthrough uses five realistic messages and stops after linking. The AI answers and saved records below are examples of the intended behaviour, not results from a run. The JSON examples show the relevant parts of the records rather than a complete processing file.

### 1. Sample TXT input

```text
R01 [10:15] Chen: Please allocate ORD-061 by April 5.
R02 [10:16] Ravi: Which workshop handled ORD-061 last time?
R03 [10:17] Mei: Please allocate ORD-045 as cheaply as possible.
R04 [10:18] Chen: For my ORD-061 allocation request, avoid QuickStitch.
R05 [10:19] Chen: Also, for that same allocation request, use April 6 instead of April 5.
```

There are three independent requests:

- Chen wants an allocation.
- Ravi asks a question.
- Mei wants a different allocation.

The last two messages change **Chen's existing request**.

### 2. Reading the file

Code gives each nonempty line an internal message ID and keeps the full original text.

| Label in the TXT | Internal message ID |
|---|---|
| R01 | L0001 |
| R02 | L0002 |
| R03 | L0003 |
| R04 | L0004 |
| R05 | L0005 |

For example, the first saved message looks like:

```json
{
  "message_id": "L0001",
  "raw_text": "R01 [10:15] Chen: Please allocate ORD-061 by April 5."
}
```

**Nothing has been interpreted yet.** This is just the original message with an ID.

### 3. Extracting the first three messages

The first batch contains the first three messages.

AI should recognise each as a new independent request. Here, "request" also includes an information question; it does not mean everything should be allocated.

Code checks the AI's answer, then saves the extracted pieces:

| Saved piece ID | Message | Kind | Original text |
|---|---|---|---|
| L0001:J1 | L0001 | request | R01 [10:15] Chen: Please allocate ORD-061 by April 5. |
| L0002:J1 | L0002 | request | R02 [10:16] Ravi: Which workshop handled ORD-061 last time? |
| L0003:J1 | L0003 | request | R03 [10:17] Mei: Please allocate ORD-045 as cheaply as possible. |

The first piece would look like this:

```json
{
  "item_id": "L0001:J1",
  "message_id": "L0001",
  "kind": "request",
  "excerpts": [
    "R01 [10:15] Chen: Please allocate ORD-061 by April 5."
  ]
}
```

An **item** simply means one request or follow-up found inside a message. `J1` means the first one found in that message. `excerpts` contains the copied original text; in this example each message has one item, so the full line is kept.

All pieces from the batch are saved before its messages are marked processed.

### 4. Creating the first three tasks

Each new request becomes a separate task.

| Task ID | What it represents |
|---|---|
| T:L0001:J1 | Chen's allocation request |
| T:L0002:J1 | Ravi's information question |
| T:L0003:J1 | Mei's allocation request |

Chen's task initially looks like:

```json
{
  "task_id": "T:L0001:J1",
  "item_ids": [
    "L0001:J1"
  ],
  "version": 1,
  "verified_version": null,
  "verified": null
}
```

In plain terms:

- `item_ids` lists the saved pieces belonging to this task.
- `version: 1` means this is its first version.
- `null` means verification has not happened yet.

**Chen's request and Ravi's question stay separate, even though both mention ORD-061.** The descriptions in the table explain their meaning to the reader; final intent verification still comes later.

Code also remembers which tasks mention each order:

```text
ORD-061 -> Chen's task, Ravi's task
ORD-045 -> Mei's task
```

These lists help find possible matches. They do not automatically join tasks.

### 5. Extracting Chen's first follow-up

The next batch contains messages L0004 and L0005. Earlier messages are provided as context, without being extracted again.

Ideally, AI marks both new messages as follow-ups.

The first is saved as:

```json
{
  "item_id": "L0004:J1",
  "message_id": "L0004",
  "kind": "follow_up",
  "excerpts": [
    "R04 [10:18] Chen: For my ORD-061 allocation request, avoid QuickStitch."
  ]
}
```

The item is classified as a follow-up; **its target task must still be identified**.

### 6. Finding possible tasks for that follow-up

Code builds a list using:

- Any earlier internal message ID explicitly mentioned.
- Any order number mentioned.
- The four most recently created or updated tasks.

L0004 mentions ORD-061. That brings in both Chen's task and Ravi's question. Recent tasks also bring in Mei's request.

After removing repeats, AI receives these possible matches and their original text:

| Possible task | Evidence AI can read |
|---|---|
| Chen's task | "Please allocate ORD-061 by April 5." |
| Ravi's task | "Which workshop handled ORD-061 last time?" |
| Mei's task | "Please allocate ORD-045 as cheaply as possible." |

The actual evidence includes the full saved lines, including their labels, times and sender names. The table shortens them for readability.

AI also receives the new follow-up:

> For my ORD-061 allocation request, avoid QuickStitch.

The important wording is **"my ORD-061 allocation request."** It supports connecting this message to Chen's allocation request.

Simply seeing ORD-061 would not be enough to choose between Chen's request and Ravi's question.

There is also a size check before asking AI. The current code allows at most **six candidate tasks** and **24,000 payload characters**. If there are no candidates, too many candidates, or too much evidence, the follow-up goes to review without a model call. Code does not shorten the list or cut the evidence, because that could remove the correct match.

### 7. AI proposes the link; code checks and saves it

An ideal AI answer would be:

```json
{
  "action": "attach",
  "task_ids": [
    "T:L0001:J1"
  ],
  "evidence_quote": "For my ORD-061 allocation request, avoid QuickStitch.",
  "reason": "This changes Chen's allocation request, rather than Ravi's question about previous work."
}
```

Here, `attach` means connect this follow-up to the listed task. `evidence_quote` is the exact wording offered to support that connection.

Code then checks:

- The chosen task came from the supplied list.
- The same task was not selected twice.
- The supporting quotation exists in the follow-up.
- If the quotation names an earlier internal message ID, the selected task actually belongs to that message.

These checks catch invented task IDs and quotations. **AI still has to understand the relationship correctly.**

Once accepted, code adds the follow-up's piece ID to Chen's task and increases its version:

```json
{
  "task_id": "T:L0001:J1",
  "item_ids": [
    "L0001:J1",
    "L0004:J1"
  ],
  "version": 2,
  "verified_version": null,
  "verified": null
}
```

The original request remains saved. The correction has been added to it.

Code also remembers that message L0004 now belongs to Chen's task and marks that task as recently updated.

Any earlier verification is cleared when new evidence is attached. In this example verification has not started, so both verification fields remain `null`.

### 8. Linking the second follow-up

Now we process:

```text
R05 [10:19] Chen: Also, for that same allocation request, use April 6 instead of April 5.
```

This message has **no order number**.

Code therefore uses the recent-task list to supply possible matches. Chen's task now includes both:

- His original allocation request.
- His correction excluding QuickStitch.

AI can read those together when deciding what "that same allocation request" refers to.

Ideally, it again chooses Chen's task, using this exact wording as its supporting quotation:

```text
Also, for that same allocation request, use April 6 instead of April 5.
```

After the same checks, Chen's task becomes:

```json
{
  "task_id": "T:L0001:J1",
  "item_ids": [
    "L0001:J1",
    "L0004:J1",
    "L0005:J1"
  ],
  "version": 3,
  "verified_version": null,
  "verified": null
}
```

Ravi's and Mei's tasks remain at version 1.

If the meaning of "that same request" were unclear, the follow-up would be saved for review instead of being attached.

That review preserves its original text, candidate task IDs and reason in `state["unresolved_links"]`. The candidates are possibilities, not confirmed connections. Later, code identifies tasks that this unresolved input might change. Those tasks still go through verification and allocation using their established evidence; their plan rows carry a **provisional warning**. A provisional recommendation still reserves tentative queue time. The unresolved follow-up itself reserves nothing.

### 9. What Chen's task evidence now looks like

The task contains IDs pointing to three saved pieces. When a later stage needs its evidence, code collects the original text from those pieces.

The resulting task evidence looks like:

```json
[
  {
    "message_id": "L0001",
    "excerpts": [
      "R01 [10:15] Chen: Please allocate ORD-061 by April 5."
    ]
  },
  {
    "message_id": "L0004",
    "excerpts": [
      "R04 [10:18] Chen: For my ORD-061 allocation request, avoid QuickStitch."
    ]
  },
  {
    "message_id": "L0005",
    "excerpts": [
      "R05 [10:19] Chen: Also, for that same allocation request, use April 6 instead of April 5."
    ]
  }
]
```

**That is task evidence: the original request and its connected follow-ups, kept in order.**

It preserves both April 5 and April 6. Linking has connected the messages; the later verification stage must determine which date is current.

### 10. How later stages see it

The shared processing record contains:

```text
Saved pieces:
    Each piece ID -> its source message and copied text

Saved tasks:
    Each task ID -> the piece IDs belonging to it
```

LangGraph carries this record during the run. Code also saves it in the run's `state.json` file.

Later verification follows Chen's three piece IDs and receives all three messages together. It should interpret the current requirements as:

```text
Order: ORD-061
Current deadline: April 6
Excluded workshop: QuickStitch
```

Those are the **expected later interpretation**, not fields already established by linking.

At the end of linking there are **three separate tasks**, with Chen's two corrections connected to his original request and all original evidence retained.

**End of Part 1: initial explanation.**

---

## Part 2: Comprehensive worked example

**The evidence grows by keeping the original request and adding each follow-up that belongs to it.** The task stores the IDs of those saved pieces. When another stage needs the evidence, code follows those IDs and collects the original text.

Here is a new example with **seven messages about one task**, plus an unrelated request. These are illustrative records, assuming AI proposes the correct links and code accepts them.

### 1. The conversation

```text
[14:00] Elena: Please allocate ORD-092 by November 20, 2026, at the lowest cost.
[14:01] Elena: For the allocation I just sent, avoid BudgetWorks.
[14:02] Marcus: Please allocate ORD-017 by November 18, 2026.
[14:03] Elena: For my ORD-092 request, use November 22, 2026, instead of November 20, 2026.
[14:04] Elena: For that same ORD-092 allocation, choose the fastest delivery instead of the cheapest option.
[14:05] Elena: Update to my ORD-092 request: BudgetWorks is allowed again.
[14:06] Elena: Confirming that same allocation: earliest delivery is my main priority.
[14:07] Elena: Final deadline for my ORD-092 request: November 21, 2026, replacing November 22, 2026.
```

Code gives these lines internal message IDs: `L0001` through `L0008`.

Notice that Elena changes her deadline twice, changes her preference, removes an earlier exclusion, and confirms her preference. We must preserve all of that history.

### 2. Save each extracted piece

In this example, every message contains one request or follow-up, so each produces one saved piece.

The first message becomes:

```json
{
  "item_id": "L0001:J1",
  "message_id": "L0001",
  "kind": "request",
  "excerpts": [
    "[14:00] Elena: Please allocate ORD-092 by November 20, 2026, at the lowest cost."
  ]
}
```

Her first follow-up becomes:

```json
{
  "item_id": "L0002:J1",
  "message_id": "L0002",
  "kind": "follow_up",
  "excerpts": [
    "[14:01] Elena: For the allocation I just sent, avoid BudgetWorks."
  ]
}
```

Here:

- `item_id` identifies the saved piece.
- `message_id` identifies its original line.
- `excerpts` contains copied original text.

**The text is saved before we decide which task the follow-up belongs to.**

The other messages are saved in the same form. Marcus's message is a new `request`; Elena's remaining messages are `follow_up` pieces.

### 3. The first request creates the task

Elena's first piece creates this task:

```json
{
  "task_id": "T:L0001:J1",
  "item_ids": [
    "L0001:J1"
  ],
  "version": 1,
  "verified_version": null,
  "verified": null
}
```

At this point, the task points to **one saved piece**.

If code collects its evidence now, it gets:

```json
[
  {
    "message_id": "L0001",
    "excerpts": [
      "[14:00] Elena: Please allocate ORD-092 by November 20, 2026, at the lowest cost."
    ]
  }
]
```

That is the initial task evidence.

### 4. Each accepted link adds another piece

For every follow-up, code finds possible tasks and gives AI their existing evidence alongside the new message.

AI proposes which task the follow-up belongs to. Code checks the proposed task IDs and supporting quotation. Once accepted, code appends the new piece ID to that task.

Here is **exactly how Elena's task grows**:

| Message processed | What happens | Elena's saved `item_ids` | Version |
|---|---|---|---:|
| `L0001` | Create Elena's task | `["L0001:J1"]` | 1 |
| `L0002` | Attach the BudgetWorks exclusion | `["L0001:J1", "L0002:J1"]` | 2 |
| `L0003` | Create Marcus's separate task | `["L0001:J1", "L0002:J1"]` | 2 |
| `L0004` | Attach the first deadline change | `["L0001:J1", "L0002:J1", "L0004:J1"]` | 3 |
| `L0005` | Attach the preference change | `["L0001:J1", "L0002:J1", "L0004:J1", "L0005:J1"]` | 4 |
| `L0006` | Attach permission to use BudgetWorks again | `["L0001:J1", "L0002:J1", "L0004:J1", "L0005:J1", "L0006:J1"]` | 5 |
| `L0007` | Attach the confirmation | `["L0001:J1", "L0002:J1", "L0004:J1", "L0005:J1", "L0006:J1", "L0007:J1"]` | 6 |
| `L0008` | Attach the final deadline change | `["L0001:J1", "L0002:J1", "L0004:J1", "L0005:J1", "L0006:J1", "L0007:J1", "L0008:J1"]` | 7 |

**Marcus's message never enters Elena's evidence.**

Also, the confirmation in `L0007` increases the version because it adds a new piece of evidence, even though it repeats the existing preference.

Each newly attached piece clears any earlier verification. In this walkthrough, verification has not started, so those fields remain `null`.

### 5. A closer look at one link

Consider this message:

```text
[14:06] Elena: Confirming that same allocation: earliest delivery is my main priority.
```

It contains no order ID.

Elena's task is among the recently updated tasks, so code supplies it as a possible match. AI can read its existing evidence, including:

```text
[14:04] Elena: For that same ORD-092 allocation, choose the fastest delivery instead of the cheapest option.
[14:05] Elena: Update to my ORD-092 request: BudgetWorks is allowed again.
```

An ideal link answer would be:

```json
{
  "action": "attach",
  "task_ids": [
    "T:L0001:J1"
  ],
  "evidence_quote": "Confirming that same allocation: earliest delivery is my main priority.",
  "reason": "Elena is confirming the delivery preference of her existing allocation request."
}
```

**`evidence_quote` supports this particular link.** It is different from the task's complete evidence collection.

After accepting the link, code adds `L0007:J1` to Elena's task. The complete original line remains stored in that piece's `excerpts`.

### 6. What the task finally stores

After all seven of Elena's messages are connected:

```json
{
  "task_id": "T:L0001:J1",
  "item_ids": [
    "L0001:J1",
    "L0002:J1",
    "L0004:J1",
    "L0005:J1",
    "L0006:J1",
    "L0007:J1",
    "L0008:J1"
  ],
  "version": 7,
  "verified_version": null,
  "verified": null
}
```

There is **no long evidence paragraph inside this task record**. It contains the IDs needed to retrieve the saved text.

The shared processing record contains two connected collections:

```text
items:
    Piece ID -> original message ID and copied text

tasks:
    Task ID -> list of piece IDs belonging to that task
```

Both are saved in the run's `state.json`. Linking saves the updated state after each processed item.

### 7. Exactly how code builds the complete evidence

Code reads Elena's `item_ids` in their saved order:

```text
L0001:J1 -> retrieve its message_id and excerpts
L0002:J1 -> retrieve its message_id and excerpts
L0004:J1 -> retrieve its message_id and excerpts
L0005:J1 -> retrieve its message_id and excerpts
L0006:J1 -> retrieve its message_id and excerpts
L0007:J1 -> retrieve its message_id and excerpts
L0008:J1 -> retrieve its message_id and excerpts
```

It places those retrieved values into one list:

```json
[
  {
    "message_id": "L0001",
    "excerpts": [
      "[14:00] Elena: Please allocate ORD-092 by November 20, 2026, at the lowest cost."
    ]
  },
  {
    "message_id": "L0002",
    "excerpts": [
      "[14:01] Elena: For the allocation I just sent, avoid BudgetWorks."
    ]
  },
  {
    "message_id": "L0004",
    "excerpts": [
      "[14:03] Elena: For my ORD-092 request, use November 22, 2026, instead of November 20, 2026."
    ]
  },
  {
    "message_id": "L0005",
    "excerpts": [
      "[14:04] Elena: For that same ORD-092 allocation, choose the fastest delivery instead of the cheapest option."
    ]
  },
  {
    "message_id": "L0006",
    "excerpts": [
      "[14:05] Elena: Update to my ORD-092 request: BudgetWorks is allowed again."
    ]
  },
  {
    "message_id": "L0007",
    "excerpts": [
      "[14:06] Elena: Confirming that same allocation: earliest delivery is my main priority."
    ]
  },
  {
    "message_id": "L0008",
    "excerpts": [
      "[14:07] Elena: Final deadline for my ORD-092 request: November 21, 2026, replacing November 22, 2026."
    ]
  }
]
```

**That list is the task evidence. Code assembles it from saved text; AI does not rewrite it into a summary.**

Nothing has been removed:

- November 20 remains, alongside both later deadline changes.
- "Lowest cost" remains, alongside the change to fastest delivery.
- "Avoid BudgetWorks" remains, alongside the later permission.

A later verification stage reads this whole collection and should establish:

| Current requirement | Supporting message |
|---|---|
| Order: `ORD-092` | Original request and later explicit references |
| Deadline: November 21, 2026 | `L0008` replaces the previous deadline |
| Preference: fastest delivery | `L0005`, confirmed by `L0007` |
| BudgetWorks is allowed | `L0006` replaces its earlier exclusion |

Those are the expected interpretations after verification. Linking itself only connects and preserves the messages.

The dates and order IDs in this example illustrate linking and verification. They are not a claim that either order is currently awaiting live dispatch. For example, the supplied CSV marks ORD-092 COMPLETE; the historical allocation experiment permits that with a warning, while a live status policy remains separate work.

### 8. Where the order ID fits

Code also builds this lookup from order IDs appearing in the saved evidence:

```json
{
  "ORD-092": [
    "T:L0001:J1"
  ],
  "ORD-017": [
    "T:L0003:J1"
  ]
}
```

So the connection is:

```text
ORD-092
    -> Elena's task
        -> its seven saved piece IDs
            -> the original text of those seven messages
```

The order lookup helps find the task. **The task's piece IDs are what determine its evidence.** That is why a follow-up without an order ID can still become part of the correct task once its link is accepted.
