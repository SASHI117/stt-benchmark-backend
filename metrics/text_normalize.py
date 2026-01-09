import re

def normalize_text(text: str) -> str:
    """
    Normalize text for fair WER comparison.
    Works for English + Indian languages reasonably well.
    """
    if not text:
        return ""

    text = text.lower()

    # Remove punctuation (keep numbers & native chars)
    text = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)

    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text
