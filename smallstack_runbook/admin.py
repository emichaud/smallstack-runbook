"""Admin registration for Runbook models."""

from django.contrib import admin

from .models import Document, Runbook, Section


@admin.register(Runbook)
class RunbookAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created_at", "updated_at"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ["name", "runbook", "slug", "order", "created_at"]
    list_filter = ["runbook"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "section", "file_type", "version", "is_current", "uploaded_by", "updated_at"]
    list_filter = ["file_type", "is_current", "section__runbook", "section"]
    search_fields = ["title", "description"]
    raw_id_fields = ["previous_version", "uploaded_by"]
