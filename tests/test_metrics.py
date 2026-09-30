import pytest

from metrics.text_normalize import normalize_text
from metrics.wer import accuracy, word_error_rate


def test_normalize_strips_punctuation_and_case():
    assert normalize_text("Hello, World!  How's it?") == "hello world hows it"


@pytest.mark.parametrize(
    "text",
    ["किसान भाई", "నమస్కారం రైతు", "வணக்கம் விவசாயி"],
)
def test_normalize_keeps_indic_vowel_signs(text):
    # Regression: the old [^\w\s] regex deleted matras/viramas (Mn/Mc).
    assert normalize_text(text) == text


def test_normalize_drops_danda():
    assert normalize_text("फसल अच्छी है।") == "फसल अच्छी है"


def test_nukta_and_chandrabindu_variants_are_the_same_word():
    # Seen from IndicConformer on TTS audio: a correct transcript that spells
    # गेहूं/फसल as गेहूँ/फ़सल must not be scored as two substitutions.
    ref = "किसान भाई इस साल गेहूं की फसल अच्छी हुई है"
    hyp = "किसान भाई इस साल गेहूँ की फ़सल अच्छी हुई है"
    assert word_error_rate(ref, hyp) == 0.0
    assert word_error_rate("\u092b\u093c\u0938\u0932", "\u095e\u0938\u0932") == 0.0   # decomposed vs precomposed nukta letter


def test_telugu_arasunna_is_not_merged():
    # Telugu chandrabindu (U+0C01) and anusvara (U+0C02) are different sounds.
    assert normalize_text("\u0c05\u0c01") != normalize_text("\u0c05\u0c02")


def test_wrong_hindi_hypothesis_is_penalised():
    # Before the fix this returned 0.0 because both sides collapsed to "कसन भई".
    assert word_error_rate("किसान भाई", "कसान भई") == 1.0


@pytest.mark.parametrize(
    "ref, hyp, expected",
    [
        ("the cat sat", "the cat sat", 0.0),
        ("the cat sat", "the cat", 1 / 3),        # deletion
        ("the cat sat", "the big cat sat", 1 / 3),  # insertion
        ("the cat sat", "the dog sat", 1 / 3),     # substitution
        ("a b", "c d e f", 2.0),                  # WER can exceed 1
    ],
)
def test_wer_edit_operations(ref, hyp, expected):
    assert word_error_rate(ref, hyp) == pytest.approx(expected, abs=1e-4)


def test_wer_empty_reference():
    assert word_error_rate("", "") == 0.0
    assert word_error_rate("", "noise") == 1.0


def test_accuracy_is_clamped_at_zero():
    assert accuracy("a b", "c d e f") == 0.0
    assert accuracy("a b", "a b") == 100.0
