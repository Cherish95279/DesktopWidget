#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键发布公告脚本
用法:
  python tools/publish_notice.py "标题" "内容"
  python tools/publish_notice.py "标题" "内容" "链接"
  python tools/publish_notice.py "标题" "内容" "链接" false
"""

import json
import sys
import subprocess
import os
from datetime import datetime

NOTICE_FILE = "notice.json"


def publish_notice(title, content, link=None, show_date=True):
    """发布公告"""
    # 切换到项目根目录（publish_notice.py 在 tools/ 下）
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    # 读取现有公告
    with open(NOTICE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 生成新 ID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_id = f"notice_{timestamp}"

    # 更新时间戳
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

    print(f"✅ 公告已更新:")
    print(f"   ID: {new_id}")
    print(f"   标题: {title}")
    print(f"   内容: {content}")
    print(f"   时间: {now}")

    # 提交并推送
    print("ℹ️ 正在推送到 GitHub...")

    result = subprocess.run(["git", "add", NOTICE_FILE], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ git add 失败: {result.stderr}")
        return False

    result = subprocess.run(["git", "commit", "-m", f"公告: {title}"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ git commit 失败: {result.stderr}")
        return False

    result = subprocess.run(["git", "push"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ git push 失败: {result.stderr}")
        return False

    print("✅ 公告已推送到 GitHub!")
    return True


def main():
    if len(sys.argv) < 3:
        print("用法:")
        print('  python tools/publish_notice.py "标题" "内容"')
        print('  python tools/publish_notice.py "标题" "内容" "链接"')
        print('  python tools/publish_notice.py "标题" "内容" "链接" false')
        sys.exit(1)

    title = sys.argv[1]
    content = sys.argv[2]
    link = sys.argv[3] if len(sys.argv) > 3 else None
    show_date = sys.argv[4].lower() != 'false' if len(sys.argv) > 4 else True

    publish_notice(title, content, link, show_date)


if __name__ == "__main__":
    main()