from utils import plugins
from utils.install import update_settings

PLUGIN_NAME = 'Isolinear'
DESCRIPTION = 'Combines repository and journal workflows.'
AUTHOR = 'Open Library of Humanities'
VERSION = '0.1'
SHORT_NAME = 'isolinear'
DISPLAY_NAME = 'Isolinear'
MANAGER_URL = 'isolinear_index'
JANEWAY_VERSION = "1.5.0"
IS_WORKFLOW_PLUGIN = False

MS_MIMES_FOR_PREPRINTS = [
    'application/pdf',
    'application/x-pdf',
    'application/rtf',
    'application/x-rtf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.oasis.opendocument.text',
]
class IsolinearPlugin(plugins.Plugin):
    plugin_name = PLUGIN_NAME
    display_name = DISPLAY_NAME
    description = DESCRIPTION
    author = AUTHOR
    short_name = SHORT_NAME

    manager_url = MANAGER_URL

    version = VERSION
    janeway_version = JANEWAY_VERSION

    is_workflow_plugin = IS_WORKFLOW_PLUGIN


def install():
    IsolinearPlugin.install()
    update_settings(
        file_path='plugins/isolinear/install/settings.json'
    )


def hook_registry():
    return {
        'unassigned_additional_actions':
            {
                'module': 'plugins.isolinear.hooks',
                'function': 'editor_assignment_hook',
            },
        'logs_documents':
            {
                'module': 'plugins.isolinear.hooks',
                'function': 'logs_documents_hook',
            },
        'preprint_abstract_block':
            {
                'module': 'plugins.isolinear.hooks',
                'function': 'abstract',
            },
        'article_content':
            {
                'module': 'plugins.isolinear.hooks',
                'function': 'embed_pdf',
            },
        'preprint_version_downloads':
            {
                'module': 'plugins.isolinear.hooks',
                'function': 'version_downloads',
            },
        'review_actions':
            {
                'module': 'plugins.isolinear.hooks',
                'function': 'review_actions',
            },
    }
