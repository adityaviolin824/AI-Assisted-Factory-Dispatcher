# read_chat_messages.py: the first step of the pipeline. It turns the chat input into the message
# list that processing reads.
#
# Pipeline: read_chat_messages -> order_processing_into_tasks (extract items, tasks, verification)
# Came from: notebook 05, Section 2 (read_messages, copied unchanged).
# Reads:     a chat TXT file, one message per line, such as "R01 [07:53] Chen: ...". This is the
#            format of data/dispatch_requests.txt and of the mock chat's "Export for notebook".
# Writes:    nothing.
#
# Later, other inputs (for example voice transcribed to text) will be turned into the same
# message list here, so processing never needs to know where a message came from.


def read_messages(path):
    """Read the chat file and give every nonempty line a message ID: L0001, L0002, ...

    Returns a list of {"message_id": "L0001", "raw_text": ...} in file order. One message can hold
    several jobs; this function only reads and numbers the lines. Later steps use the IDs to track
    which messages are done and where each quote came from.
    """
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    print(f"[Read] {len(lines)} nonempty lines from {path.name}, numbered L0001, L0002, ...")
    return [
        {"message_id": f"L{number:04d}", "raw_text": line}
        for number, line in enumerate(lines, 1)
    ]
