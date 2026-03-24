"""Forms for Runbook."""

from __future__ import annotations

from django import forms

from .models import Document, Runbook, Section


def _apply_text_class(form: forms.BaseForm) -> None:
    """Add vTextField CSS class to all text inputs and textareas."""
    for field in form.fields.values():
        if isinstance(field.widget, (forms.TextInput, forms.Textarea)):
            field.widget.attrs.setdefault("class", "vTextField")


class RunbookForm(forms.ModelForm):
    class Meta:
        model = Runbook
        fields = ["name", "description", "icon"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_text_class(self)


class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ["name", "description", "icon", "order"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_text_class(self)


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["title", "section", "file", "description"]

    def __init__(self, *args, **kwargs):
        self.runbook: Runbook | None = kwargs.pop("runbook", None)
        super().__init__(*args, **kwargs)
        if self.runbook:
            self.fields["section"].queryset = Section.objects.filter(runbook=self.runbook)
        # Restrict file upload to markdown only
        self.fields["file"].widget.attrs["accept"] = ".md"
        _apply_text_class(self)


class DocumentCreateFromScratchForm(forms.ModelForm):
    """Create a new markdown document from scratch (no file upload)."""

    class Meta:
        model = Document
        fields = ["title", "section", "description"]

    def __init__(self, *args, **kwargs):
        self.runbook: Runbook | None = kwargs.pop("runbook", None)
        super().__init__(*args, **kwargs)
        if self.runbook:
            self.fields["section"].queryset = Section.objects.filter(runbook=self.runbook)
        _apply_text_class(self)


class NewVersionForm(forms.ModelForm):
    """Upload a new version of an existing document."""

    class Meta:
        model = Document
        fields = ["file", "description"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["file"].widget.attrs["accept"] = ".md"
        _apply_text_class(self)
