import time

from django.core.management.base import BaseCommand

from chat.models import Message, Room


class Command(BaseCommand):
    help = 'Benchmark insert and paginated query performance for chat messages.'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=1000)
        parser.add_argument('--room', type=str, default='Benchmark')

    def handle(self, *args, **options):
        count = max(1, options['count'])
        room_name = options['room']
        room, _ = Room.objects.get_or_create(name=room_name)

        start_insert = time.perf_counter()
        batch = [
            Message(room=room, alias='Bench', content=f'Message {idx}')
            for idx in range(count)
        ]
        Message.objects.bulk_create(batch, batch_size=200)
        insert_ms = (time.perf_counter() - start_insert) * 1000

        start_query = time.perf_counter()
        rows = list(
            room.messages.only('id', 'alias', 'content', 'timestamp')
            .order_by('-timestamp')[:30]
        )
        query_ms = (time.perf_counter() - start_query) * 1000

        self.stdout.write(self.style.SUCCESS(f'Inserted {count} messages in {insert_ms:.2f}ms'))
        self.stdout.write(self.style.SUCCESS(f'Loaded {len(rows)} messages in {query_ms:.2f}ms'))
