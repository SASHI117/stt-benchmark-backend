import re
import unicodedata


def normalize_text(text: str) -> str:
    """
    Normalize text for fair WER comparison across English and Indic scripts.

    Punctuation and symbols are removed by Unicode category rather than with
    ``[^\\w\\s]``: Python's ``\\w`` does not match combining marks (categories
    Mn/Mc), so a regex-based strip deletes Devanagari/Telugu/Tamil vowel signs
    and viramas and silently merges distinct words.
    """
    if not text:
        return ""

    text = unicodedata.normalize("NFC", text).casefold()

    kept = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat[0] in ("P", "S") or cat == "Cf":
            # punctuation (incl. danda), symbols, zero-width joiners
            continue
        else:
            kept.append(ch)

    return re.sub(r"\s+", " ", "".join(kept)).strip()
