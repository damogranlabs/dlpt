"""
Basic functions to simplify sending emails.
"""
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import smtplib
import ssl
from typing import List

import dlpt


MAX_ATTACHMENTS_SIZE_KB = 24e3


class Sender():
    def __init__(self, mail: str, pwd: str, smtp: str, smtpPort: int = 465):
        self.mail = mail
        self.pwd = pwd
        self.smtp = smtp
        self.smtpPort = smtpPort


class Data():
    def __init__(self):
        self.recipients: List[str] = []
        self.recipientsCc: List[str] = []

        self.subject: str = "/"
        self.content: str = "/"
        self.isHtml: bool = True

        self.attachments: List[str] = []  # list of attachments (abs file paths)

    def checkAttachmentsFileSize(self):
        """
        Raise exception if attachments size exceeds MAX_ATTACHMENTS_SIZE_KB.
        """
        attachmentsSizeKb = 0
        for attachment in self.attachments:
            attachmentsSizeKb += round(os.path.getsize(attachment) / 1024)

        if attachmentsSizeKb >= MAX_ATTACHMENTS_SIZE_KB:
            errorMsg = f"Email attachments exceeds {MAX_ATTACHMENTS_SIZE_KB} KB: {self.attachments}"
            raise Exception(errorMsg)


def send(sender: Sender, cfgData: Data):
    """
    Send email with given data.
        @param sender: object with all relevant sender email data info.
        @param cfgData: object with all relevant email data.
    """
    # Create a multipart message and set headers
    message = MIMEMultipart()
    message["From"] = sender.mail
    message["To"] = ','.join(cfgData.recipients)
    message["Cc"] = ','.join(cfgData.recipientsCc)

    # prepare subject and data
    message["Subject"] = cfgData.subject
    if cfgData.isHtml:
        dataType = "HTML"
    else:
        dataType = "plain"
    data = MIMEText(cfgData.content, dataType)
    message.attach(data)

    # handle attachments
    for attachment in cfgData.attachments:
        cfgData.checkAttachmentsFileSize()
        data = _toBinary(attachment)
        message.attach(data)

    # Execute (multipart) email transfer by logging into server using secure context
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(sender.smtp, sender.smtpPort, context=context) as server:
        server.login(sender.mail, sender.pwd)

        recipients = []
        recipients.extend(cfgData.recipients)
        recipients.extend(cfgData.recipientsCc)
        text = message.as_string()
        server.sendmail(sender.mail, recipients, text)


def _toBinary(filePath: str) -> MIMEBase:
    """
    Get binary file representation (as expected by email lib) 
        @param filePath: path to a file to encode.
    """
    dlpt.pth.check(filePath)

    part = None
    # Open file in binary mode
    with open(filePath, "rb") as fHandler:
        content = fHandler.read()
        part = MIMEBase("application", "octet-stream")
        part.set_payload(content)

    encoders.encode_base64(part)  # Encode file in ASCII characters to send by email

    # Add header as key/value pair to attachment part
    fileName = dlpt.pth.getName(filePath)
    part.add_header("Content-Disposition", f"attachment; filename=\"{fileName}\"")

    return part
