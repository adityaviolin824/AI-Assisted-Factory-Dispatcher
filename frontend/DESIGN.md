# Design plan

Written with the `frontend-design` skill on 21 October 2026. Aditya delegated frontend design decisions the same day ("Don't ask me for clarifications when it comes to frontend"), so this plan is recorded rather than sent for approval. It covers both core interfaces, Chat (`/operations`) and Dispatcher (`/dispatcher`), and the secondary introduction (`/`).

## Subject, audience and job

- **Subject:** a garment factory deciding which of eight sewing workshops (W1 QuickStitch to W8 FreshStart) should make each batch of an order such as ORD-045.
- **Audience:** factory staff who write requests in a shared chat, and the dispatcher who checks Python's answers and decides.
- **Primary job:** let the dispatcher see, for each request, the person's original words beside Python's answers to the three questions in the [Factory Primer](../reference-documents/Factory_Primer.md): can the workshop make the batch, can it take it given its capacity and queue, and is it allowed to.

## First pass

### Colour

Named after denim, the factory's most familiar cloth: indigo-dyed cotton, undyed ecru, gold topstitching thread and the red selvedge edge.

| Name | Hex | Role |
|---|---|---|
| Raw indigo | `#121A30` | Page background |
| Washed indigo | `#1B2542` | Raised surfaces: header bar, panels, table heads, composer |
| Seam | `#34426A` | Dividing lines and table rules (not text, not control borders) |
| Ecru | `#EDE6D3` | Main text and the primary button fill |
| Topstitch gold | `#E3A73E` | Thread lines that mark state, keyboard focus, active filter |
| Selvedge red | `#EE7564` | Needs attention, late, blocked, errors |

Supporting tones: faded denim `#A9B2CA` for secondary text, and a stronger control border derived from it so inputs pass 3:1 against the background. Measured contrast: ecru on raw indigo 13.9:1, faded denim 8.2:1, gold 8.1:1, red 6.1:1; the lowest text pair, red on washed indigo, is 5.3:1.

### Type

Two clearly different families, each tied to a source of truth in this project:

- **Literata** (serif, optical sizes): only for words a person wrote: chat messages and quoted source messages in Dispatcher. 18px in the chat, 16px in quotes, line height 1.6.
- **Archivo** (grotesque with a width axis): everything the system labels or Python calculates. Normal width (100) for interface text and tables, with tabular figures so columns of days and costs line up. Expanded width (125) at weight 700 for page titles, section headings and the mode switch, like the stencilled markings on cartons and bale labels.

Scale (px, from the classic typographic scale): 13 small details, 14 tables, 16 body, 18 chat text, 21 section headings, 28 page titles, 40 introduction headline. Sentence case everywhere; no all-caps labels.

### Layout

Left-aligned throughout; numbers right-aligned in tables. Panels are separated by tone and seam lines, not by floating cards.

App shell, every page. The mode switch is two links in one control, always in the same place:

```
+--------------------------------------------------------------------------+
| Workshop dispatch     [  Chat  |  Dispatcher  ]                 About    |
+--------------------------------------------------------------------------+
```

Chat: a transcript, not bubbles, because it is one shared factory log read by many people. The processing panel sits beside it so the start-run path is Send, then Process conversation, then Open in Dispatcher.

```
+----------------------------------------------+---------------------------+
| Chat                                         | Process conversation      |
| 42 messages, last at 14:32                   | Snapshot of 42 messages   |
|----------------------------------------------| [Create snapshot]         |
| 09:02  Chen                         L0028    | Processing calls paid AI  |
|        Can someone place ORD-107? 2000       | models and takes minutes. |
|        cardigans, due Mar 16.                | [Process conversation]    |
| 09:05  Priya                        L0029    |                           |
|        ...                                   | Runs from this chat       |
|----------------------------------------------|  19 Oct 11:25             |
| Your name [Chen      ]                       |  Open in Dispatcher       |
| [ message ...                     ] [Send]   |                           |
+----------------------------------------------+---------------------------+
```

Dispatcher: the worklist and the evidence panel side by side, the workshop queues below. Below 1100px the panel moves under the worklist.

```
+--------------------------------------------------------------------------+
| Dispatcher   [run 2026-10-19_11-25-25    v] [Refresh]                    |
| Plan before the dispatcher's review, planned from 2026-04-01             |
+-------------------------------------------+------------------------------+
| [All 181] [Needs attention 165] [Sugg. 4] | T:L0028:J1                   |
| Row        Order    Outcome    Workshop   | Needs clarification          |
| : T:L0028  ORD-107  Suggested  W2   3.50  | reason                       |
| | T:L0029  ORD-045  Needs rev. -    -     | Chen, 09:59                  |
| ...                                       |   "Can someone place ..."    |
|                                           | Request facts                |
|                                           | Workshop comparison          |
+-------------------------------------------+------------------------------+
| Workshops and queues                                                     |
+--------------------------------------------------------------------------+
```

Introduction: one worked example instead of a marketing hero. A real chat message (Literata) beside the three questions Python answers for it, then the three-step flow (a real sequence, so it is numbered), links to Chat and Dispatcher, and what is implemented versus pending.

### Principles

1. **Thread marks state.** Gold thread lines carry one meaning: a dashed line is basting (provisional, unsaved or not yet final), a solid line is topstitching (final, saved). Red marks what needs attention. Every state also has a text label, so colour and line style are never the only signal.
2. **Two voices.** Serif means a person said it; grotesque means the system labelled or Python calculated it. The dispatcher can tell at a glance which words came from the chat.
3. **Rows stay rows.** Tables keep dense, readable rows with tabular figures. Nothing is chopped into cards.
4. **Quiet everywhere else.** One accent family (gold), one alarm colour (red), no gradients, glows, textures or decorative icons. Motion only answers an action, such as a sent message settling into the transcript, and is removed under reduced motion.

## Second pass: review against the brief and generic defaults

Working through a similar prompt ("dark dashboard for a logistics team") gives a slate navy page, white text, a bright single accent, rounded cards and a monospace face for IDs. Parts of the first draft were close to that, so they changed:

| First draft | Why it read as a default | Revision |
|---|---|---|
| Gold-filled primary buttons on navy | Navy and gold fills are the stock "premium dashboard" look, and gold would then mean both "click here" and "provisional" | Primary buttons are ecru (undyed cotton) with indigo text; gold is reserved for thread lines, focus and the active filter |
| A subtle diagonal twill texture on the page | Decorative and built from gradients, which the brief forbids | Removed; the denim reference lives in the palette and the stitch lines |
| Rounded chat bubbles, left and right | Consumer messenger pattern; it implies a private two-person chat and wastes width | A left-aligned transcript with time, name and message ID, like a shared log |
| A monospace face for IDs like ORD-045 and L0028 | Listed as a generic tell, and a third family | Archivo with tabular figures |
| Pill-shaped status chips in several colours | Decorative pills and a rainbow of states | Outcome text with a thread mark at the row's left edge: dashed gold, solid gold or red |
| A page background near `#0F172A` | Matches a common framework's slate colour, the default dark navy | Raw indigo `#121A30`, a dyed-cloth blue with ecru text instead of white |

What stays deliberate rather than default: the dark indigo base (asked for by the brief and grounded in denim), sentence-case headings without eyebrow labels, and buttons named for what they do ("Send", "Process conversation", "Open in Dispatcher") with no arrows.
