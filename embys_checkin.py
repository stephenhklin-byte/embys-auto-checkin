#!/usr/bin/env python3
"""
Emby 签到自动脚本 - 定时运行版本
目标: https://embys.vincent253.us.ci/
账号: kok123 / Kok123123
通知: Telegram (chat_id: 7011731940)
GitHub: stephenhklin-byte/embys-auto-checkin

依赖:
    pip install playwright requests
    playwright install chromium

用法:
    python embys_checkin.py          # 单次运行
    python embys_checkin.py --cron   # 定时运行（每天09:00）
"""

import asyncio
import sys
import os
import io
import json
import time
import base64
import requests
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ==================== 配置 ====================
BASE_URL = "https://embys.vincent253.us.ci/"
USERNAME = "kok123"
PASSWORD = "Kok123123"

TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "7011731940")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "stephenhklin-byte/embys-auto-checkin")
GITHUB_BRANCH = "main"


# ==================== 通知函数 ====================
def send_telegram(message, parse_mode="HTML"):
    """发送 Telegram 通知"""
    try:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TG_CHAT_ID, "text": message, "parse_mode": parse_mode}
        resp = requests.post(url, json=data, timeout=10)
        if resp.status_code == 200:
            print("  📱 Telegram 通知已发送")
            return True
        else:
            print(f"  ⚠️ Telegram 发送失败: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"  ⚠️ Telegram 异常: {e}")
        return False


def push_to_github(content, filename="checkin_log.md"):
    """推送签到记录到 GitHub"""
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            existing = base64.b64decode(resp.json()["content"]).decode("utf-8")
            new_content = existing + f"\n\n---\n\n{content}"
            sha = resp.json()["sha"]
        elif resp.status_code == 404:
            new_content = content
            sha = None
        else:
            print(f"  ⚠️ GitHub API 错误: {resp.status_code}")
            return False

        data = {
            "message": f"checkin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "content": base64.b64encode(new_content.encode("utf-8")).decode("utf-8"),
            "branch": GITHUB_BRANCH,
        }
        if sha:
            data["sha"] = sha

        resp = requests.put(url, json=data, headers=headers, timeout=10)
        if resp.status_code in (200, 201):
            print("  📤 GitHub 推送成功")
            return True
        else:
            print(f"  ⚠️ GitHub 推送失败: {resp.status_code} {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"  ⚠️ GitHub 推送异常: {e}")
        return False


# ==================== 签到核心 ====================
async def login(page):
    """登录"""
    print("[1/3] 正在登录...")
    await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
    await page.wait_for_timeout(2000)

    content = await page.content()
    if "晚上好" in content or "已签" in content:
        print("  已登录，跳过登录步骤")
        return True

    # 用户名
    for sel in ['input[type="text"]', 'input[name="username"]', '#username',
                'input[placeholder*="用户名"]', 'input[placeholder*="账号"]']:
        try:
            el = await page.query_selector(sel)
            if el:
                await el.fill(USERNAME)
                print(f"  已输入用户名: {USERNAME}")
                break
        except:
            continue

    # 密码
    for sel in ['input[type="password"]', 'input[name="password"]', '#password',
                'input[placeholder*="密码"]']:
        try:
            el = await page.query_selector(sel)
            if el:
                await el.fill(PASSWORD)
                print("  已输入密码")
                break
        except:
            continue

    # 登录按钮
    btn = await page.query_selector('button:has-text("登录"), input[type="submit"], button[type="submit"]')
    if btn:
        await btn.click()
        print("  已点击登录按钮")
        await page.wait_for_timeout(3000)
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
        except:
            pass
    else:
        await page.press('input[type="password"]', "Enter")
        print("  已按回车提交")
        await page.wait_for_timeout(3000)

    return True


async def check_in(page):
    """执行签到"""
    print("[2/3] 正在签到...")
    try:
        await page.goto(BASE_URL + "home", wait_until="domcontentloaded", timeout=15000)
    except:
        pass
    await page.wait_for_timeout(2000)

    # 查找签到按钮
    sign_button = None
    for text in ["签到", "已签", "签", "打卡"]:
        try:
            btn = await page.query_selector(f'button:has-text("{text}")')
            if btn:
                sign_button = btn
                print(f"  找到签到按钮: {text}")
                break
        except:
            continue

    if not sign_button:
        btn_info = await page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('button'));
            for (const b of btns) {
                const t = b.textContent.trim();
                if (t.includes('签') || t.includes('打卡')) {
                    return {text: t, disabled: b.disabled};
                }
            }
            return null;
        }""")
        if btn_info and not btn_info.get('disabled'):
            sign_button = await page.query_selector(f'button:has-text("{btn_info["text"]}")')

    if not sign_button:
        print("  未找到签到按钮")
        return False

    is_disabled = await sign_button.is_disabled()
    btn_text = await sign_button.text_content()

    if is_disabled or "已签" in btn_text:
        print(f"  今日已签到: {btn_text.strip()}")
        return True

    await sign_button.click()
    print(f"  已点击签到: {btn_text.strip()}")
    await page.wait_for_timeout(3000)
    return True


async def verify_checkin(page):
    """验证签到状态"""
    print("[3/3] 验证签到状态...")
    try:
        await page.goto(BASE_URL + "home", wait_until="domcontentloaded", timeout=15000)
    except:
        pass
    await page.wait_for_timeout(2000)

    result = await page.evaluate("""() => {
        const btns = Array.from(document.querySelectorAll('button'));
        for (const b of btns) {
            const t = b.textContent.trim();
            if (t.includes('签')) return {text: t, disabled: b.disabled};
        }
        return null;
    }""")

    if result:
        print(f"  签到状态: {result['text']} (disabled={result['disabled']})")
        return "已签" in result['text']
    return False


# ==================== 主流程 ====================
async def run_once():
    """执行一次签到"""
    result = {"success": False, "message": "", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            if not await login(page):
                result["message"] = "登录失败"
                send_telegram(f"❌ <b>Emby签到失败</b>\n时间: {result['timestamp']}\n账号: {USERNAME}\n原因: 登录失败")
                return result

            if not await check_in(page):
                result["message"] = "签到失败"
                send_telegram(f"❌ <b>Emby签到失败</b>\n时间: {result['timestamp']}\n账号: {USERNAME}\n原因: 签到失败")
                return result

            verified = await verify_checkin(page)
            if verified:
                result["success"] = True
                result["message"] = "签到成功"
                print("\n✅ 签到成功！")
                send_telegram(f"✅ <b>Emby签到成功</b>\n时间: {result['timestamp']}\n账号: {USERNAME}\n状态: 已签到")
            else:
                result["message"] = "签到状态未确认"
                print("\n⚠️ 签到状态未确认")
                send_telegram(f"⚠️ <b>Emby签到状态未确认</b>\n时间: {result['timestamp']}\n账号: {USERNAME}")

            await browser.close()
        except Exception as e:
            result["message"] = str(e)
            print(f"\n❌ 发生错误: {e}")
            send_telegram(f"❌ <b>Emby签到异常</b>\n时间: {result['timestamp']}\n账号: {USERNAME}\n错误: {str(e)[:200]}")
            await browser.close()

    # GitHub 推送
    if result["success"]:
        log = f"""# Emby 签到记录

## {result['timestamp']}

- **状态**: ✅ 签到成功
- **账号**: {USERNAME}
- **目标**: {BASE_URL}

---
"""
        push_to_github(log)

    return result


async def run_cron():
    """定时运行：每天 09:00 执行"""
    print("cron 模式已启动，每天 09:00 自动签到...")
    while True:
        now = datetime.now()
        target = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)

        wait_seconds = (target - now).total_seconds()
        print(f"  距离下次签到还有 {int(wait_seconds / 3600)} 小时 {int((wait_seconds % 3600) / 60)} 分钟")
        await asyncio.sleep(wait_seconds)

        print(f"\n{'=' * 50}")
        print(f"定时签到: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 50}")
        await run_once()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cron":
        asyncio.run(run_cron())
    else:
        asyncio.run(run_once())