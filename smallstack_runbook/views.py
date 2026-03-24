"""Views for the Runbook app."""

from __future__ import annotations

from django.contrib import messages
from django.db.models import Count, Q, QuerySet
from django.http import FileResponse, Http404, HttpResponse, HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from .mixins import StaffRequiredMixin
from .forms import DocumentCreateFromScratchForm, DocumentForm, NewVersionForm, RunbookForm, SectionForm
from .models import Document, Runbook, Section, strip_frontmatter
from .utils import parse_slides, parse_steps, render_document, render_markdown

# -- Dashboard ----------------------------------------------------------------


class RunbookDashboardView(StaffRequiredMixin, TemplateView):
    """Staff-only dashboard listing all runbooks."""

    template_name = "runbook/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        docs = Document.objects.filter(is_current=True)
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)

        type_counts = docs.values("file_type").annotate(count=Count("pk")).order_by("-count")

        runbooks = Runbook.objects.annotate(
            section_count=Count("sections", distinct=True),
            doc_count=Count(
                "sections__documents",
                filter=Q(sections__documents__is_current=True),
                distinct=True,
            ),
        )

        context.update({
            "total_docs": docs.count(),
            "total_sections": Section.objects.count(),
            "total_runbooks": runbooks.count(),
            "recent_uploads": docs.filter(created_at__gte=seven_days_ago).count(),
            "type_counts": type_counts,
            "recent_docs": docs.select_related("section", "section__runbook", "uploaded_by")[:10],
            "runbooks": runbooks,
        })
        return context


# -- Runbook CRUD -------------------------------------------------------------


class RunbookCreateView(StaffRequiredMixin, CreateView):
    model = Runbook
    form_class = RunbookForm
    template_name = "runbook/runbook_form.html"

    def get_success_url(self):
        messages.success(self.request, f'Runbook "{self.object.name}" created.')
        return self.object.get_absolute_url()


class RunbookUpdateView(StaffRequiredMixin, UpdateView):
    model = Runbook
    form_class = RunbookForm
    template_name = "runbook/runbook_form.html"

    def get_success_url(self):
        messages.success(self.request, f'Runbook "{self.object.name}" updated.')
        return self.object.get_absolute_url()


class RunbookDeleteView(StaffRequiredMixin, View):
    def post(self, request: HttpRequest, slug: str):
        runbook = get_object_or_404(Runbook, slug=slug)
        name = runbook.name
        runbook.delete()
        messages.success(request, f'Runbook "{name}" deleted.')
        return redirect("runbook:dashboard")


class RunbookDetailView(StaffRequiredMixin, DetailView):
    """Table of contents view for a single runbook."""

    model = Runbook
    template_name = "runbook/runbook_detail.html"
    context_object_name = "runbook"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sections = self.object.sections.prefetch_related(
            "documents"
        ).annotate(
            doc_count=Count("documents", filter=Q(documents__is_current=True))
        ).order_by("order", "name")

        context["sections"] = sections
        context["total_docs"] = sum(s.doc_count for s in sections)
        return context


# -- Section CRUD -------------------------------------------------------------


class SectionCreateView(StaffRequiredMixin, CreateView):
    model = Section
    form_class = SectionForm
    template_name = "runbook/section_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.runbook = get_object_or_404(Runbook, slug=kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["runbook"] = self.runbook
        return context

    def form_valid(self, form):
        form.instance.runbook = self.runbook
        return super().form_valid(form)

    def get_success_url(self):
        messages.success(self.request, f'Section "{self.object.name}" created.')
        return self.object.get_absolute_url()


class SectionUpdateView(StaffRequiredMixin, UpdateView):
    model = Section
    form_class = SectionForm
    template_name = "runbook/section_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["runbook"] = self.object.runbook
        return context

    def get_success_url(self):
        messages.success(self.request, f'Section "{self.object.name}" updated.')
        return self.object.get_absolute_url()


