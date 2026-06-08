"""通知：微信（PushPlus / Server酱）、邮件、Telegram 或终端输出。"""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.mime.text import MIMEText

import requests


@dataclass(frozen=True)
class NotifyConfig:
    pushplus_token: str | None = None
    serverchan_sendkey: str | None = None
    wework_webhook: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    email_from: str | None = None
    email_to: str | None = None
    bot_token: str | None = None
    chat_id: str | None = None


def _send_pushplus(text: str, *, title: str, token: str) -> None:
    resp = requests.post(
        "https://www.pushplus.plus/send",
        json={"token": token, "title": title, "content": text, "template": "txt"},
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("code") != 200:
        raise RuntimeError(f"PushPlus 失败: {payload.get('msg', payload)}")


def _send_serverchan(text: str, *, title: str, sendkey: str) -> None:
    resp = requests.post(
        f"https://sctapi.ftqq.com/{sendkey}.send",
        data={"title": title, "desp": text},
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("code") != 0:
        raise RuntimeError(f"Server酱 失败: {payload.get('message') or payload}")


def _send_wework(text: str, *, webhook: str) -> None:
    resp = requests.post(
        webhook,
        json={"msgtype": "text", "text": {"content": text}},
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("errcode", 0) != 0:
        raise RuntimeError(f"企业微信 失败: {payload.get('errmsg', payload)}")


def _send_telegram(text: str, *, bot_token: str, chat_id: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=30,
    )
    resp.raise_for_status()


def _send_email(
    text: str,
    *,
    subject: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    email_from: str,
    email_to: str,
) -> None:
    msg = MIMEText(text, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = email_to

    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(email_from, [email_to], msg.as_string())
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_password)
            server.sendmail(email_from, [email_to], msg.as_string())


def send_alert(
    text: str,
    *,
    config: NotifyConfig,
    subject: str = "新航积分票提醒 SIN→PER",
) -> None:
    """打印到终端，并按配置推送到微信 / 邮件 / Telegram。"""
    print(text)

    if config.pushplus_token:
        _send_pushplus(text, title=subject, token=config.pushplus_token)

    if config.serverchan_sendkey:
        _send_serverchan(text, title=subject, sendkey=config.serverchan_sendkey)

    if config.wework_webhook:
        _send_wework(text, webhook=config.wework_webhook)

    if config.smtp_host and config.smtp_user and config.smtp_password and config.email_to:
        sender = config.email_from or config.smtp_user
        _send_email(
            text,
            subject=subject,
            smtp_host=config.smtp_host,
            smtp_port=config.smtp_port,
            smtp_user=config.smtp_user,
            smtp_password=config.smtp_password,
            email_from=sender,
            email_to=config.email_to,
        )

    if config.bot_token and config.chat_id:
        _send_telegram(text, bot_token=config.bot_token, chat_id=config.chat_id)
