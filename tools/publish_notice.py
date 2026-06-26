#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键发布公告脚本（交互式）
用法:
  python publish_notice.py                    # 交互式输入
  python publish_notice.py "标题" "内容"      # 快速发布（无链接）
  python publish_notice.py "标题" "内容" "链接"   # 快速发布（有链接）
  python publish_notice.py "标题" "内容" "链接" false   # 不显示日期
"""

import json
import sys
import subprocess
import os
from datetime import datetime

NOTICE_FILE = "notice.json"

# 颜色输出
try:
    from colorama import init, Fore, Style
    init()
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    RED = Fore.RED
    RESET = Style.RESET_ALL
except ImportError:
    GREEN = YELLOW = RED = RESET = ""


def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")


def print_info(msg):
    print(f"{YELLOW}ℹ️ {msg}{RESET}")


def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")


def get_notice_from_input():
    """交互式获取公告内容"""
    print("\n" + "=" * 50)
    print("📢 发布新公告")
    print("=" * 50)

    title = input("📌 标题: ").strip()
    if not title:
        print_error("标题不能为空")
        return None

    print_info("支持多行输入，输入空行结束")
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    content = "\n".join(lines) if lines else ""

    if not content:
        print_error("内容不能为空")
        return None

    link = input("🔗 链接（直接回车跳过）: ").strip()
    if not link:
        link = ""

    show_date_input = input("📅 显示日期？（y/n，默认 y）: ").strip().lower()
    show_date = show_date_input != 'n'

    return {
        "title": title,
        "content": content,
        "link": link,
        "show_date": show_date
    }


def publish_notice(title, content, link=None, show_date=True):
    """发布公告"""
    try:
        # 读取现有公告
        with open(NOTICE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 生成新 ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_id = f"notice_{timestamp}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 更新公告数据
        data.update({
            "id": new_id,
            "title": title,
            "content": content,
            "link": link if link else "",
            "timestamp": now,
            "show_date": show_date,
            "enabled": True
        })

        # 写入文件
        with open(NOTICE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print_success(f"公告已更新:")
        print(f"   ID: {new_id}")
        print(f"   标题: {title}")
        print(f"   内容: {content[:50]}{'...' if len(content) > 50 else ''}")
        print(f"   时间: {now}")

        # 提交并推送
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        print_info("正在推送到 GitHub...")

        result = subprocess.run(["git", "add", NOTICE_FILE], capture_output=True, text=True)
        if result.returncode != 0:
            print_error(f"git add 失败: {result.stderr}")
            return False

        result = subprocess.run(["git", "commit", "-m", f"公告: {title}"], capture_output=True, text=True)
        if result.returncode != 0:
            print_error(f"git commit 失败: {result.stderr}")
            return False

        result = subprocess.run(["git", "push"], capture_output=True, text=True)
        if result.returncode != 0:
            print_error(f"git push 失败: {result.stderr}")
            return False

        print_success("公告已推送到 GitHub!")
        print()
        print_info("📢 用户将在下次轮询（60分钟内）看到新公告")
        print_info(f"🔗 验证链接: https://raw.githubusercontent.com/Cherish95279/DesktopWidget/main/notice.json")
        return True

    except Exception as e:
        print_error(f"发布失败: {e}")
        return False


def main():
    # 快速模式（命令行参数）
    if len(sys.argv) >= 3:
        title = sys.argv[1]
        content = sys.argv[2]
        link = sys.argv[3] if len(sys.argv) > 3 else None
        show_date = sys.argv[4].lower() != 'false' if len(sys.argv) > 4 else True
        publish_notice(title, content, link, show_date)
        return

    # 交互式模式
    if len(sys.argv) == 1:
        data = get_notice_from_input()
        if data is None:
            sys.exit(1)
        publish_notice(data["title"], data["content"], data["link"], data["show_date"])
        return

    # 参数不完整
    print("📢 用法:")
    print("")
    print("  交互式（推荐）:")
    print("    python publish_notice.py")
    print("")
    print("  快速模式:")
    print('    python publish_notice.py "标题" "内容"')
    print('    python publish_notice.py "标题" "内容" "链接"')
    print('    python publish_notice.py "标题" "内容" "链接" false')
    print("")
    print("  示例:")
    print('    python publish_notice.py "📢 新版本发布" "v1.2.1 已正式发布"')
    print('    python publish_notice.py "🎉 节日快乐" "端午安康！" "" false')


if __name__ == "__main__":
    main()