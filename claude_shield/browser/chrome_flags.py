DEFAULT_FLAGS = [
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-sync",
]

ALLOWED_FLAGS = DEFAULT_FLAGS + ["--disable-extensions"]

PROHIBITED_FLAGS = [
    "--disable-blink-features=AutomationControlled",
    "--ignore-certificate-errors",
    "--disable-web-security",
    "--allow-running-insecure-content",
    "--user-agent",
    "--lang",
    "--timezone",
    "--use-gl",
    "--use-angle",
    "--remote-debugging-port", # Not allowed in this phase
    "--remote-allow-origins",
    "--headless" # Unless explicitly running tests
]

def sanitize_flags(flags: list) -> list:
    """Keep local file URLs and explicitly allowed browser flags."""
    sanitized = []
    for flag in flags:
        flag_base = flag.split('=')[0]
        if flag.startswith("file://") or flag in ALLOWED_FLAGS or flag_base in DEFAULT_FLAGS:
            sanitized.append(flag)
    return sanitized
