from django.template.loader import render_to_string

from utils import setting_handler
from plugins.isolinear import plugin_settings


def editor_assignment_hook(context):
    plugin = plugin_settings.IsolinearPlugin.get_self()
    request = context.get('request')
    article = context.get('article')
    isolinear_enabled = setting_handler.get_plugin_setting(
        plugin,
        'enable_isolinear',
        request.journal,
    ).value

    if isolinear_enabled:
        return render_to_string(
            'isolinear/editor_assignment.html',
            {
                'article': article,
            }
        )


def logs_documents_hook(context):
    plugin = plugin_settings.IsolinearPlugin.get_self()
    request = context.get('request')
    article = context.get('article')
    isolinear_enabled = setting_handler.get_plugin_setting(
        plugin,
        'enable_isolinear',
        request.journal,
    ).value

    if isolinear_enabled:
        return render_to_string(
            'isolinear/logs_documents.html',
            {
                'article': article,
            }
        )


def abstract(context):
    plugin = plugin_settings.IsolinearPlugin.get_self()
    request = context.get('request')
    article = context.get('article')
    isolinear_enabled = setting_handler.get_plugin_setting(
        plugin,
        'enable_isolinear',
        request.journal,
    ).value

    if isolinear_enabled:
        return render_to_string(
            'isolinear/abstract.html',
            {
                'article': article,
            }
        )


def embed_pdf(context):
    plugin = plugin_settings.IsolinearPlugin.get_self()
    request = context.get('request')
    article = context.get('article')
    isolinear_enabled = setting_handler.get_plugin_setting(
        plugin,
        'enable_isolinear',
        request.journal,
    ).value
    repository_code = setting_handler.get_plugin_setting(
        plugin=plugin_settings.IsolinearPlugin.get_self(),
        setting_name='isolinear_repository_code',
        journal=request.journal,
    ).value

    if isolinear_enabled:
        return render_to_string(
            'isolinear/embed_pdf.html',
            {
                'article': article,
                'preprint': article.preprint,
                'repository_code': repository_code,
            }
        )


def version_downloads(context):
    plugin = plugin_settings.IsolinearPlugin.get_self()
    request = context.get('request')
    article = context.get('article')
    isolinear_enabled = setting_handler.get_plugin_setting(
        plugin,
        'enable_isolinear',
        request.journal,
    ).value
    repository_code = setting_handler.get_plugin_setting(
        plugin=plugin_settings.IsolinearPlugin.get_self(),
        setting_name='isolinear_repository_code',
        journal=request.journal,
    ).value

    if isolinear_enabled:
        return render_to_string(
            'isolinear/version_downloads.html',
            {
                'article': article,
                'preprint': article.preprint,
                'repository_code': repository_code,
            }
        )


def review_actions(context):
    plugin = plugin_settings.IsolinearPlugin.get_self()
    request = context.get('request')
    article = context.get('article')
    isolinear_enabled = setting_handler.get_plugin_setting(
        plugin,
        'enable_isolinear',
        request.journal,
    ).value
    repository_code = setting_handler.get_plugin_setting(
        plugin=plugin_settings.IsolinearPlugin.get_self(),
        setting_name='isolinear_repository_code',
        journal=request.journal,
    ).value

    if isolinear_enabled:
        return render_to_string(
            'isolinear/review_actions.html',
            {
                'article': article,
                'preprint': article.preprint,
                'repository_code': repository_code,
            }
        )