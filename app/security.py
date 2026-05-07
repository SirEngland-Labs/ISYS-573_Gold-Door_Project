"""Security middleware — input sanitization, rate limiting, output filtering."""

import time
import re
from collections import defaultdict

# Rate limiting: max requests per phone per hour
RATE_LIMIT = 20
RATE_WINDOW = 3600  # 1 hour in seconds

# Track request counts per phone number
_request_counts: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(phone: str) -> bool:
    """Check if a phone number has exceeded the rate limit.

    Returns True if allowed, False if rate limited.
    """
    now = time.time()
    # Clean old entries
    _request_counts[phone] = [t for t in _request_counts[phone] if now - t < RATE_WINDOW]

    if len(_request_counts[phone]) >= RATE_LIMIT:
        return False

    _request_counts[phone].append(now)
    return True


# Patterns that suggest prompt injection attempts
INJECTION_PATTERNS = [
    r"ignore (all |your |previous )?instructions",
    r"ignore (all |your |previous )?prompts",
    r"you are now",
    r"new instructions",
    r"system prompt",
    r"reveal your",
    r"show me your (prompt|instructions|rules)",
    r"act as",
    r"pretend (to be|you are)",
    r"jailbreak",
    r"DAN mode",
    r"developer mode",
    r"<\|system\|>",
    r"\[INST\]",
    r"<<SYS>>",
]

_compiled_patterns = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def sanitize_input(text: str) -> str:
    """Sanitize user input — strip injection attempts.

    Returns cleaned text. If injection detected, returns a safe replacement.
    """
    for pattern in _compiled_patterns:
        if pattern.search(text):
            return "[Message contained disallowed content]"

    # Strip any XML/HTML-like tags that could confuse the LLM
    text = re.sub(r'<[^>]+>', '', text)

    # Limit message length
    if len(text) > 2000:
        text = text[:2000]

    return text.strip()


# Patterns to catch in agent output before sending to user
OUTPUT_BLOCKLIST = [
    r"/Users/",
    r"\.env",
    r"api[_-]?key",
    r"MINIMAX_",
    r"TWILIO_",
    r"sk-[a-zA-Z0-9]+",
    r"system prompt",
    r"you are a",
    r"your instructions",
]

_compiled_output_patterns = [re.compile(p, re.IGNORECASE) for p in OUTPUT_BLOCKLIST]


def filter_output(text: str) -> str:
    """Filter agent output to prevent information leakage.

    Returns cleaned text or a safe replacement if leakage detected.
    """
    for pattern in _compiled_output_patterns:
        if pattern.search(text):
            return "I'm here to help with restaurant reservations. How can I assist you?"

    return text