class SectionDeleteView(StaffRequiredMixin, View):
    def post(self, request: HttpRequest, pk: int):
        section = get_object_or_404(Section, pk=pk)
        runbook = section.runbook
        name = section.name
        section.delete()
        messages.success(request, f'Section "{name}" deleted.')
        return redirect(runbook.get_absolute_url())


# -- Document CRUD ------------------------------------------------------------


def _current_docs() -> QuerySet[Document]:
    """Base queryset for current (non-superseded) documents."""
    return Document.objects.filter(is_current=True)


def _search_docs(qs: QuerySet[Document], query: str) -> QuerySet[Document]:
    """Filter documents by title, description, or content text."""
    return qs.filter(
        Q(title__icontains=query)
        | Q(description__icontains=query)
        | Q(content_text__icontains=query)
    )


class DocumentListView(StaffRequiredMixin, ListView):
    model = Document
    template_name = "runbook/document_list.html"
    context_object_name = "documents"
    paginate_by = 25

    def get_queryset(self):
        qs = _current_docs().select_related("section", "section__runbook", "uploaded_by")

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = _search_docs(qs, q)

        section = self.request.GET.get("section", "")
        if section:
            qs = qs.filter(section__slug=section)

        file_type = self.request.GET.get("type", "")
        if file_type:
            qs = qs.filter(file_type=file_type)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sections"] = Section.objects.select_related("runbook").all()
        context["search_query"] = self.request.GET.get("q", "")
        context["active_section"] = self.request.GET.get("section", "")
        context["active_type"] = self.request.GET.get("type", "")
        return context


class DocumentCreateView(StaffRequiredMixin, CreateView):
    model = Document
    form_class = DocumentForm
    template_name = "runbook/document_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.runbook = get_object_or_404(Runbook, slug=kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["runbook"] = self.runbook
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["runbook"] = self.runbook
        return context

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f'Document "{self.object.title}" uploaded.')
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()


class DocumentCreateFromScratchView(StaffRequiredMixin, CreateView):
    """Create a new markdown document from scratch (no file upload)."""

    model = Document
    form_class = DocumentCreateFromScratchForm
    template_name = "runbook/document_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.runbook = get_object_or_404(Runbook, slug=kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["runbook"] = self.runbook
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["runbook"] = self.runbook
        context["from_scratch"] = True
        return context

    def form_valid(self, form):
        from django.core.files.base import ContentFile

        doc = form.save(commit=False)
        doc.uploaded_by = self.request.user
        starter = f"# {doc.title}\n\n"
        doc.file = ContentFile(starter.encode("utf-8"), name=f"{doc.slug or 'untitled'}.md")
        doc.save()
        messages.success(self.request, f'Document "{doc.title}" created.')
        return redirect("runbook:document_edit_content", pk=doc.pk)


class DocumentUpdateView(StaffRequiredMixin, UpdateView):
    model = Document
    form_class = DocumentForm
    template_name = "runbook/document_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.object.section:
            kwargs["runbook"] = self.object.section.runbook
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object.section:
            context["runbook"] = self.object.section.runbook
        return context

    def get_success_url(self):
        messages.success(self.request, f'Document "{self.object.title}" updated.')
        return self.object.get_absolute_url()


class DocumentDeleteView(StaffRequiredMixin, View):
    def post(self, request: HttpRequest, pk: int):
        doc = get_object_or_404(Document, pk=pk)
        title = doc.title
        doc.delete()
        messages.success(request, f'Document "{title}" deleted.')
        return redirect("runbook:document_list")


# -- Document Detail & Rendering ----------------------------------------------


class DocumentDetailView(StaffRequiredMixin, DetailView):
    """Render document content based on file_type."""

    model = Document
    template_name = "runbook/document_detail.html"
    context_object_name = "document"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["rendered"] = render_document(self.object)
        return context


