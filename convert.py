import os
import uuid
import subprocess
from pypdf import PdfWriter

from django.conf import settings
from django.template import Template, Context

from utils.logger import get_logger

logger = get_logger(__name__)

MEMORY_LIMIT_ARG = ['+RTS', '-M256M', '-RTS']
PANDOC_CMD = ['pandoc']
LATEX = ['--pdf-engine=xelatex']


def generate_pdf_cover_sheet(cover_sheet_content, context):
    template = Template(cover_sheet_content)
    html_content = template.render(Context(context))
    temp_dir = os.path.join(
        settings.BASE_DIR,
        'files',
        'temp',
    )
    media_dir = os.path.join(
        settings.BASE_DIR,
        'media',
    )
    cover_sheet_html_path = os.path.join(
        temp_dir,
        f"{uuid.uuid4()}.html",
    )
    with open(cover_sheet_html_path, 'w') as cover_sheet_html_file:
        cover_sheet_html_file.write(
            html_content,
        )
    cover_sheet_pdf_path = os.path.join(
        temp_dir,
        f"{uuid.uuid4()}.pdf"
    )
    pandoc_command = (
        PANDOC_CMD
        + MEMORY_LIMIT_ARG
        + LATEX
        + ['-s', cover_sheet_html_path, '-t', 'pdf', '-o', cover_sheet_pdf_path, f'--resource-path={media_dir}']
    )
    try:
        logger.info("[PANDOC] Running command '{}'".format(pandoc_command))
        subprocess.run(
            pandoc_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise PandocError("PandocError: {e.stderr}".format(e=e))

    os.unlink(cover_sheet_html_path)
    return cover_sheet_pdf_path


def generate_pdf_from_doc(file):

    file_path = file.self_article_path()

    _, extension = os.path.splitext(file_path)
    if extension not in ['.docx', '.doc', '.rtf', '.odt']:
        raise TypeError("File Extension {} not supported".format(extension))

    out_filename = f"{uuid.uuid4()}.pdf"
    out_path = os.path.join(
        settings.BASE_DIR,
        'files',
        'articles',
        str(file.article_id),
        out_filename,
    )

    pandoc_command = (
        PANDOC_CMD
        + MEMORY_LIMIT_ARG
        + LATEX
        + ['-s', file_path, '-t', 'pdf', '-o', out_path]
    )

    try:
        logger.info("[PANDOC] Running command '{}'".format(pandoc_command))
        subprocess.run(
            pandoc_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise PandocError("PandocError: {e.stderr}".format(e=e))

    return out_path


def splice_pdf_files_together(article_file_path, cover_file_path):
    merger = PdfWriter()
    out_file_path = os.path.join(
        settings.BASE_DIR,
        'files',
        'temp',
        f"{uuid.uuid4()}.pdf"
    )
    for pdf in [cover_file_path, article_file_path]:
        merger.append(pdf)
    merger.write(out_file_path)

    merger.close()

    os.unlink(cover_file_path)

    return out_file_path


class PandocError(Exception):
    def __init__(self, msg, cmd=None):
        super().__init__(self, msg)
        self.cmd = cmd