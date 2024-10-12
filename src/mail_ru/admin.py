from django.contrib import admin
from mail_ru.models import MailData, Attachments


admin.site.register(MailData)
admin.site.register(Attachments)