class DocumentSlideView(StaffRequiredMixin, DetailView):
    """Slide deck presentation for markdown documents."""

    model = Document
    template_name = "runbook/document_slides.html"
    context_object_name = "document"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not obj.is_markdown:
            raise Http404("Slide view is only available for Markdown documents.")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doc = self.object
        raw = doc.file.read().decode("utf-8")
        doc.file.seek(0)
        context["slides"] = parse_slides(strip_frontmatter(raw))
        return context


class DocumentStepView(StaffRequiredMixin, DetailView):
    """Step/process timeline view for markdown documents."""

    model = Document
    template_name = "runbook/document_steps.html"
    context_object_name = "document"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not obj.is_markdown:
            raise Http404("Step view is only available for Markdown documents.")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doc = self.object
        raw = doc.file.read().decode("utf-8")
        doc.file.seek(0)
        context["steps"] = parse_steps(strip_frontmatter(raw))
        return context


# -- Versioning ---------------------------------------------------------------


class DocumentVersionsView(StaffRequiredMixin, DetailView):
    """Show version chain for a document."""

    model = Document
    template_name = "runbook/document_versions.html"
    context_object_name = "document"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["version_chain"] = self.object.get_version_chain()
        return context


class NewVersionView(StaffRequiredMixin, CreateView):
    """Upload a new version of an existing document."""

    model = Document
    form_class = NewVersionForm
    template_name = "runbook/new_version_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.parent_doc = get_object_or_404(Document, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parent_doc"] = self.parent_doc
        return context

    def form_valid(self, form):
        new_doc = self.parent_doc.create_new_version(
            file=form.cleaned_data["file"],
            uploaded_by=self.request.user,
            description=form.cleaned_data.get("description", ""),
        )
        messages.success(self.request, f'Version {new_doc.version} of "{new_doc.title}" uploaded.')
        return redirect(new_doc.get_absolute_url())


class RestoreVersionView(StaffRequiredMixin, View):
    """Restore an old version by creating a new version from it."""

    def post(self, request: HttpRequest, pk: int):
        old_doc = get_object_or_404(Document, pk=pk)

        # Find the current head of the version chain
        current = (
            Document.objects.filter(slug=old_doc.slug, is_current=True).first()
            or old_doc
        )

        new_doc = current.create_new_version(
            file=old_doc.file,
            uploaded_by=request.user,
            description=f"Restored from version {old_doc.version}",
        )
        messages.success(request, f'Restored version {old_doc.version} as new version {new_doc.version}.')
        return redirect(new_doc.get_absolute_url())


# -- In-Place Content Editing -------------------------------------------------


class DocumentEditContentView(StaffRequiredMixin, View):
    """Edit markdown file content in-place via a textarea."""

    def _get_markdown_doc(self, pk: int) -> Document:
        doc = get_object_or_404(Document, pk=pk)
        if not doc.is_markdown:
            raise Http404("Content editing is only available for Markdown documents.")
        return doc

    def get(self, request: HttpRequest, pk: int):
        doc = self._get_markdown_doc(pk)
        raw = doc.file.read().decode("utf-8")
        doc.file.seek(0)
        return render(request, "runbook/document_edit_content.html", {
            "document": doc,
            "content": raw,
        })

    def post(self, request: HttpRequest, pk: int):
        doc = self._get_markdown_doc(pk)
        content = request.POST.get("content", "")

        # Write content to file
        doc.file.open("wb")
        doc.file.write(content.encode("utf-8"))
        doc.file.close()

        # Update search index without re-reading the file
        doc.content_text = strip_frontmatter(content)
        doc.save(update_fields=["content_text", "updated_at"], skip_content_extract=True)

        messages.success(request, f'Content of "{doc.title}" saved.')
        return redirect(doc.get_absolute_url())


class MarkdownPreviewView(StaffRequiredMixin, View):
    """htmx endpoint: render markdown content to HTML fragment."""

    def post(self, request: HttpRequest, pk: int):
        get_object_or_404(Document, pk=pk)
        content = request.POST.get("content", "")
        rendered = render_markdown(strip_frontmatter(content))
        return HttpResponse(f'<div class="runbook-content">{rendered["html"]}</div>')


