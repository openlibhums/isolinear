import os.path
from uuid import uuid4

from django.utils import timezone
from django.core.files.base import ContentFile

from repository import models as repo_models
from utils import setting_handler
from plugins.isolinear import convert, plugin_settings
from core import files
from identifiers import preprints


def get_pdf_path(journal, article, file):
    # generate a cover sheet using the cover sheet xml setting.
    plugin = plugin_settings.IsolinearPlugin.get_self()
    isolinear_cover_sheet = setting_handler.get_plugin_setting(
        plugin,
        'isolinear_cover_sheet',
        journal,
    ).value
    repo_code = setting_handler.get_plugin_setting(
        plugin,
        'isolinear_repository_code',
        journal,
    ).value
    repository = repo_models.Repository.objects.get(
        short_name=repo_code,
    )
    context = {
        'repository': repository,
        'article': article,
        'authors': article.frozen_authors(),
    }

    cover_sheet_path = convert.generate_pdf_cover_sheet(
        isolinear_cover_sheet,
        context,
    )

    # check if the supplied file is a PDF, if it is, we only need to splice.
    file_mime = files.file_path_mime(
        file.get_file_path(article)
    )
    if not file_mime == 'application/pdf':
        article_pdf_path = convert.generate_pdf_from_doc(
            file,
        )
    else:
        article_pdf_path = file.get_file_path(article)

    # splice the two files together and return the saved path
    spliced_file_path = convert.splice_pdf_files_together(
        article_pdf_path,
        cover_sheet_path,
    )
    return spliced_file_path


def publish_repository_object_from_journal_article(article, repository, file):
    preprint, _ = repo_models.Preprint.objects.get_or_create(
        repository=repository,
        owner=article.owner,
        title=article.title,
        article=article,
        defaults={
            'date_submitted': article.date_submitted,
            'date_accepted': timezone.now(),
            'date_published': timezone.now(),
            'date_updated': timezone.now(),
            'abstract': article.abstract,
            'stage': repo_models.STAGE_PREPRINT_PUBLISHED,
            'license': article.license,
        },
    )
    for keyword in article.keywords.all():
        preprint.keywords.add(keyword)

    # Create a dummy file to allow the PreprintVersion to be generated first,
    # so the version ID can be used in the final file.
    placeholder_file = ContentFile(b"")
    placeholder_file.name = f"{uuid4()}_placeholder.pdf"

    preprint_file, _ = repo_models.PreprintFile.objects.get_or_create(
        preprint=preprint,
        file=placeholder_file,
        original_filename="placeholder.pdf",
        mime_type="application/pdf",
        size=0,
        defaults={
            'uploaded': timezone.now(),
        },
    )

    version, _ = repo_models.PreprintVersion.objects.get_or_create(
        preprint=preprint,
        version=1,
        title=preprint.title,
        abstract=preprint.abstract,
        file=preprint_file,
    )

    if article.preprint.repository.crossref_enable:
        preprints.deposit_doi_for_preprint_version(
            repository=article.preprint.repository,
            preprint_versions=[version],
        )

    file_path = get_pdf_path(
        article.journal,
        article,
        file,
    )

    with open(file_path, 'rb') as preprint_pdf:
        file = ContentFile(preprint_pdf.read())
        file.name = f"{uuid4()}.pdf"

        preprint_file.file = file
        preprint_file.original_filename = article.manuscript_files.all().first().original_filename
        preprint_file.size = os.path.getsize(file_path)
        preprint_file.save()

        version.file = preprint_file
        version.save()

        preprint.submission_file = preprint_file
        preprint.save()

    for author in article.frozen_authors():
        repo_models.PreprintAuthor.objects.get_or_create(
            preprint=preprint,
            account=author.author,
            order=author.order,
            affiliation=author.affiliation
        )


def recreate_version_file(article, version, file):
    file_path = get_pdf_path(article.journal, article, file)
    with open(file_path, 'rb') as preprint_pdf:
        file = ContentFile(preprint_pdf.read())
        file.name = f"{uuid4()}.pdf"

        preprint_file = repo_models.PreprintFile.objects.create(
            preprint=article.preprint,
            file=file,
            original_filename=article.manuscript_files.all().first().original_filename,
            mime_type='application/pdf',
            size=os.path.getsize(file_path),
            uploaded=timezone.now(),
        )
        version.file = preprint_file
        version.save()


def publish_new_preprint_version(article, file):
    """
    Publishes a new preprint version and attaches a generated PDF file.
    Ensures the version ID is included in the cover sheet by creating the
    version before generating the file.
    """
    # Create a placeholder PreprintFile object
    placeholder_file = ContentFile(b"")
    placeholder_file.name = f"{uuid4()}_placeholder.pdf"

    preprint_file, _ = repo_models.PreprintFile.objects.get_or_create(
        preprint=article.preprint,
        file=placeholder_file,
        original_filename="placeholder.pdf",
        mime_type="application/pdf",
        size=0,
        defaults={
            "uploaded": timezone.now(),
        }
    )

    # Create the version with the placeholder file
    version, _ = repo_models.PreprintVersion.objects.get_or_create(
        preprint=article.preprint,
        file=preprint_file,
        version=article.preprint.next_version_number(),
        title=article.preprint.title,
        abstract=article.preprint.abstract,
    )

    if article.preprint.repository.crossref_enable:
        preprints.deposit_doi_for_preprint_version(
            repository=article.preprint.repository,
            preprint_versions=[version],
        )

    # Generate the actual PDF file with the version ID on the cover sheet
    file_path = get_pdf_path(article.journal, article, file)
    with open(file_path, "rb") as preprint_pdf:
        generated_file = ContentFile(preprint_pdf.read())
        generated_file.name = f"{uuid4()}.pdf"

    # Update the PreprintFile with the generated file
    preprint_file.file = generated_file
    preprint_file.original_filename = article.manuscript_files.all().first().original_filename
    preprint_file.size = os.path.getsize(file_path)
    preprint_file.save()

    # Update the version with the final file
    version.file = preprint_file
    version.save()

