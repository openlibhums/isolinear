import os
import re
import shutil
import uuid
import subprocess
import tempfile
import zipfile
from pypdf import PdfWriter

from django.conf import settings
from django.template import Template, Context

from utils.logger import get_logger

logger = get_logger(__name__)

MEMORY_LIMIT_ARG = ['+RTS', '-M256M', '-RTS']
PANDOC_CMD = ['pandoc']
LATEX = ['--pdf-engine=xelatex']
GEOMETRY = ['-V', 'geometry:margin=1in']
COVER_SHEET_STYLE = ['-V', 'mainfont=Arial', '-V', 'pagestyle=empty']

LATEXMK_CMD = [
    'latexmk',
    '-lualatex',
    '-interaction=nonstopmode',
    '-halt-on-error',
    '-no-shell-escape',
]
LATEX_TIMEOUT = 300
# Stops TeX reading or writing files outside the build directory.
LATEX_ENV = {'openin_any': 'p', 'openout_any': 'p', 'shell_escape': 'f'}
MAX_ZIP_FILES = 2000
MAX_ZIP_BYTES = 500 * 1024 * 1024
DOCUMENTCLASS = re.compile(r'^[^%\n]*\\documentclass', re.MULTILINE)


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
        + GEOMETRY
        + COVER_SHEET_STYLE
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
    out_dir = os.path.join(
        settings.BASE_DIR,
        'files',
        'articles',
        str(file.article_id),
    )
    return generate_pdf_from_doc_path(file.self_article_path(), out_dir)


def generate_pdf_from_doc_path(file_path, out_dir):
    _, extension = os.path.splitext(file_path)
    if extension not in ['.docx', '.doc', '.rtf', '.odt']:
        raise PandocError("File Extension {} not supported".format(extension))

    out_filename = f"{uuid.uuid4()}.pdf"
    out_path = os.path.join(out_dir, out_filename)

    pandoc_command = (
        PANDOC_CMD
        + MEMORY_LIMIT_ARG
        + LATEX
        + GEOMETRY
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


def generate_pdf_from_latex_zip(zip_path):
    """
    Builds a PDF from a zipped LaTeX project with latexmk and LuaLaTeX.
    The project is unpacked into a temporary directory that is removed
    afterwards, and the PDF is copied to files/temp.
    """
    temp_dir = os.path.join(settings.BASE_DIR, 'files', 'temp')
    build_dir = tempfile.mkdtemp(prefix='isolinear-latex-', dir=temp_dir)
    try:
        extract_latex_zip(zip_path, build_dir)
        main_tex = find_main_tex(build_dir)
        command = LATEXMK_CMD + [os.path.basename(main_tex)]
        logger.info("[LATEX] Running command '{}'".format(command))
        try:
            subprocess.run(
                command,
                cwd=os.path.dirname(main_tex),
                env=dict(os.environ, **LATEX_ENV),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=LATEX_TIMEOUT,
                check=True,
            )
        except subprocess.TimeoutExpired:
            raise LatexError(
                'LaTeX build took longer than {} seconds.'.format(LATEX_TIMEOUT)
            )
        except subprocess.CalledProcessError as e:
            raise LatexError(
                'LaTeX build failed: {}'.format(latex_log_tail(main_tex, e)),
            )

        pdf_path = os.path.splitext(main_tex)[0] + '.pdf'
        if not os.path.exists(pdf_path):
            raise LatexError('LaTeX build finished without producing a PDF.')
        out_path = os.path.join(temp_dir, f"{uuid.uuid4()}.pdf")
        shutil.copyfile(pdf_path, out_path)
        return out_path
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)


def extract_latex_zip(zip_path, build_dir):
    root = os.path.realpath(build_dir)
    with zipfile.ZipFile(zip_path) as archive:
        members = [
            info for info in archive.infolist()
            if not info.is_dir()
            and not info.filename.startswith('__MACOSX/')
            and not os.path.basename(info.filename).startswith('._')
        ]
        if len(members) > MAX_ZIP_FILES:
            raise LatexError('The zip file contains too many files.')
        if sum(info.file_size for info in members) > MAX_ZIP_BYTES:
            raise LatexError('The zip file is too large once unpacked.')
        for info in members:
            target = os.path.realpath(os.path.join(root, info.filename))
            if os.path.commonpath([root, target]) != root:
                raise LatexError(
                    'The zip file contains an unsafe path: {}'.format(info.filename)
                )
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with archive.open(info) as source, open(target, 'wb') as dest:
                shutil.copyfileobj(source, dest)


def find_main_tex(build_dir):
    """
    Returns the .tex file that declares \\documentclass, preferring main.tex
    and then the one nearest the top of the project.
    """
    candidates = []
    for dirpath, _, filenames in os.walk(build_dir):
        for filename in filenames:
            if not filename.lower().endswith('.tex'):
                continue
            path = os.path.join(dirpath, filename)
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                if DOCUMENTCLASS.search(f.read()):
                    candidates.append(path)
    if not candidates:
        raise LatexError('No .tex file with \\documentclass found in the zip.')
    candidates.sort(key=lambda path: (
        os.path.basename(path).lower() != 'main.tex',
        path.count(os.sep),
        path,
    ))
    return candidates[0]


def latex_log_tail(main_tex, error, lines=20):
    log_path = os.path.splitext(main_tex)[0] + '.log'
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            log = f.read().splitlines()
        errors = [line for line in log if line.startswith('!')]
        return '\n'.join(errors[:5] or log[-lines:])
    return error.stderr.decode('utf-8', 'ignore')[-2000:]


class PandocError(Exception):
    def __init__(self, msg, cmd=None):
        super().__init__(self, msg)
        self.cmd = cmd


class LatexError(Exception):
    pass