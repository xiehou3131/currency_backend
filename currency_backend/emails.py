#! /usr/bin/env python
# -*- coding: utf-8 -*-

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from email import encoders
import os


def send_mail(mail_to, mail_from, subject, text, files, server="localhost"):
    assert type(mail_to) == list
    assert type(files) == list

    msg = MIMEMultipart()
    msg['From'] = mail_from
    msg['To'] = COMMASPACE.join(mail_to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject
    # 如果 text 是html，则需要设置 _subtype='html'
    # 默认情况下 _subtype='plain'，即纯文本
    # msg.attach(MIMEText(text, _subtype='html', _charset='utf-8'))
    msg.attach(MIMEText(text, 'html', _charset='utf-8'))

    for f in files:
        part = MIMEBase('application', "octet-stream")
        part.set_payload(open(f, "rb").read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"'
                        % os.path.basename(f))
        msg.attach(part)

    smtp = smtplib.SMTP(server, port=8001)
    try:
        smtp.sendmail(mail_from, mail_to, msg.as_string())
    except:
        pass # 如果邮箱不存在，无所谓
    smtp.close()


if __name__ == '__main__':
    # Example:
    # 这里可以任意定制发送者的邮箱地址
    send_mail(['Naibo <naibowang@foxmail.com>'], 'Currency Market <validator@currencymarket.naibo.wang>', 'Hello Python!',
              'Say hello to Python! :)', [])
