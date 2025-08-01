from django.core.management.base import BaseCommand
from core.tasks import ingest_data

class Command(BaseCommand):
    help = 'Ingests customer and loan data from CSV files into the database using a Celery task.'

    def handle(self, *args, **options):
        self.stdout.write('Starting data ingestion task...')
        task = ingest_data.delay()
        self.stdout.write(self.style.SUCCESS(f'Data ingestion task queued with ID: {task.id}'))
