# Multi-line order correction

## Conversation example

Imagine someone says Yo we need to dispatch that sweater ASAP.
Next person says, oh which one? The new release? What's the order Id?
Then someone says, oh yeah its id-201 I believe
Then someone says, no no that's different, he's speaking about 205.

## Expected interpretation

- The conversation is about a dispatch request for a sweater.
- `205` is the latest proposed order reference, while `id-201` is an earlier, disputed reference. Neither becomes a verified order ID from conversation alone.
- The handoff preserves both statements and records the conflict in `doubts_to_clarify`.
- Ask the dispatcher to confirm the exact order ID before any allocation. Trusted order data must verify the confirmed ID.

## Why this example matters

Reading one line at a time can miss the correction. A window containing all four messages lets the parser connect the request, question, tentative ID, and correction while retaining their source lines.
