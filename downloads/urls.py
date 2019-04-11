from django.conf.urls import url
import views

urlpatterns = [
    url(r'^data/create/', views.CreatePath.as_view()),

    url(r'^files/archive/(?P<key>[a-f0-9]{40})/(?P<path>[^.]+\.tar\.gz)$', views.send_archive),
    url(r'^files/snapshot/(?P<key>[a-f0-9]{40})/(?P<path>.+)$', views.send_snapshot),
    url(r'^files/raw/(?P<key>[a-f0-9]{40})/(?P<path>.+)$', views.send_file),
    url(r'^files/frame/(?P<key>[a-f0-9]{40})/(?P<path>.+)/(?P<brightness>\w{2}).png$', views.send_frame),

    # remove these
    url(r'^files/(?P<key>[a-f0-9]{40})/(?P<path>[^.]+\.tar\.gz)$', views.send_archive),
    url(r'^files/(?P<path>[^.]+\.tar\.gz)$', views.send_archive),
    url(r'^files/(?P<key>[a-f0-9]{40})/(?P<path>.+\.gif)$', views.send_snapshot),
    url(r'^files/(?P<key>[a-f0-9]{40})/(?P<path>.+)$', views.send_file),

]
