#!/usr/bin/env python3
"""发送一条 Server酱 测试推送。"""

from dotenv import load_dotenv
import os
import sys

from notifier import NotifyConfig, send_alert

load_dotenv()

key = os.getenv("SERVERCHAN_SENDKEY", "").strip()
if not key:
    sys.exit("请先在 .env 填写 SERVERCHAN_SENDKEY")

send_alert(
    "Server酱 测试成功。\n\nSIN→PER Business Saver 监控已就绪。",
    config=NotifyConfig(serverchan_sendkey=key),
    subject="新航监控测试",
)
print("已发送，请查看微信。")
