from django.core.management.base import BaseCommand

from journal import models as jm
from core import models as cm
from submission import models as sm
from plugins.isolinear import iso_utils


class Command(BaseCommand):
    """ CLI interface for the CSV importer"""

    help = "CLI interface for the CSV importer"

    def add_arguments(self, parser):
        parser.add_argument('journal_code')
        parser.add_argument('article_id')
        parser.add_argument('file_id')

    def handle(self, *args, **options):
        journal = jm.Journal.objects.get(
            code=options.get('journal_code')
        )
        article = sm.Article.objects.get(
            pk=options.get('article_id')
        )
        file = cm.File.objects.get(
            pk=options.get('file_id'),
        )
        print(
            iso_utils.get_pdf_path(
                journal,
                article,
                file,
            )
        )
