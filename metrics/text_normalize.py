import re
import unicodedata

_NUKTAS = "\u093c\u09bc\u0a3c\u0abc\u0b3c\u0cbc"   # Devanagari, Bengali, Gurmukhi, Gujarati, Odia, Kannada
_INDIC_VARIANTS = {ord(c): None for c in _NUKTAS} | {0x0901: 0x0902}   # chandrabindu -> anusvara


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
    # Spelling variants that are the same word: nukta (फ़/फ, NFC already splits
    # precomposed nukta letters into base + U+093C) and Devanagari chandrabindu
    # vs anusvara (गेहूँ/गेहूं). ASR systems pick either form freely, so scoring
    # them as substitutions penalises correct transcripts.
    text = text.translate(_INDIC_VARIANTS)

    kept = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat[0] in ("P", "S") or cat == "Cf":
            # punctuation (incl. danda), symbols, zero-width joiners
            continue
        else:
            kept.append(ch)

    return re.sub(r"\s+", " ", "".join(kept)).strip()
