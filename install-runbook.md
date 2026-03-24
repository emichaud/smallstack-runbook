# Skill: Install smallstack-runbook

Install the `smallstack-runbook` package into any SmallStack project. This adds a markdown knowledge base with runbooks, sections, versioned documents, full-text search, slide/step views, and bulk ZIP export.

## Prerequisites

- A working SmallStack project with `apps.smallstack` in `INSTALLED_APPS`
- The project must already have SmallStack's theme, component CSS, and template blocks

## Steps

### 1. Add the package

```bash
uv add "smallstack-runbook @ git+https://github.com/emichaud/smallstack-runbook.git"
```

### 2. Add to INSTALLED_APPS

In `config/settings/base.py`, add `"smallstack_runbook"` to `INSTALLED_APPS`. Place it with the other custom apps, before `django.contrib.admin`:

```python
INSTALLED_APPS = [
    ...
    "smallstack_runbook",
    ...
]
```

### 3. Add the base template setting

In `config/settings/base.py`, add this setting (anywhere after the imports):

```python
RUNBOOK_BASE_TEMPLATE = "smallstack/base.html"
```

### 4. Add the context processor

In `config/settings/base.py`, add the runbook context processor to the `TEMPLATES` config. It goes after `apps.smallstack.context_processors.branding`:

```python
TEMPLATES = [
    {
        ...
        "OPTIONS": {
            "context_processors": [
                ...
                "apps.smallstack.context_processors.branding",
                "smallstack_runbook.context_processors.runbook_settings",
            ],
        },
    },
]
```

### 5. Include URLs

In `apps/smallstack/site_urls.py` (or wherever URLs are wired), add the runbook URL include:

```python
path("runbook/", include("smallstack_runbook.urls")),
```

Don't forget to import `include` from `django.urls` if it isn't already imported.

### 6. Run migrations

```bash
uv run python manage.py migrate
```

### 7. (Optional) Seed sample data

```bash
uv run python manage.py seed_runbook
```

## Verification

1. Start the dev server: `make run`
2. Log in as a staff user
3. The "Runbook" link should appear in the sidebar navigation
4. Navigate to `/smallstack/runbook/` (or wherever your SmallStack prefix is) — the dashboard should load
5. If you seeded data, you should see sample runbooks and documents

## Optional settings

| Setting | Default | Description |
|---------|---------|-------------|
| `RUNBOOK_BASE_TEMPLATE` | `"base.html"` | Template that all runbook pages extend |
| `RUNBOOK_STAFF_REQUIRED` | `True` | Restrict access to staff users |
| `RUNBOOK_URL_PREFIX` | `"runbook/"` | URL prefix (informational) |

## Management commands

```bash
# Re-index all documents for full-text search
uv run python manage.py reindex_documents

# Seed sample runbook with example documents
uv run python manage.py seed_runbook
```

## Troubleshooting

- **No sidebar link**: Make sure `"smallstack_runbook"` is in `INSTALLED_APPS` and that the project has `apps.smallstack.navigation` available.
- **Template errors**: Make sure `RUNBOOK_BASE_TEMPLATE` is set and the context processor is registered.
- **404 on runbook URLs**: Make sure the URL include is in place and you've restarted the dev server.
- **Migration conflicts**: The package uses app label `runbook`. If you previously had an `apps.runbook` app, the existing migration history and tables will be reused automatically.
