"""Template tags for smallstack-runbook.

Provides the RUNBOOK_BASE_TEMPLATE context variable to all templates.
"""

from django import template

from smallstack_runbook.conf import RUNBOOK_BASE_TEMPLATE

register = template.Library()


@register.simple_tag
def runbook_base_template():
    """Return the configured base template path."""
    return RUNBOOK_BASE_TEMPLATE
