from django.core.management.base import BaseCommand

from operations.services.messaging import (
    run_reminders
)


class Command(BaseCommand):

    help = 'Run followup and chronic reminders'

    def handle(self, *args, **kwargs):

        result = run_reminders()

        self.stdout.write(
            self.style.SUCCESS(
                str(result)
            )
        )