# -- File Serving -------------------------------------------------------------


class ServeFileView(StaffRequiredMixin, View):
    """Serve the uploaded file (for downloads)."""

    def get(self, request: HttpRequest, pk: int):
        doc = get_object_or_404(Document, pk=pk)
        download = request.GET.get("download")
        as_attachment = download is not None
        filename = f"{doc.slug}.{doc.file_type}" if as_attachment else None
        return FileResponse(
            doc.file.open("rb"),
            content_type="text/markdown",
            as_attachment=as_attachment,
            filename=filename,
        )


# -- Bulk Download ------------------------------------------------------------


class DownloadZipView(StaffRequiredMixin, View):
    """Download documents as a ZIP with runbook/section folder structure.

    ``?runbook=<slug>`` downloads a single runbook (omit for all).
    Each runbook folder gets an ``index.html`` table of contents.
    """

    def get(self, request: HttpRequest):
        import io
        import os
        import zipfile
        from collections import defaultdict

        runbook_slug = request.GET.get("runbook", "").strip()

        docs = _current_docs().select_related(
            "section", "section__runbook"
        ).order_by("section__runbook__name", "section__order", "section__name", "title")

        if runbook_slug:
            runbook = get_object_or_404(Runbook, slug=runbook_slug)
            docs = docs.filter(section__runbook=runbook)
            zip_name = f"{runbook.slug}.zip"
            single_runbook = True
        else:
            zip_name = "runbooks.zip"
            single_runbook = False

        # Structure: {runbook: {section: [(rel_path, doc)]}}
        runbook_map: dict = defaultdict(lambda: defaultdict(list))

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for doc in docs:
                parts: list[str] = []
                rb = doc.section.runbook if doc.section else None
                sec = doc.section

                if not single_runbook and rb:
                    parts.append(rb.slug)
                if sec:
                    parts.append(sec.slug)
                filename = os.path.basename(doc.file.name)
                parts.append(filename)
                path = "/".join(parts)

                doc.file.open("rb")
                zf.writestr(path, doc.file.read())
                doc.file.close()

                rel_path = f"{sec.slug}/{filename}" if sec else filename
                runbook_map[rb][sec].append((rel_path, doc))

            for rb, sections in runbook_map.items():
                index_html = _build_zip_index(rb, sections, single_runbook)
                prefix = "" if single_runbook else f"{rb.slug}/"
                zf.writestr(f"{prefix}index.html", index_html)

        buf.seek(0)
        return FileResponse(buf, as_attachment=True, filename=zip_name, content_type="application/zip")


