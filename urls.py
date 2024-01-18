from django.urls import re_path

from plugins.isolinear import views


urlpatterns = [
    re_path(
        r'^$',
        views.index,
        name='isolinear_index',
    ),
    re_path(
        r'^article/(?P<article_id>\d+)/$',
        views.publish_preprint,
        name='isolinear_publish_preprint',
    ),
    re_path(
        r'^article/(?P<article_id>\d+)/new-version/$',
        views.create_new_version,
            name='isolinear_create_new_version',
    ),
    re_path(
        r'^manager/$',
        views.manager,
        name='isolinear_manager',
    ),
    re_path(
        r'^preprints/$',
        views.PreprintArticlesListView.as_view(),
        name='isolinear_preprint_list',
    ),
    re_path(
        r'^article/(?P<article_id>\d+)/version/(?P<version_number>\d+)/$',
        views.preprint_version,
        name='isolinear_preprint_version',
    ),
]