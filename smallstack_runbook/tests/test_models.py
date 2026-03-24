"""Tests for Runbook models."""

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from smallstack_runbook.models import Document, Runbook, Section, strip_frontmatter

User = get_user_model()


@pytest.fixture
def runbook(db):
    return Runbook.objects.create(name="Test Runbook")


@pytest.fixture
def section(runbook):
    return Section.objects.create(name="Test Section", runbook=runbook)


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="testpass")


# -- Runbook ------------------------------------------------------------------


@pytest.mark.django_db
class TestRunbook:
    def test_auto_slug(self):
        rb = Runbook.objects.create(name="My Runbook")
        assert rb.slug == "my-runbook"

    def test_str(self):
        rb = Runbook(name="Operations")
        assert str(rb) == "Operations"

    def test_get_absolute_url(self):
        rb = Runbook(name="Ops", slug="ops")
        assert "/ops/" in rb.get_absolute_url()


# -- Section ------------------------------------------------------------------


@pytest.mark.django_db
class TestSection:
    def test_auto_slug(self, runbook):
        section = Section.objects.create(name="Incident Response", runbook=runbook)
        assert section.slug == "incident-response"

    def test_str(self):
        section = Section(name="Operations")
        assert str(section) == "Operations"

    def test_ordering(self, runbook):
        s1 = Section.objects.create(name="B Section", order=1, runbook=runbook)
        s2 = Section.objects.create(name="A Section", order=0, runbook=runbook)
        sections = list(Section.objects.filter(runbook=runbook))
        assert sections[0] == s2
        assert sections[1] == s1


# -- Document -----------------------------------------------------------------


@pytest.mark.django_db
class TestDocument:
    def test_auto_slug_and_file_type(self, user):
        doc = Document(
            title="My Document",
            file=SimpleUploadedFile("test.md", b"# Hello"),
            uploaded_by=user,
        )
        doc.save()
        assert doc.slug == "my-document"
        assert doc.file_type == "md"

    def test_str(self):
        doc = Document(title="Test", version=3)
        assert str(doc) == "Test (v3)"

    def test_is_markdown(self):
        doc = Document(title="Test", file_type="md")
        assert doc.is_markdown
        assert not doc.is_pdf
        assert not doc.is_docx

    def test_is_pdf(self):
        doc = Document(title="Test", file_type="pdf")
        assert doc.is_pdf
        assert not doc.is_markdown

    def test_version_chain(self, user, section):
        v1 = Document.objects.create(
            title="Doc",
            file=SimpleUploadedFile("doc.md", b"v1"),
            section=section,
            uploaded_by=user,
            version=1,
        )
        v1.is_current = False
        v1.save(skip_content_extract=True)

        v2 = Document.objects.create(
            title="Doc",
            file=SimpleUploadedFile("doc.md", b"v2"),
            section=section,
            uploaded_by=user,
            version=2,
            previous_version=v1,
        )

        chain = v2.get_version_chain()
        assert len(chain) == 2
        assert chain[0] == v2
        assert chain[1] == v1


# -- Content extraction -------------------------------------------------------


@pytest.mark.django_db
class TestContentExtraction:
    def test_extract_text_on_save(self, user):
        content = b"# Hello World\n\nSome body text."
        doc = Document(
            title="Extract Test",
            file=SimpleUploadedFile("test.md", content),
            uploaded_by=user,
        )
        doc.save()
        assert "Hello World" in doc.content_text
        assert "Some body text" in doc.content_text

    def test_extract_strips_frontmatter(self, user):
        content = b"---\ntitle: Test\n---\n# Real Content\n\nBody here."
        doc = Document(
            title="FM Test",
            file=SimpleUploadedFile("fm.md", content),
            uploaded_by=user,
        )
        doc.save()
        assert "title: Test" not in doc.content_text
        assert "Real Content" in doc.content_text

    def test_skip_content_extract(self, user):
        doc = Document.objects.create(
            title="Skip Test",
            file=SimpleUploadedFile("skip.md", b"# Original"),
            uploaded_by=user,
        )
        original_text = doc.content_text
        doc.content_text = "manually set"
        doc.save(update_fields=["content_text"], skip_content_extract=True)
        doc.refresh_from_db()
        assert doc.content_text == "manually set"


# -- Version creation ---------------------------------------------------------


@pytest.mark.django_db
class TestCreateNewVersion:
    def test_creates_version_and_marks_old_not_current(self, user, section):
        v1 = Document.objects.create(
            title="Versioned",
            file=SimpleUploadedFile("v1.md", b"# V1"),
            section=section,
            uploaded_by=user,
        )
        assert v1.is_current is True

        new_file = SimpleUploadedFile("v2.md", b"# V2")
        v2 = v1.create_new_version(file=new_file, uploaded_by=user, description="Updated")

        v1.refresh_from_db()
        assert v1.is_current is False
        assert v2.is_current is True
        assert v2.version == 2
        assert v2.previous_version == v1
        assert v2.title == v1.title
        assert v2.slug == v1.slug
        assert v2.description == "Updated"

    def test_version_chain_after_multiple_versions(self, user, section):
        v1 = Document.objects.create(
            title="Chain",
            file=SimpleUploadedFile("v1.md", b"# V1"),
            section=section,
            uploaded_by=user,
        )
        v2 = v1.create_new_version(
            file=SimpleUploadedFile("v2.md", b"# V2"),
            uploaded_by=user,
        )
        v3 = v2.create_new_version(
            file=SimpleUploadedFile("v3.md", b"# V3"),
            uploaded_by=user,
        )

        chain = v3.get_version_chain()
        assert len(chain) == 3
        assert chain[0].version == 3
        assert chain[2].version == 1


# -- strip_frontmatter --------------------------------------------------------


class TestStripFrontmatter:
    def test_strips_yaml_frontmatter(self):
        text = "---\ntitle: Hello\ntags: [a, b]\n---\n# Content\n\nBody."
        assert strip_frontmatter(text) == "# Content\n\nBody."

    def test_no_frontmatter(self):
        text = "# Just Content\n\nBody."
        assert strip_frontmatter(text) == "# Just Content\n\nBody."

    def test_empty_string(self):
        assert strip_frontmatter("") == ""

    def test_incomplete_frontmatter(self):
        text = "---\ntitle: Hello\nNo closing delimiter"
        # Only one --- so it's not valid frontmatter — returned as-is
        assert strip_frontmatter(text) == text.strip()

    def test_frontmatter_with_trailing_whitespace(self):
        text = "---\nkey: val\n---\n\n  # Content  \n\n"
        assert strip_frontmatter(text) == "# Content"
