from django.shortcuts import render, reverse, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from plugins.isolinear import iso_utils, plugin_settings, forms
from submission import models as submission_models
from repository import models as repository_models
from utils import setting_handler
from core import forms as core_forms, models as core_models
from core.views import GenericFacetedListView
from security.decorators import has_journal, any_editor_user_required
from journal import forms as journal_forms


@has_journal
@any_editor_user_required
def index(request):
    return redirect(
        reverse(
            'isolinear_manager',
        )
    )


@has_journal
@any_editor_user_required
def manager(request):
    settings = [
        {
            'name': 'enable_isolinear',
            'object': setting_handler.get_setting(
                'plugin:isolinear',
                'enable_isolinear',
                request.journal,
            ),
        },
        {
            'name': 'isolinear_repository_code',
            'object': setting_handler.get_setting(
                'plugin:isolinear',
                'isolinear_repository_code',
                request.journal,
            ),
        },
        {
            'name': 'isolinear_cover_sheet',
            'object': setting_handler.get_setting(
                'plugin:isolinear',
                'isolinear_cover_sheet',
                request.journal,
            ),
        },
    ]
    setting_group = 'plugin:isolinear'
    manager_form = core_forms.GeneratedSettingForm(
        settings=settings
    )
    if request.POST:
        manager_form = core_forms.GeneratedSettingForm(
            request.POST,
            settings=settings,
        )
        if manager_form.is_valid():
            manager_form.save(
                group=setting_group,
                journal=request.journal,
            )
            messages.add_message(
                request,
                messages.SUCCESS,
                'Form saved.',
            )
            return redirect(
                reverse('isolinear_manager')
            )
    template = 'isolinear/manager.html'
    context = {
        'manager_form': manager_form,
    }
    return render(
        request,
        template,
        context,
    )


@has_journal
@any_editor_user_required
def publish_preprint(request, article_id):
    """
    Allows an editor user to create a preprint of an article and publish it.
    :param request: HttpRequest object
    :param article_id: Integer
    :return: HttpResponse
    """
    article = get_object_or_404(
        submission_models.Article,
        pk=article_id,
        journal=request.journal,
    )
    repository_code = setting_handler.get_plugin_setting(
        plugin=plugin_settings.IsolinearPlugin.get_self(),
        setting_name='isolinear_repository_code',
        journal=request.journal,
    ).value
    repository = get_object_or_404(
        repository_models.Repository,
        short_name=repository_code,
    )
    form = forms.FileSelectionForm(
        files=article.manuscript_files.all(),
    )
    if request.POST:
        file = get_object_or_404(
            core_models.File,
            pk=request.POST.get('file'),
            article_id=article.pk,
        )
        iso_utils.publish_repository_object_from_journal_article(
            article,
            repository,
            file,
        )
        messages.add_message(
            request,
            messages.SUCCESS,
            'Preprint published.',
        )
        return redirect(
            reverse(
                'isolinear_publish_preprint',
                kwargs={
                    'article_id': article.pk,
                }
            )
        )
    template = 'isolinear/publish_preprint.html'
    context = {
        'article': article,
        'repository': repository,
        'form': form,
    }
    return render(
        request,
        template,
        context,
    )


@has_journal
@any_editor_user_required
def create_new_version(request, article_id):
    article = get_object_or_404(
        submission_models.Article,
        pk=article_id,
        journal=request.journal,
    )
    file_objs = article.manuscript_files.all().order_by('-last_modified')
    form = forms.FileSelectionForm(
        files=file_objs,
    )
    if request.POST:
        form = forms.FileSelectionForm(
            request.POST,
            files=file_objs,
        )
        if form.is_valid():
            file = form.cleaned_data.get('file')
            iso_utils.publish_new_preprint_version(
                article,
                file,
            )
            messages.add_message(
                request,
                messages.SUCCESS,
                'New version created.',
            )
            return redirect(
                reverse(
                    'isolinear_create_new_version',
                    kwargs={
                        'article_id': article.pk,
                    }
                )
            )

    template = 'isolinear/create_new_version.html'
    context = {
        'article': article,
        'form': form,
    }
    return render(
        request,
        template,
        context,
    )


def rebuild_version_pdf(request, article_id, version_id):
    article = get_object_or_404(
        submission_models.Article,
        pk=article_id,
        journal=request.journal,
    )
    version = repository_models.PreprintVersion.objects.get(
        preprint__article=article,
        pk=version_id,
    )
    file_objs = article.manuscript_files.all().order_by('-last_modified')
    form = forms.FileSelectionForm(
        files=file_objs,
    )
    if request.POST:
        form = forms.FileSelectionForm(
            request.POST,
            files=file_objs,
        )
        if form.is_valid():
            file = form.cleaned_data.get('file')
            iso_utils.recreate_version_file(
                article,
                version,
                file,
            )
            messages.add_message(
                request,
                messages.SUCCESS,
                'New file created',
            )
            return redirect(
                reverse(
                    'isolinear_rebuild_version_pdf',
                    kwargs={
                        'article_id': article.pk,
                        'version_id': version.pk,
                    }
                )
            )
    template = 'isolinear/rebuild_version_pdf.html'
    context = {
        'article': article,
        'form': form,
    }
    return render(
        request,
        template,
        context,
    )


class PreprintArticlesListView(GenericFacetedListView):
    """
    A complete list of all preprints regardless of status — under review,
    published, and declined — for full transparency.
    """

    model = submission_models.Article
    template_name = 'isolinear/full_preprint_list.html'

    def get_queryset(self, params_querydict=None):
        queryset = super().get_queryset(params_querydict)
        return queryset.filter(
            preprint__isnull=False,
        ).select_related('preprint').order_by(self.get_order_by())

    def get_facets(self):
        return {
            'q': {
                'type': 'search',
                'field_label': _('Search'),
            },
        }

    def get_order_by_choices(self):
        return [
            ('-preprint__date_published', _('Newest')),
            ('preprint__date_published', _('Oldest')),
            ('title', _('Title A–Z')),
            ('-title', _('Title Z–A')),
        ]

    def get_order_by(self):
        order_by = self.request.GET.get('order_by', '-preprint__date_published')
        return order_by if order_by in dict(self.get_order_by_choices()) else '-preprint__date_published'


def preprint_version(request, article_id, version_number):
    article = get_object_or_404(
        submission_models.Article,
        pk=article_id,
        journal=request.journal,
        preprint__isnull=False,
    )
    preprint_version = get_object_or_404(
        repository_models.PreprintVersion,
        preprint=article.preprint,
        version=version_number,
    )
    repository_code = setting_handler.get_plugin_setting(
        plugin=plugin_settings.IsolinearPlugin.get_self(),
        setting_name='isolinear_repository_code',
        journal=request.journal,
    ).value

    public_editorial_log = setting_handler.get_setting(
        'general',
        'public_editorial_log',
        request.journal,
    ).processed_value

    editorial_log = None
    if public_editorial_log:
        from journal import logic as journal_logic
        editorial_log = journal_logic.build_editorial_timeline(article)

    template = 'journal/preprint_version.html'
    context = {
        'article': article,
        'preprint_version': preprint_version,
        'repository_code': repository_code,
        'editorial_log': editorial_log,
    }
    return render(
        request,
        template,
        context,
    )

