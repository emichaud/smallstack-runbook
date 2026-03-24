"""Backfill content_text for all existing documents."""

from django.core.management.base import BaseCommand

from smallstack_runbook.models import Document


class Command(BaseCommand):
    help = "Extract and store plaintext from all document files for full-text search."

    def handle(self, *args, **options) -> None:
        docs = Document.objects.all()
        total = docs.count()
        updated = 0

        for doc in docs.iterator():
            text = doc.extract_text()
            if text != doc.content_text:
                doc.content_text = text
                doc.save(update_fields=["content_text"], skip_content_extract=True)
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Indexed {updated}/{total} documents."))
