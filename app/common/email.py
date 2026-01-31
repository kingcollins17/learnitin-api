import logging
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

# Define the templates directory relative to this file
# This file is in app/common/, so we go up one level to app/ and then into templates/
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def get_jinja_env() -> Environment:
    """
    Create and return a Jinja2 Environment configured for the project.
    """
    if not TEMPLATE_DIR.exists():
        logger.warning(f"Template directory does not exist: {TEMPLATE_DIR}")

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Add common globals
    from datetime import datetime

    env.globals["now"] = datetime.now
    from app.common.config import settings

    env.globals["app_logo"] = settings.APP_LOGO

    return env


_env = get_jinja_env()


def render_template(
    template_name: str, context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Render a Jinja2 template with the given context.

    Args:
        template_name: The name of the template file (e.g., 'welcome.html')
        context: A dictionary of variables to pass to the template

    Returns:
        The rendered template string
    """
    if context is None:
        context = {}

    try:
        template = _env.get_template(template_name)
        return template.render(**context)
    except Exception as e:
        logger.error(f"Error rendering template {template_name}: {str(e)}")
        raise
