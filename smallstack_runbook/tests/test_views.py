"""Tests for Runbook views."""

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from smallstack_runbook.models import Document, Runbook, Section

User = get_user_model()


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(username="staff", password="pass", is_staff=True)


@pytest.fixture
def staff_client(staff_user):
    client = Client()
    client.login(username="staff", password="pass")
    return client


@pytest.fixture
def runbook(db):
    return Runbook.objects.create(name="Test Runbook", slug="test-runbook")


@pytest.fixture
def section(runbook):
    return Section.objects.create(name="General", runbook=runbook)


@pytest.fixture
def document(section, staff_user):
    return Document.objects.create(
        title="Test Doc",
        file=SimpleUploadedFile("test.md", b"# Test\n\nHello world."),
        section=section,
        uploaded_by=staff_user,
    )


@pytest.mark.django_db
class TestDashboard:
    def test_dashboard_loads(self, staff_client):
        resp = staff_client.get("/runbook/")
        assert resp.status_code == 200

    def test_requires_staff(self, client):
        resp = client.get("/runbook/")
        assert resp.status_code == 302  # redirect to login


@pytest.mark.django_db
class TestDocumentDetail:
    def test_renders_markdown(self, staff_client, document):
        resp = staff_client.get(f"/runbook/documents/{document.pk}/")
        assert resp.status_code == 200
        assert "Hello world" in resp.content.decode()


@pytest.mark.django_db
class TestSearch:
    def test_search_by_title(self, staff_client, document):
        resp = staff_client.get("/runbook/search/?q=Test+Doc")
        assert resp.status_code == 200
        assert "Test Doc" in resp.content.decode()

    def test_search_by_content(self, staff_client, document):
        resp = staff_client.get("/runbook/search/?q=Hello+world")
        assert resp.status_code == 200
        assert "Test Doc" in resp.content.decode()

    def test_search_empty_query(self, staff_client):
        resp = staff_client.get("/runbook/search/?q=")
        assert resp.status_code == 200


@pytest.mark.django_db
class TestEditContent:
    def test_get_loads_editor(self, staff_client, document):
        resp = staff_client.get(f"/runbook/documents/{document.pk}/edit-content/")
        assert resp.status_code == 200
        assert "# Test" in resp.content.decode()

    def test_post_saves_content(self, staff_client, document):
        resp = staff_client.post(
            f"/runbook/documents/{document.pk}/edit-content/",
            {"content": "# Updated\n\nNew body."},
        )
        assert resp.status_code == 302
        document.refresh_from_db()
        assert "New body" in document.content_text

    def test_post_updates_file(self, staff_client, document):
        staff_client.post(
            f"/runbook/documents/{document.pk}/edit-content/",
            {"content": "# Changed"},
        )
        document.refresh_from_db()
        document.file.open("r")
        content = document.file.read()
        document.file.close()
        assert "Changed" in content


@pytest.mark.django_db
class TestNewVersion:
    def test_upload_new_version(self, staff_client, document):
        new_file = SimpleUploadedFile("v2.md", b"# Version 2")
        resp = staff_client.post(
            f"/runbook/documents/{document.pk}/new-version/",
            {"file": new_file, "description": "Updated"},
        )
        assert resp.status_code == 302

        document.refresh_from_db()
        assert document.is_current is False

        v2 = Document.objects.get(previous_version=document)
        assert v2.version == 2
        assert v2.is_current is True


@pytest.mark.django_db
class TestStatDetail:
    def test_runbooks_stat(self, staff_client, runbook):
        resp = staff_client.get("/runbook/stats/runbooks/")
        assert resp.status_code == 200
        assert "Test Runbook" in resp.content.decode()

    def test_types_stat(self, staff_client, document):
        resp = staff_client.get("/runbook/stats/types/")
        assert resp.status_code == 200
        assert ".md" in resp.content.decode()

    def test_unknown_stat_returns_empty(self, staff_client):
        resp = staff_client.get("/runbook/stats/nonexistent/")
        assert resp.status_code == 200
