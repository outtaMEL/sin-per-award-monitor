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

## GitHub Actions（关机也能监控）

把代码推到 GitHub 后，由云端每 **3 小时**自动查票，有票推微信。**电脑可以关。**

### 1. 导出 Cloudflare 登录态（本机做一次）

```bash
source .venv/bin/activate
python scripts/export_storage_state.py
```

终端会输出一长串 Base64，复制备用。

### 2. 创建 GitHub 仓库并推送

```bash
cd "/Users/outtamel/Desktop/CursorProjects/singapore air"
git init
git add .
git commit -m "Add SIN-PER award monitor"
# 在 github.com 新建空仓库后：
git remote add origin https://github.com/你的用户名/仓库名.git
git branch -M main
git push -u origin main
```

### 3. 配置 Secrets

仓库 → **Settings → Secrets and variables → Actions → New repository secret**

| Secret 名称 | 内容 |
|-------------|------|
| `SERVERCHAN_SENDKEY` | Server酱 SendKey |
| `PLAYWRIGHT_STORAGE_STATE` | 上一步复制的整段 Base64 |

### 4. 手动试跑

仓库 → **Actions** → **SIN-PER Award Monitor** → **Run workflow**

成功后每 3 小时自动运行。登录态大约 **1–2 周**会过期，查票失败时重新运行 `export_storage_state.py` 更新 Secret。

> 免费 Server酱 每天约 5 条推送；只有**发现新票**才消耗，正常够用。

### ⚠️ GitHub 云端跑的限制

GitHub 免费服务器的 IP 常被 seats.aero 的 Cloudflare **直接拦截**，即使导入了登录态也可能 403。  
若 Actions 报错 `Sorry, you have been blocked`，属于正常现象，不是配置错了。

**关机还要监控的替代方案：**

1. **seats.aero 网页免费 Alert**（最省事，他们服务器查票）
2. **腾讯云/阿里云轻量服务器**（约 ¥30/月，跑同一套脚本）
3. **Mac 自托管 GitHub Runner**（电脑开着时自动查，见下方）

#### Mac 自托管 Runner（电脑开着即可，不用关终端）

```bash
# 在 Mac 上一次性安装
gh api repos/outtaMEL/sin-per-award-monitor/actions/runners/registration-token --method POST
# 按 GitHub 页面提示下载 runner，或访问：
# https://github.com/outtaMEL/sin-per-award-monitor/settings/actions/runners/new
```

把 workflow 的 `runs-on: ubuntu-latest` 改成 `runs-on: self-hosted` 后，用你家宽带的 IP 查票，成功率更高。

## 说明

- seats.aero 数据有缓存延迟（通常数小时），有票后请**立即登录新航官网核实**
- 请勿高频轮询，避免 IP 被 Cloudflare 封禁
- Business Saver 通过里程上限判断（SIN-PER 标准 Saver 约 62,500 里程）
- 当前若 seats.aero 缓存中无 KrisFlyer 数据，脚本会报告「暂无票」——属正常情况
