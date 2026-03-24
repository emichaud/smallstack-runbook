"""Package-level settings with sensible defaults."""

from django.conf import settings

RUNBOOK_BASE_TEMPLATE = getattr(settings, "RUNBOOK_BASE_TEMPLATE", "base.html")
RUNBOOK_STAFF_REQUIRED = getattr(settings, "RUNBOOK_STAFF_REQUIRED", True)
RUNBOOK_URL_PREFIX = getattr(settings, "RUNBOOK_URL_PREFIX", "runbook/")
