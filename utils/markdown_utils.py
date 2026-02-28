"""
Markdown utility functions for HiveBuzz
Provides functionality for rendering Markdown content safely
"""

import markdown
import bleach
from markupsafe import Markup
import logging

# Set up logging
logger = logging.getLogger(__name__)


def render_markdown(text):
    """
    Convert markdown text to safe HTML

    Args:
        text: Markdown text to convert

    Returns:
        Safe HTML as a Markup object
    """
    if not text:
        return ""

    try:
        # Convert markdown to HTML
        html = markdown.markdown(
            text,
            extensions=[
                "markdown.extensions.fenced_code",
                "markdown.extensions.tables",
                "markdown.extensions.nl2br",
            ],
        )

        # Clean the HTML to remove potentially harmful tags/attributes
        allowed_tags = [
            "p",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "hr",
            "br",
            "a",
            "abbr",
            "acronym",
            "b",
            "blockquote",
            "code",
            "em",
            "i",
            "li",
            "ol",
            "strong",
            "ul",
            "pre",
            "table",
            "thead",
            "tbody",
            "tr",
            "th",
            "td",
            "img",
            "span",
            "div",
            "strike",
            "del",
        ]
        allowed_attrs = {
            "a": ["href", "title", "rel"],
            "img": ["src", "alt", "title", "width", "height"],
            "*": ["class"],
        }

        clean_html = bleach.clean(
            html, tags=allowed_tags, attributes=allowed_attrs, strip=True
        )

        return Markup(clean_html)
    except Exception as e:
        logger.error(f"Error rendering markdown: {e}")
        return Markup(f"<p>Error rendering content: {str(e)}</p>")


def setup_markdown_filter(app):
    """
    Register markdown filter with Flask app

    Args:
        app: Flask application instance
    """
    app.template_filter("markdown")(render_markdown)
    logger.info("Markdown filter registered with Flask app")
