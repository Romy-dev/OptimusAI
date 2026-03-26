"""Prompt management — loads and formats templates for agents."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


class PromptManager:
    """Loads and renders prompt templates from the filesystem."""

    def __init__(self, templates_dir: str | None = None):
        if templates_dir is None:
            # Default to app/prompts/templates
            templates_dir = str(Path(__file__).parent / "templates")
        
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(),
            # Use default Undefined so that {{ var | default("fallback") }} works
            # when a variable is not provided by the caller.
        )

    def render(self, template_name: str, **kwargs: Any) -> str:
        """Render a template with provided variables."""
        template = self.env.get_template(template_name)
        return template.render(**kwargs)

    def get_prompt(self, agent_name: str, prompt_type: str = "system", **kwargs: Any) -> str:
        """Helper to get a specific prompt for an agent (e.g., 'copywriter/system')."""
        template_name = f"{agent_name}/{prompt_type}.j2"
        return self.render(template_name, **kwargs)


# Singleton
_prompt_manager: PromptManager | None = None


def get_prompt_manager() -> PromptManager:
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
