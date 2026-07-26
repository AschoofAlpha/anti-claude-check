# Allowed and Prohibited Chrome Flags

ALLOWED_FLAGS = [
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-sync",
    "--disable-background-networking",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-client-side-phishing-detection",
    "--disable-component-update",
    "--password-store=basic",
    "--use-mock-keychain",
    "--disable-features=Translate",
    "--metrics-recording-only",
    "--safebrowsing-disable-auto-update",
    "--disable-domain-reliability",
    "--disable-ipc-flooding-protection",
    "--disable-popup-blocking",
    "--disable-prompt-on-repost"
]

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
    """Removes prohibited flags and returns the sanitized list."""
    sanitized = []
    for flag in flags:
        flag_base = flag.split('=')[0]
        if flag not in PROHIBITED_FLAGS and flag_base not in PROHIBITED_FLAGS:
            sanitized.append(flag)
    return sanitized
