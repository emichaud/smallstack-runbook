"""Runbook models — Runbook, Section, and Document."""

from __future__ import annotations

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Runbook(models.Model):
    """A collection of sections and documents."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("runbook:runbook_detail", kwargs={"slug": self.slug})


class Section(models.Model):
    """Organizational grouping for documents within a runbook."""

    runbook = models.ForeignKey(
        Runbook,
        on_delete=models.CASCADE,
        related_name="sections",
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "name"]
        unique_together = [("runbook", "slug")]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("runbook:runbook_detail", kwargs={"slug": self.runbook.slug}) + f"#{self.slug}"


ALLOWED_EXTENSIONS: list[str] = ["md"]


class Document(models.Model):
    """A markdown document with versioning support."""

    FILE_TYPE_CHOICES = [
        ("md", "Markdown"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    section = models.ForeignKey(
        Section,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    file = models.FileField(
        upload_to="runbook/",
        validators=[FileExtensionValidator(allowed_extensions=ALLOWED_EXTENSIONS)],
    )
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, editable=False)
    description = models.TextField(blank=True)
    content_text = models.TextField(
        blank=True,
        editable=False,
        help_text="Extracted plaintext for full-text search.",
    )
    previous_version = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="next_versions",
    )
    is_current = models.BooleanField(default=True)
    version = models.IntegerField(default=1)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="runbook_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["is_current"]),
            models.Index(fields=["section", "is_current"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} (v{self.version})"

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.title)
        if self.file and not self.file_type:
            ext = self.file.name.rsplit(".", 1)[-1].lower()
            self.file_type = ext
        # Extract searchable text from file content on create/upload.
        # Callers that write file content directly (e.g. in-place editor)
        # pass skip_content_extract=True and set content_text themselves.
        if self.file and not kwargs.pop("skip_content_extract", False):
            self.content_text = self.extract_text()
        super().save(*args, **kwargs)

    def extract_text(self) -> str:
        """Read the markdown file and return plaintext for search indexing."""
        try:
            raw = self.file.read().decode("utf-8")
            self.file.seek(0)
            return strip_frontmatter(raw)
        except Exception:
            return ""

    def get_absolute_url(self) -> str:
        return reverse("runbook:document_detail", kwargs={"pk": self.pk})

    def get_version_chain(self) -> list[Document]:
        """Walk backward through previous_version to build full chain."""
        chain: list[Document] = [self]
        current = self
        while current.previous_version:
            current = current.previous_version
            chain.append(current)
        return chain

    def create_new_version(self, *, file, uploaded_by, description: str = "") -> Document:
        """Create a new version of this document, marking self as not current.

        Returns the newly created Document.
        """
        new_doc = Document(
            title=self.title,
            slug=self.slug,
            section=self.section,
            file=file,
            description=description,
            previous_version=self,
            version=self.version + 1,
            uploaded_by=uploaded_by,
        )
        new_doc.save()
        self.is_current = False
        self.save(update_fields=["is_current"])
        return new_doc

    @property
    def is_markdown(self) -> bool:
        return self.file_type == "md"

    @property
    def is_pdf(self) -> bool:
        return self.file_type == "pdf"

    @property
    def is_docx(self) -> bool:
        return self.file_type in ("docx", "doc")


def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter (--- delimited) from markdown text."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text.strip()
