from django.urls import path, re_path
from mail_ru.views import ReadMailRu, MailDetailView, MailListView, ESJsonView

from . import consumers


urlpatterns = [
    path('mail-ru/', ReadMailRu.as_view(), name='mail_ru'),
    path('', MailListView.as_view(), name='mail_list'),
    path('mail/<int:pk>/', MailDetailView.as_view(), name='mail_detail'),
    path('elastic/<str:text>', ESJsonView.as_view(), name='es_view'),
]

websocket_urlpatterns = [
    re_path(r'ws/mail_checker/$', consumers.MailCheckerConsumer.as_asgi()),
]
