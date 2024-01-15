from django.shortcuts import render, reverse, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from plugins.isolinear import iso_utils, plugin_settings, forms
from submission import models as submission_models
from repository import models as repository_models
from utils import setting_handler
from core import forms as core_forms, models as core_models
from core.views import FilteredArticlesListView
from security.decorators import has_journal, any_editor_user_required
from journal import forms as journal_forms


@has_journal
@any_editor_user_required
def index(request):
    pass


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


class PreprintArticlesListView(FilteredArticlesListView):

    """
    A list of published articles that can be searched,
    sorted, and filtered
    """

    template_name = 'journal/article_list.html'

    def get_queryset(self, params_querydict=None):

        self.queryset = super().get_queryset(params_querydict)
        return self.queryset.filter(
            preprint__date_published__lte=timezone.now(),
            date_published__isnull=True,
        )

    def get_facets(self):

        facets = {
            'preprint__date_published__date__gte': {
                'type': 'date',
                'field_label': _('Published after'),
            },
            'preprint__date_published__date__lte': {
                'type': 'date',
                'field_label': _('Published before'),
            },
            'section__pk': {
                'type': 'foreign_key',
                'model': submission_models.Section,
                'field_label': _('Section'),
                'choice_label_field': 'name',
            },
        }
        return self.filter_facets_if_journal(facets)

    def get_facet_queryset(self):
        queryset = super().get_facet_queryset()
        return queryset.filter(
            preprint__date_published__lte=timezone.now(),
        )

    def get_order_by_choices(self):
        return [
            ('-preprint__date_published', _('Newest')),
            ('preprint__date_published', _('Oldest')),
            ('title', _('Titles A-Z')),
            ('-title', _('Titles Z-A')),
            ('correspondence_author__last_name', _('Author Name')),
        ]

    def order_queryset(self, queryset):
        order_by = self.get_order_by()
        if order_by:
            return queryset.order_by('pinnedarticle__sequence', order_by)
        else:
            return queryset.order_by('pinnedarticle__sequence')

    def get_order_by(self):
        order_by = self.request.GET.get('order_by', '-preprint__date_published')
        order_by_choices = self.get_order_by_choices()
        return order_by if order_by in dict(order_by_choices) else ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = journal_forms.SearchForm()
        context['preprints'] = True
        return context
