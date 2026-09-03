# Emby 自动签到脚本

自动签到 https://embys.vincent253.us.ci/ ，支持 Telegram 通知和 GitHub 记录推送。

## 功能

- 自动登录 Emby 站点
- 每日自动签到
- Telegram 通知（成功/失败）
- GitHub 签到记录推送

## 配置

### 依赖

```bash
pip install playwright requests
playwright install chromium
```

## 用法

```bash
# 单次运行
python embys_checkin.py

# 定时运行（每天 09:00）
python embys_checkin.py --cron
```

## 部署到 GitHub Actions

创建 .github/workflows/checkin.yml：

```yaml
name: Emby Checkin
on:
  schedule:
    - cron: '0 1 * * *'
  workflow_dispatch:

jobs:
  checkin:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install playwright requests
          playwright install chromium
      - name: Run checkin
        env:
          GITHUB_TOKEN: secrets.GITHUB_TOKEN
        run: python embys_checkin.py
```

## 日志

签到记录会推送到 stephenhklin-byte/embys-auto-checkin 仓库的 checkin_log.md。