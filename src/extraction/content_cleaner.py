import re


BOILERPLATE_LINES = {
    "skip to main content",
    "home",
    "menu",
    "close",
    "search",
    "login",
    "log in",
    "sign in",
    "sign up",
}

def extract_emails(text: str) -> list[str]:
    """
    Extract public email addresses from webpage text.
    """

    if not text:
        return []

    pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"

    emails = re.findall(pattern, text)

    return sorted(set(emails))

def clean_text(text: str) -> str:
    """
    Clean webpage text before sending it to the LLM.
    """

    if not text:
        return ""

    # Normalize whitespace
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)

    # Split into individual lines
    lines = text.splitlines()

    cleaned_lines = []
    previous_line = ""

    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Remove common navigation/boilerplate
        if line.lower() in BOILERPLATE_LINES:
            continue

        # Remove duplicate consecutive lines
        if line.lower() == previous_line.lower():
            continue

        cleaned_lines.append(line)
        previous_line = line

    # Join the cleaned content
    cleaned_text = "\n".join(cleaned_lines)

    return cleaned_text.strip()

def optimize_context(
    pages: list[dict],
    max_chars_per_page: int = 6000,
    max_total_chars: int = 24000,
) -> str:
    """
    Combine cleaned page content while controlling context size.
    """

    sections = []
    seen_content = set()

    for page in pages:
        if page.get("error"):
            continue

        cleaned = clean_text(page.get("content", ""))

        if not cleaned:
            continue

        # Remove duplicate pages/content
        content_key = cleaned[:500].lower()

        if content_key in seen_content:
            continue

        seen_content.add(content_key)

        # Limit individual page size
        cleaned = cleaned[:max_chars_per_page]

        section = (
            f"SOURCE URL: {page['url']}\n"
            f"PAGE TITLE: {page['title']}\n\n"
            f"{cleaned}"
        )

        sections.append(section)

        # Stop when total context reaches the limit
        current_size = len("\n\n".join(sections))

        if current_size >= max_total_chars:
            break

    return "\n\n".join(sections)[:max_total_chars]