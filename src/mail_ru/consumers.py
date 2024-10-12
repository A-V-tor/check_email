import json
import imaplib
import asyncio
import email
import os
from datetime import datetime
from email.header import decode_header
from bs4 import BeautifulSoup
import chardet
from asgiref.sync import sync_to_async
from core.settings import es_client

from .models import Attachments, MailData
from channels.generic.websocket import AsyncWebsocketConsumer


class MailCheckerConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        username = data.get('username')
        password = data.get('password')

        if username and password:
            await self.check_mail(password, username)

    def save_data(self, thema_mail, sent_date, text):
        new_note = MailData.objects.create(
            theme=thema_mail,
            date_receipt=sent_date,
            body=text,
        )

        return new_note

    def save_attachment(self, name, mail):
        note = Attachments.objects.create(name=name[:255], mail=mail)

        return note

    async def save_attachments(self, filename: str, file_path: str, file_data):
        try:
            with open(file_path, 'wb') as f:
                f.write(file_data)
            print(f'Сохранено вложение: {file_path}')

            return True

        except IOError as e:
            print(f'Ошибка сохранения файла {filename}: {e}')

    async def sanitize_filename(self, filename):
        """
        Создает безопасное имя файла, удаляя потенциально опасные символы.
        :param filename: Оригинальное имя файла
        :return: Безопасное имя файла
        """
        if isinstance(filename, bytes):
            filename = filename.decode('utf-8', errors='ignore')
        return ''.join(
            c for c in filename if c.isalnum() or c in (' ', '.', '_')
        ).rstrip()

    async def decode_mime_words(self, s):
        """
        Декодирует заголовок в кодировке MIME.
        :param s: MIME-заголовок
        :return: Декодированная строка
        """
        if not s:
            return ''
        decoded_words = decode_header(s)
        decoded_string = ''
        for word, enc in decoded_words:
            if isinstance(word, bytes):
                enc = enc if enc else 'utf-8'
                try:
                    word = word.decode(enc, errors='ignore')
                except LookupError:
                    word = word.decode('utf-8', errors='ignore')
            decoded_string += word
        return decoded_string

    async def check_mail(self, mail_psw, username):
        # Создаем директорию для сохранения файлов вложений, если она не существует
        attachments_dir = 'attachments'
        if not os.path.exists(attachments_dir):
            os.makedirs(attachments_dir)

        loop = asyncio.get_event_loop()
        imap_server = 'imap.mail.ru'

        imap = imaplib.IMAP4_SSL(imap_server)
        try:
            await loop.run_in_executor(None, imap.login, username, mail_psw)
        except UnicodeEncodeError:
            await self.send(
                text_data=json.dumps(
                    {
                        'progress': 0,
                        'message': f'ТОЛЬКО ASCII СИМВОЛЫ!!!',
                    }
                )
            )
            return
        except imaplib.IMAP4.error:
            await self.send(
                text_data=json.dumps(
                    {
                        'progress': 0,
                        'message': f'НЕВРНОЕ ИМЯ ИЛИ ПАРОЛЬ - 403',
                    }
                )
            )
            return
        await loop.run_in_executor(None, imap.select, 'INBOX')

        # Получаем списки идентификаторов прочитанных и непрочитанных писем
        status, unseen_messages = await loop.run_in_executor(
            None, imap.search, None, 'UNSEEN'
        )
        status, seen_messages = await loop.run_in_executor(
            None, imap.search, None, 'SEEN'
        )

        unseen_messages = unseen_messages[0].split()
        seen_messages = seen_messages[0].split()

        all_messages = unseen_messages + seen_messages
        total_messages = len(all_messages)

        # Проходимся по каждому письму
        for index, num in enumerate(all_messages, 1):
            status, msg_data = await loop.run_in_executor(
                None, imap.fetch, num, '(RFC822)'
            )
            if status != 'OK':
                print(f'Ошибка получения письма {num}')
                continue

            msg = email.message_from_bytes(msg_data[0][1])

            # Определяем статус прочитанности
            is_unseen = num in unseen_messages
            status_label = 'Непрочитанное' if is_unseen else 'Прочитанное'

            # Пример обработки заголовков
            date_header = msg['Date']
            date_tuple = email.utils.parsedate_tz(date_header)
            sent_date = None
            if date_tuple:
                sent_date = datetime.fromtimestamp(
                    email.utils.mktime_tz(date_tuple)
                )

            letter_id = msg['Message-ID']
            letter_from = msg['Return-path']
            subject = msg['Subject']
            thema_mail = (
                await self.decode_mime_words(subject)
                if subject
                else 'Без темы'
            )
            text = ''
            attachments = []

            # Обрабатываем тело письма
            for part in msg.walk():
                content_disposition = part.get('Content-Disposition')

                if part.get_content_maintype() == 'text':
                    payload = part.get_payload(decode=True)
                    if payload:
                        # Определяем кодировку с использованием chardet
                        result = chardet.detect(payload)
                        encoding = result['encoding']

                        try:
                            encoding = encoding if encoding else 'utf-8'
                            decoded_payload = payload.decode(
                                encoding, errors='ignore'
                            )

                            # Проверяем тип контента (text/plain или text/html)
                            if part.get_content_subtype() == 'html':
                                # Парсим HTML и извлекаем только текстовое содержимое
                                soup = BeautifulSoup(
                                    decoded_payload, 'html.parser'
                                )
                                text = soup.get_text()
                            else:
                                text = decoded_payload

                        except (UnicodeDecodeError, AttributeError) as e:
                            print(f'Ошибка декодирования: {e}')

                # если это вложение:
                if content_disposition and 'attachment' in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        decoded_filename, encoding = decode_header(filename)[0]
                        if isinstance(decoded_filename, bytes):
                            encoding = encoding if encoding else 'utf-8'
                            try:
                                decoded_filename = decoded_filename.decode(
                                    encoding, errors='ignore'
                                )
                            except LookupError:
                                decoded_filename = decoded_filename.decode(
                                    'utf-8', errors='ignore'
                                )
                        sanitized_filename = await self.sanitize_filename(
                            decoded_filename
                        )
                        file_data = part.get_payload(decode=True)
                        file_path = os.path.join(
                            attachments_dir, sanitized_filename
                        )

                        await self.save_attachments(
                            filename, file_path, file_data
                        )
                        attachments.append(filename)

            save_data_async = sync_to_async(self.save_data)
            mail_note = await save_data_async(thema_mail, sent_date, text)

            save_attachment_async = sync_to_async(self.save_attachment)
            for attachment in attachments:
                await save_attachment_async(attachment, mail_note)

            doc = {
                'id': mail_note.id,
                'theme': mail_note.theme,
                'text': mail_note.body,
                'attachments': attachments
            }
            es_client.index(index='mail-index', id=mail_note.id, document=doc)

            sent_date = (
                sent_date.strftime('%Y-%m-%d %H:%M:%S') if sent_date else None
            )
            # Обновляем прогресс
            await self.send(
                text_data=json.dumps(
                    {
                        'progress': index / total_messages * 100,
                        'message': f'Проверено {index} из {total_messages} писем',
                        'text_message': text,
                        'subject': thema_mail,
                        'id': index,
                        'sent_date': sent_date,
                    }
                )
            )
            attachments = []

        # закрыть сессию с подключением к серверу
        await loop.run_in_executor(None, imap.logout)
