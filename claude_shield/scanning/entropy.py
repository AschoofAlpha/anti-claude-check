import math
from collections import Counter

def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq = Counter(s)
    length = len(s)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())

def is_high_entropy(s: str, min_length: int = 20, threshold: float = 4.5) -> bool:
    """
    Checks if a string has high entropy, suggesting it might be a generated secret.
    Should be combined with pattern or context matching to avoid false positives.
    """
    if len(s) < min_length:
        return False
    return shannon_entropy(s) > threshold
