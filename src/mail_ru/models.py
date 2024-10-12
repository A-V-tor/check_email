import datetime
from django.db import models

# Create your models here.


class MailData(models.Model):
    theme = models.CharField(max_length=255, verbose_name='тема сообщения')
    date_receipt = models.DateField(
        default=datetime.datetime.now, verbose_name='дата получения', null=True
    )
    body = models.TextField(verbose_name='текст сообщения', null=True)


class Attachments(models.Model):
    name = models.CharField(max_length=255, verbose_name='название')
    mail = models.ForeignKey(
        'MailData',
        related_name='attachments',
        on_delete=models.CASCADE,
        verbose_name='письмо',
        null=True,
    )