def _build_zip_index(runbook: Runbook | None, sections: dict, single_runbook: bool) -> str:
    """Build a standalone HTML table of contents page for a ZIP export."""
    title = runbook.name if runbook else "Runbook"
    desc = runbook.description if runbook and runbook.description else ""

    sections_html: list[str] = []
    for section, doc_list in sections.items():
        sec_name = section.name if section else "Unsorted"
        items: list[str] = []
        for rel_path, doc in doc_list:
            badge = f'<span style="color:#888;font-size:0.8em;margin-left:6px;">.{doc.file_type}</span>'
            desc_line = ""
            if doc.description:
                desc_line = f'<div style="color:#888;font-size:0.85em;">{doc.description}</div>'
            items.append(
                f'<li style="margin-bottom:8px;">'
                f'<a href="{rel_path}">{doc.title}</a>{badge}'
                f'{desc_line}</li>'
            )
        sections_html.append(
            f'<h2 style="font-size:1.1em;margin:1.5em 0 0.5em;border-bottom:1px solid #ddd;'
            f'padding-bottom:4px;">{sec_name}</h2>'
            f'<ul style="list-style:none;padding:0;">{"".join(items)}</ul>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Table of Contents</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         max-width: 720px; margin: 2em auto; padding: 0 1em; color: #222; }}
  a {{ color: #5b4a9e; }}
  h1 {{ margin-bottom: 0.25em; }}
  .subtitle {{ color: #666; margin-bottom: 1.5em; }}
</style>
</head>
<body>
<h1>{title}</h1>
{f'<p class="subtitle">{desc}</p>' if desc else ''}
{"".join(sections_html)}
</body>
</html>"""


# -- Dashboard Stat Detail ----------------------------------------------------


class DashboardStatDetailView(StaffRequiredMixin, View):
    """htmx endpoint: return HTML table for stat card drill-down modals."""

    def get(self, request: HttpRequest, stat_type: str):
        rows = _get_stat_rows(stat_type)
        return HttpResponse(_render_stat_table(rows))


def _get_stat_rows(stat_type: str) -> list[dict[str, str]]:
    """Return label/value rows for a given stat type."""
    docs = _current_docs().select_related("section", "section__runbook")

    if stat_type == "runbooks":
        runbooks = Runbook.objects.annotate(
            section_count=Count("sections", distinct=True),
            doc_count=Count(
                "sections__documents",
                filter=Q(sections__documents__is_current=True),
                distinct=True,
            ),
        ).order_by("name")
        rows = [
            {"label": rb.name, "value": f"{rb.section_count} sections, {rb.doc_count} docs"}
            for rb in runbooks
        ]
        return rows or [{"label": "No runbooks yet", "value": ""}]

    if stat_type == "documents":
        items = docs.order_by("-created_at")[:30]
        rows = [
            {
                "label": doc.title,
                "value": f".{doc.file_type} &middot; v{doc.version}"
                + (f" &middot; {doc.section.name}" if doc.section else ""),
            }
            for doc in items
        ]
        return rows or [{"label": "No documents yet", "value": ""}]

    if stat_type == "recent":
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)
        items = docs.filter(created_at__gte=seven_days_ago).order_by("-created_at")
        rows = [
            {"label": doc.title, "value": doc.created_at.strftime("%b %d, %Y")}
            for doc in items
        ]
        return rows or [{"label": "No uploads in the last 7 days", "value": ""}]

    if stat_type == "types":
        type_counts = docs.values("file_type").annotate(count=Count("pk")).order_by("-count")
        rows = [
            {"label": f".{tc['file_type']}", "value": str(tc["count"])}
            for tc in type_counts
        ]
        return rows or [{"label": "No documents yet", "value": ""}]

    return []


def _render_stat_table(rows: list[dict[str, str]]) -> str:
    """Render stat rows as an HTML table fragment."""
    parts = ['<table class="crud-table"><thead><tr><th>Name</th><th style="text-align:right;">Detail</th></tr></thead><tbody>']
    for row in rows:
        parts.append(
            f'<tr>'
            f'<td style="font-size:0.85rem;">{row["label"]}</td>'
            f'<td style="font-size:0.85rem;text-align:right;">{row["value"]}</td>'
            f'</tr>'
        )
    parts.append("</tbody></table>")
    return "".join(parts)


# -- Search -------------------------------------------------------------------


class SearchView(StaffRequiredMixin, TemplateView):
    """Full-text search across documents."""

    template_name = "runbook/search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get("q", "").strip()
        context["search_query"] = q

        if q:
            context["results"] = _search_docs(
                _current_docs(), q
            ).select_related("section", "section__runbook", "uploaded_by")[:50]
        else:
            context["results"] = []

        return context


class SearchResultsView(StaffRequiredMixin, View):
    """htmx endpoint: return search results as HTML fragment."""

    def get(self, request: HttpRequest):
        q = request.GET.get("q", "").strip()
        if not q:
            return HttpResponse("")

        results = _search_docs(
            _current_docs(), q
        ).select_related("section", "section__runbook")[:20]

        return render(request, "runbook/includes/search_results.html", {
            "results": results,
            "search_query": q,
        })
