# translate_message.py: a chat message written in Chinese -> the English that the Chat page's Send saves.
#
# Send flow: POST /chat/messages (fastapi_routes/chat.py) -> translate_to_english when the message has
#            Chinese characters and [translation] is on -> the English is saved, so intake and
#            processing read English.
# Reads:     the [translation] settings in config.toml, and the downloaded model in its model_folder.
# Writes:    nothing. The model runs on this computer, so no message leaves it and nothing is paid.
import re
from functools import cache

from order_processing_into_tasks.settings_and_data import BACKEND_DIR, CONFIG

TRANSLATION_ON = CONFIG["translation"]["enabled"]
MODEL_FOLDER = BACKEND_DIR / CONFIG["translation"]["model_folder"]
# The model card's Chinese-to-English instruction, before the message: "Translate the following text
# into English; output only the translation, with no explanation."
PROMPT = "将以下文本翻译成英语,注意只需要输出翻译后的结果,不要额外解释:\n\n"
# Chinese characters, the same range as the Chat page's Mandarin check.
CHINESE = re.compile(r"[一-鿿]")
# Order and workshop IDs, such as ORD-045 and W6, which the English must keep exactly.
IDENTIFIER = re.compile(r"ORD-\d+|W\d+")


def needs_translation(text):
    """True when translation is switched on and the text contains Chinese characters."""
    return TRANSLATION_ON and CHINESE.search(text) is not None


def translate_to_english(text):
    """Return the English translation of text.

    Raises ValueError when the English lost, changed or added an order or workshop ID, so a mistyped
    ID is never saved for processing. Quantities, dates and cancellations are not checked.
    """
    english = run_model(text).strip()
    if set(IDENTIFIER.findall(english)) != set(IDENTIFIER.findall(text)):
        raise ValueError(f"Not sent: the English translation did not keep the order and workshop IDs exactly "
                         f"({english}). Check the IDs, or write the message in English.")
    return english


def run_model(text):
    """Translate text with greedy decoding, so the same message always gives the same English."""
    from mlx_lm import generate  # imported only when needed: it adds about 1.3 s to the API's start
    model, tokenizer = load_model()
    prompt = tokenizer.apply_chat_template([{"role": "user", "content": PROMPT + text}], add_generation_prompt=True)
    return generate(model, tokenizer, prompt=prompt, max_tokens=4096)  # the model card's limit


@cache
def load_model():
    """Load the model and its tokenizer once, at the first translation, and keep them in memory."""
    from mlx_lm import load
    return load(str(MODEL_FOLDER))
