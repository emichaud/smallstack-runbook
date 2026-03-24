"""URL configuration for the Runbook app."""

from django.urls import path

from . import views

app_name = "runbook"

urlpatterns = [
    # Dashboard (runbook list)
    path("", views.RunbookDashboardView.as_view(), name="dashboard"),
    # Stat detail (htmx)
    path("stats/<str:stat_type>/", views.DashboardStatDetailView.as_view(), name="stat_detail"),
    # Search
    path("search/", views.SearchView.as_view(), name="search"),
    path("search-results/", views.SearchResultsView.as_view(), name="search_results"),
    # All documents (cross-runbook)
    path("documents/", views.DocumentListView.as_view(), name="document_list"),
    # Bulk download (must be before <slug:slug>/ to avoid slug capture)
    path("download/", views.DownloadZipView.as_view(), name="download_zip"),
    # Runbook CRUD
    path("new/", views.RunbookCreateView.as_view(), name="runbook_create"),
    path("<slug:slug>/", views.RunbookDetailView.as_view(), name="runbook_detail"),
    path("<slug:slug>/edit/", views.RunbookUpdateView.as_view(), name="runbook_update"),
    path("<slug:slug>/delete/", views.RunbookDeleteView.as_view(), name="runbook_delete"),
    # Sections (scoped to runbook)
    path("<slug:slug>/sections/new/", views.SectionCreateView.as_view(), name="section_create"),
    path("sections/<int:pk>/edit/", views.SectionUpdateView.as_view(), name="section_update"),
    path("sections/<int:pk>/delete/", views.SectionDeleteView.as_view(), name="section_delete"),
    # Documents (scoped to runbook for create)
    path("<slug:slug>/documents/new/", views.DocumentCreateView.as_view(), name="document_create"),
    path("<slug:slug>/documents/new-from-scratch/", views.DocumentCreateFromScratchView.as_view(), name="document_create_scratch"),
    path("documents/<int:pk>/", views.DocumentDetailView.as_view(), name="document_detail"),
    path("documents/<int:pk>/edit/", views.DocumentUpdateView.as_view(), name="document_update"),
    path("documents/<int:pk>/delete/", views.DocumentDeleteView.as_view(), name="document_delete"),
    path("documents/<int:pk>/edit-content/", views.DocumentEditContentView.as_view(), name="document_edit_content"),
    path("documents/<int:pk>/preview/", views.MarkdownPreviewView.as_view(), name="document_preview"),
    path("documents/<int:pk>/slides/", views.DocumentSlideView.as_view(), name="document_slides"),
    path("documents/<int:pk>/steps/", views.DocumentStepView.as_view(), name="document_steps"),
    path("documents/<int:pk>/versions/", views.DocumentVersionsView.as_view(), name="document_versions"),
    path("documents/<int:pk>/new-version/", views.NewVersionView.as_view(), name="document_new_version"),
    path("documents/<int:pk>/restore/", views.RestoreVersionView.as_view(), name="document_restore"),
    path("documents/<int:pk>/file/", views.ServeFileView.as_view(), name="serve_file"),
]
