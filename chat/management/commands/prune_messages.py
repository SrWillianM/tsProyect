from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from chat.models import Message


class Command(BaseCommand):
    help = 'Delete old chat messages older than --days (default: 30).'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30)

    def handle(self, *args, **options):
        days = max(1, options['days'])
        cutoff = timezone.now() - timedelta(days=days)

        qs = Message.objects.filter(timestamp__lt=cutoff)
        count = qs.count()
        qs.delete()

        self.stdout.write(self.style.SUCCESS(f'Deleted {count} messages older than {days} days.'))
