import imaplib
import sys
import os
import chardet
import email

from email.header import decode_header
from datetime import datetime
import base64
from bs4 import BeautifulSoup
import re


def save_attachments(file_path: str, file_data):
    try:
        with open(file_path, 'wb') as f:
            f.write(file_data)
        print(f'Сохранено вложение: {file_path}')

        return True

    except IOError as e:
        print(f'Ошибка сохранения файла {filename}: {e}')


def sanitize_filename(filename):
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


def decode_mime_words(s):
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


mail_pass = 'JwghbwzbPiwby72LXBZu'
username = 'torshin.artem@mail.ru'

imap_server = 'imap.mail.ru'
imap = imaplib.IMAP4_SSL(imap_server)
imap.login(username, mail_pass)

imap.select('INBOX')

# Получаем списки идентификаторов прочитанных и непрочитанных писем
status, unseen_messages = imap.search(None, 'UNSEEN')
status, seen_messages = imap.search(None, 'SEEN')

unseen_messages = unseen_messages[0].split()
seen_messages = seen_messages[0].split()

all_messages = unseen_messages + seen_messages


# Создаем директорию для сохранения файлов вложений, если она не существует
attachments_dir = 'attachments'
if not os.path.exists(attachments_dir):
    os.makedirs(attachments_dir)

# Проходимся по каждому письму
for num in all_messages:
    status, msg_data = imap.fetch(num, '(RFC822)')
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
    if date_tuple:
        sent_date = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))

    received_date = datetime.now()

    letter_id = msg['Message-ID']
    letter_from = msg['Return-path']
    subject = msg['Subject']
    thema_mail = decode_mime_words(subject) if subject else 'Без темы'

    print(f'Status: {status_label}')
    print(f'Date Sent: {sent_date}')
    print(f'Date Received: {received_date}')
    print(f'Message ID: {letter_id}')
    print(f'Return Path: {letter_from}')
    print(f'Subject: {thema_mail}')

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
                    decoded_payload = payload.decode(encoding, errors='ignore')

                    # Проверяем тип контента (text/plain или text/html)
                    if part.get_content_subtype() == 'html':
                        # Парсим HTML и извлекаем только текстовое содержимое
                        soup = BeautifulSoup(decoded_payload, 'html.parser')
                        text = soup.get_text()
                    else:
                        text = decoded_payload

                    print(text)
                except (UnicodeDecodeError, AttributeError) as e:
                    print(f'Ошибка декодирования: {e}')

        # Если это вложение:
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
                sanitized_filename = sanitize_filename(decoded_filename)
                file_data = part.get_payload(decode=True)
                file_path = os.path.join(attachments_dir, sanitized_filename)

                check_save_attachments = save_attachments(file_path, file_data)


# закрыть сессию с подключением к серверу
imap.logout()
