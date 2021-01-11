from typing import Tuple

import pytest

import dlpt

from dlpt.tfix import *

"""
NOTE: User must manually check specified inbox to see if any emails were sent.
"""
TEST_MAIL = "<email address>"  # example: dlpt@gmail.com
TEST_MAIL_PW = "<account password>"
TEST_MAIL_SMPT = "<email SMTP address>"  # example: "smtp.gmail.com"


def _getTestEmailData() -> Tuple[dlpt.emails.Sender, dlpt.emails.Data]:
    sender = dlpt.emails.Sender(TEST_MAIL, TEST_MAIL_PW, TEST_MAIL_SMPT)
    emailData = dlpt.emails.Data()
    emailData.recipients = [TEST_MAIL]

    return sender, emailData


@pytest.mark.skipif(not dlpt.utils.isDbgSession(), reason="User must check email inbox manually.")
def test_textMailSingleRecipient():
    datum = dlpt.time.getCurrentDateTime(dlpt.time.DATE_FORMAT)
    # send email
    sender, emailData = _getTestEmailData()
    emailData.subject = f"{datum} - textMailSingleRecipient()"
    emailData.content = "This mail should have only one recipient, and no HTML formatting."
    emailData.isHtml = False

    dlpt.emails.send(sender, emailData)


@pytest.mark.skipif(not dlpt.utils.isDbgSession(), reason="User must check email inbox manually.")
def test_textMailMultipleRecipients():
    datum = dlpt.time.getCurrentDateTime(dlpt.time.DATE_FORMAT)
    # send email
    sender, emailData = _getTestEmailData()
    emailData.recipientsCc = ['domen.jurkovic@isystem.si']

    emailData.subject = f"{datum} - textMailMultipleRecipients()"
    emailData.content = f"This mail should have one extra recipient in CC field. No HTML formatting: {emailData.recipientsCc}"
    emailData.isHtml = False

    dlpt.emails.send(sender, emailData)


@pytest.mark.skipif(not dlpt.utils.isDbgSession(), reason="User must check email inbox manually.")
def test_htmlMail():
    datum = dlpt.time.getCurrentDateTime(dlpt.time.DATE_FORMAT)
    # send email
    sender, emailData = _getTestEmailData()
    emailData.subject = f"{datum} - htmlMail()"

    content = "<p>This is html formatted mail:<br />"
    content += f"Proof: Here is a <a href=\"https://xkcd.com\">link</a> that won't work in a usual text mail. </p>"
    emailData.content = content

    dlpt.emails.send(sender, emailData)
