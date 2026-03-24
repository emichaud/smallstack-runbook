"""Explorer registration for Runbook models (optional SmallStack integration)."""

try:
    from django.contrib import admin

    from apps.explorer.registry import explorer

    from .models import Document, Runbook, Section

    class RunbookExplorerAdmin(admin.ModelAdmin):
        list_display = ["name", "slug", "created_at", "updated_at"]
        explorer_fields = ["name", "slug", "description", "icon"]
        explorer_group = "Runbook"

    class SectionExplorerAdmin(admin.ModelAdmin):
        list_display = ["name", "runbook", "slug", "order", "created_at"]
        explorer_fields = ["name", "runbook", "slug", "description", "icon", "order"]
        explorer_group = "Runbook"

    class DocumentExplorerAdmin(admin.ModelAdmin):
        list_display = ["title", "section", "file_type", "version", "is_current", "updated_at"]
        explorer_fields = ["title", "slug", "section", "file", "file_type", "description", "version", "is_current"]
        explorer_group = "Runbook"
        explorer_readonly = True

    explorer.register(Runbook, RunbookExplorerAdmin)
    explorer.register(Section, SectionExplorerAdmin)
    explorer.register(Document, DocumentExplorerAdmin)

except ImportError:
    pass  # Explorer app not available — skip registration
