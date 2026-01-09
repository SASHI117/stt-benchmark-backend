from metrics.text_normalize import normalize_text


def word_error_rate(reference: str, hypothesis: str) -> float:
    """
    Compute Word Error Rate (WER)
    """
    ref_words = normalize_text(reference).split()
    hyp_words = normalize_text(hypothesis).split()

    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    # Levenshtein distance (DP)
    dp = [[0] * (len(hyp_words) + 1) for _ in range(len(ref_words) + 1)]

    for i in range(len(ref_words) + 1):
        dp[i][0] = i
    for j in range(len(hyp_words) + 1):
        dp[0][j] = j

    for i in range(1, len(ref_words) + 1):
        for j in range(1, len(hyp_words) + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(
                    dp[i - 1][j],     # deletion
                    dp[i][j - 1],     # insertion
                    dp[i - 1][j - 1]  # substitution
                ) + 1

    wer = dp[len(ref_words)][len(hyp_words)] / len(ref_words)
    return round(wer, 4)


def accuracy(reference: str, hypothesis: str) -> float:
    """
    Accuracy = (1 - WER) * 100
    """
    wer = word_error_rate(reference, hypothesis)
    acc = (1 - wer) * 100
    return round(max(acc, 0.0), 2)
