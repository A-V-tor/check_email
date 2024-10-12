from django.views.generic import TemplateView, ListView, DetailView, View
from .models import MailData, Attachments
from django.http import JsonResponse
from core.settings import es_client


class ReadMailRu(TemplateView):
    template_name = 'mail_ru/index.html'


class MailListView(ListView):
    model = MailData
    template_name = 'mail_ru/mail_list.html'
    context_object_name = 'mails'

    def get_queryset(self):
        return MailData.objects.all().order_by('id')


class MailDetailView(DetailView):
    model = MailData
    template_name = 'mail_ru/mail_detail.html'
    context_object_name = 'mail'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['attachments'] = Attachments.objects.filter(mail=self.object)
        return context


class ESJsonView(ListView):
    def get(self, request, *args, **kwargs):
        text_param = kwargs.get('text')
        resp = es_client.search(
            index='mail-index', query={'match': {'text': text_param}}
        )

        hits = resp.get('hits', {}).get('hits', [])
        results = [hit['_source'] for hit in hits]

        return JsonResponse({
            'query': text_param,
            'results': results,
            'total_hits': resp.get('hits', {}).get('total', {}).get('value', 0),
        }, json_dumps_params={'ensure_ascii': False, 'indent': 4})
