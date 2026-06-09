# SIN → PER KrisFlyer Business Saver 监控

通过 **Playwright** 访问 [seats.aero/singapore](https://seats.aero/singapore) 免费页，调用其内部 API 监控新航 KrisFlyer 商务舱 Saver 余票。

## 监控范围

| 项目 | 默认值 |
|------|--------|
| 航线 | SIN → PER |
| 日期 | 2026-06-28 ~ 2026-07-06 |
| 舱位 | Business Saver（里程 ≤ 70,000） |

## 快速开始

```bash
cd "/Users/outtamel/Desktop/CursorProjects/singapore air"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp config.example.env .env
# 编辑 .env，填入 Server酱 SendKey

python monitor.py --once
```

首次运行会打开浏览器（`HEADLESS=false`），需等待 Cloudflare 验证通过；cookie 保存在 `.browser_data/`，之后可自动复用。

## 持续监控

```bash
python monitor.py
```

默认每 60–90 分钟随机检查一次。发现**新**余票时推送到微信。

## 微信通知配置（Server酱）

1. 打开 [sct.ftqq.com](https://sct.ftqq.com)，**微信扫码**登录
2. 按提示关注 **Server酱** 服务号（消息从这里推过来）
3. 在「SendKey」页面复制 **SendKey**
4. 写入 `.env`：

```env
SERVERCHAN_SENDKEY=你的SendKey
```

有票时微信会收到推送。免费版每日约 5 条，监控提醒够用。

### 其他通知方式（可选）

| 方式 | 配置项 |
|------|--------|
| PushPlus | `PUSHPLUS_TOKEN` |
| 企业微信 | `WEWORK_WEBHOOK` |
| 邮件 | `SMTP_*` |

## 说明

- seats.aero 数据有缓存延迟（通常数小时），有票后请**立即登录新航官网核实**
- 请勿高频轮询，避免 IP 被 Cloudflare 封禁
- Business Saver 通过里程上限判断（SIN-PER 标准 Saver 约 62,500 里程）
- 当前若 seats.aero 缓存中无 KrisFlyer 数据，脚本会报告「暂无票」——属正常情况
