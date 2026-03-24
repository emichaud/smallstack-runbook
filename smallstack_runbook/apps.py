"""Runbook app configuration."""

from django.apps import AppConfig


class RunbookConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "smallstack_runbook"
    label = "runbook"
    verbose_name = "Runbook"
    help_content_dir = "content"
    help_section_slug = "runbook"

    def ready(self):
        try:
            from apps.smallstack.navigation import nav
        except ImportError:
            return

        icon = (
            '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">'
            '<path d="M6 2a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6H6z'
            "m7 1.5L18.5 9H13V3.5zM8 12h8v2H8v-2zm0 4h8v2H8v-2z"
            '"/></svg>'
        )
        nav.register(
            section="main",
            label="Runbook",
            url_name="runbook:dashboard",
            icon_svg=icon,
            staff_required=True,
            order=5,
        )
