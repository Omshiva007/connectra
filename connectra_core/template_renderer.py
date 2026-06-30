"""Render saved template body text into email-safe HTML."""

import html
import re

_HTML_TAG_RE = re.compile(r"</?[a-z][\s\S]*>", re.IGNORECASE)


def _looks_like_html(body: str) -> bool:
    """Return True when the body already contains HTML tags."""
    return bool(_HTML_TAG_RE.search(body))


def render_template_body(body: str) -> str:
    """Return HTML that preserves plain-text spacing or existing HTML markup."""
    body = (body or "").strip()
    if not body:
        return ""

    if _looks_like_html(body):
        return body

    escaped = html.escape(body)
    paragraphs = [
        paragraph.replace("\n", "<br>")
        for paragraph in re.split(r"\n\s*\n", escaped)
        if paragraph.strip()
    ]
    return "".join(f"<p>{paragraph}</p>" for paragraph in paragraphs)


def render_template_html(plain_body: str = "", html_body: str = "", body: str = "") -> str:
    """Return the HTML version of a template using explicit HTML when present."""
    selected_html = (html_body or "").strip()
    if selected_html:
        return selected_html
    return render_template_body(plain_body or body)


def render_template_preview(
    name: str,
    subject: str,
    body: str = "",
    plain_body: str = "",
    html_body: str = "",
) -> str:
    """Render the full preview HTML shown before sending a template."""
    title = html.escape(name or "(untitled)")
    safe_subject = html.escape(subject or "")
    rendered_body = render_template_html(plain_body, html_body, body)

    return (
        f"<h3>{title}</h3>"
        f"<p><b>Subject:</b> {safe_subject}</p>"
        "<hr/>"
        f"{rendered_body}"
    )
