# smallstack-runbook

A markdown knowledge base app for [Django SmallStack](https://github.com/emichaud/django-smallstack). Write, organize, version, and search operational documentation — all from the browser.

**Requires SmallStack.** This package depends on SmallStack's theme, component CSS classes, and template blocks.

## Features

- **Markdown documents** with in-browser editor and live preview
- **Runbooks & sections** for organizing documentation
- **Full-text search** across titles, descriptions, and content
- **Version history** with restore capability
- **Slide view** — present markdown as a slide deck
- **Step view** — render `## Step N:` headings as a process timeline
- **Bulk ZIP export** with HTML table of contents
- **Staff-only access** by default
- **Automatic sidebar registration** in SmallStack navigation

## Installation

```bash
uv add git+https://github.com/emichaud/smallstack-runbook.git
```

### 1. Add to INSTALLED_APPS

```python
# settings/base.py
INSTALLED_APPS = [
    ...
    "smallstack_runbook",
]
```

### 2. Configure the base template

```python
# settings/base.py
RUNBOOK_BASE_TEMPLATE = "smallstack/base.html"
```

### 3. Add the context processor

```python
# settings/base.py
TEMPLATES = [
    {
        ...
        "OPTIONS": {
            "context_processors": [
                ...
                "smallstack_runbook.context_processors.runbook_settings",
            ],
        },
    },
]
```

### 4. Include URLs

```python
# site_urls.py (or urls.py)
path("runbook/", include("smallstack_runbook.urls")),
```

### 5. Run migrations

```bash
uv run python manage.py migrate
```

### 6. (Optional) Seed sample data

```bash
uv run python manage.py seed_runbook
```

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `RUNBOOK_BASE_TEMPLATE` | `"base.html"` | Template that all runbook pages extend |
| `RUNBOOK_STAFF_REQUIRED` | `True` | Restrict access to staff users |
| `RUNBOOK_URL_PREFIX` | `"runbook/"` | URL prefix (informational) |

## Management Commands

```bash
# Re-index all documents for full-text search
uv run python manage.py reindex_documents

# Seed sample runbook with example documents
uv run python manage.py seed_runbook
```

## License

MIT
