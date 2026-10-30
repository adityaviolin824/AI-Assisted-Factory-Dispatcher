# transcribe_speech.py: one short voice recording -> its text, for the Chat page's Record button.
#
# Voice flow: the Chat page records -> POST /chat/transcriptions (fastapi_routes/chat.py) -> transcribe
#             -> the text goes into the message box, where the worker checks and edits it before Send.
# Reads:      the [voice] settings in config.toml, and the workshop and product names in the CSV files.
# Writes:     nothing. The recording goes to OpenAI's transcription model and is not saved here.
from openai import OpenAI

from order_processing_into_tasks.settings_and_data import CONFIG, ORDER_INDEX, WORKSHOP_INDEX, WORKSHOP_NAMES

VOICE_MODEL = CONFIG["voice"]["model"]
VOICE_LANGUAGES = CONFIG["voice"]["languages"]
# Words to spell as the records do: the "ORD-" of every order ID, then the workshop IDs and names and
# the product names. They are hints only; a misheard ID is left for the worker to correct.
KEYWORDS = ["ORD-", *WORKSHOP_INDEX, *WORKSHOP_NAMES, *sorted({row["product"] for row in ORDER_INDEX.values()})]


def transcribe(recording, file_name):
    """Return the text of one recording, in the language spoken (no translation).

    recording is the audio file's bytes; the extension of file_name, such as .webm or .mp4, tells the
    model its format. OPENAI_API_KEY must be set; a failed call raises the OpenAI error.
    """
    client = OpenAI(max_retries=0)
    result = client.audio.transcriptions.create(model=VOICE_MODEL, file=(file_name, recording),
                                                languages=VOICE_LANGUAGES, keywords=KEYWORDS)
    return result.text
