"""Context processors for smallstack-runbook."""

from .conf import RUNBOOK_BASE_TEMPLATE


def runbook_settings(request):
    """Add runbook settings to template context."""
    return {
        "RUNBOOK_BASE_TEMPLATE": RUNBOOK_BASE_TEMPLATE,
    }
