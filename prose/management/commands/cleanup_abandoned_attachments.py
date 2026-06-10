from datetime import timedelta

from django.core.management.base import BaseCommand

from prose.content import cleanup_abandoned_attachments


class Command(BaseCommand):
    help = (
        "Delete prose.Attachment rows that are not linked to any rich text "
        "field (uploaded but never saved, or orphaned after edits)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List attachments that would be deleted without deleting them.",
        )
        parser.add_argument(
            "--minimum-age-hours",
            type=int,
            default=24,
            help=(
                "Only delete attachments created at least this many hours ago "
                "(default: 24). Use 0 to include all unlinked attachments."
            ),
        )

    def handle(self, *args, **options):
        minimum_age = timedelta(hours=options["minimum_age_hours"])
        attachments = cleanup_abandoned_attachments(
            minimum_age=minimum_age,
            dry_run=options["dry_run"],
        )

        if not attachments:
            self.stdout.write("No abandoned attachments found.")
            return

        verb = "Would delete" if options["dry_run"] else "Deleted"
        self.stdout.write(f"{verb} {len(attachments)} abandoned attachment(s):")

        for attachment in attachments:
            label = attachment.filename or attachment.content_type or attachment.pk
            self.stdout.write(
                f"  - {label} (id={attachment.pk}, created {attachment.created_at:%Y-%m-%d %H:%M})"
            )
