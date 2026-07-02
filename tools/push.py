#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键推送 + 创建 Release 脚本
用法: python tools/push.py "发布说明" v1.2.6 "Release 标题" --remote github --token xxx
"""

import os
import sys
import json
import subprocess
import urllib.request
import urllib.error
import base64


def print_flush(msg):
    print(msg)
    sys.stdout.flush()


def run_cmd(cmd):
    print_flush(f"ℹ️ 执行: {' '.join(cmd)}")
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = "echo"
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.stdout:
        print_flush(result.stdout.strip())
    if result.stderr:
        print_flush(result.stderr.strip())
    return result.returncode, result.stdout, result.stderr


def create_github_release(repo, tag, title, body, token):
    """创建 GitHub Release"""
    url = f"https://api.github.com/repos/{repo}/releases"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "tag_name": tag,
        "name": title,
        "body": body,
        "draft": False,
        "prerelease": False
    }
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            print_flush(f"✅ GitHub Release 创建成功: {result.get('html_url', '')}")
            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        print_flush(f"❌ GitHub Release 创建失败: {error_body}")
        return False


def create_gitee_release(repo, tag, title, body, token):
    """创建 Gitee Release"""
    # Gitee 仓库格式：owner/repo
    url = f"https://gitee.com/api/v5/repos/{repo}/releases"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "access_token": token,
        "tag_name": tag,
        "name": title,
        "body": body,
        "draft": False,
        "prerelease": False
    }
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            print_flush(f"✅ Gitee Release 创建成功: {result.get('html_url', '')}")
            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        print_flush(f"❌ Gitee Release 创建失败: {error_body}")
        return False


def main():
    if len(sys.argv) < 5:
        print_flush("❌ 参数不足！")
        print_flush("用法: python tools/push.py \"发布说明\" v1.2.6 \"Release 标题\" --remote github --token xxx")
        sys.exit(1)

    notes = sys.argv[1]
    version = sys.argv[2]
    release_title = sys.argv[3]

    remote = "github"
    token = None

    # 解析 --remote 和 --token
    for i, arg in enumerate(sys.argv):
        if arg == "--remote" and i + 1 < len(sys.argv):
            remote = sys.argv[i + 1]
        if arg == "--token" and i + 1 < len(sys.argv):
            token = sys.argv[i + 1]

    if not token:
        print_flush("❌ 未提供 Token！请使用 --token 参数")
        sys.exit(1)

    root = os.getcwd()
    print_flush(f"ℹ️ 当前目录: {root}")
    print_flush(f"ℹ️ 目标远程仓库: {remote}")

    code, branch, _ = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if code != 0:
        print_flush("❌ 无法获取当前分支")
        sys.exit(1)
    print_flush(f"ℹ️ 当前分支: {branch.strip()}")

    print_flush("\n" + "=" * 50)
    print_flush("📋 变更文件:")
    print_flush("=" * 50)
    run_cmd(["git", "status", "--short"])

    print_flush("\n→ 添加所有文件...")
    code, _, _ = run_cmd(["git", "add", "."])
    if code != 0:
        print_flush("❌ git add 失败")
        sys.exit(1)
    print_flush("✅ 完成")

    print_flush(f"\n→ 提交: {notes}...")
    code, _, _ = run_cmd(["git", "commit", "-m", notes])
    if code != 0:
        print_flush("❌ git commit 失败")
        sys.exit(1)
    print_flush("✅ 完成")

    print_flush(f"\n→ 推送到 {remote}...")
    code, _, _ = run_cmd(["git", "push", remote, branch.strip()])
    if code != 0:
        print_flush(f"❌ git push {remote} 失败")
        sys.exit(1)
    print_flush("✅ 完成")

    tag_name = version
    print_flush(f"\n→ 打标签: {tag_name}...")
    code, _, _ = run_cmd(["git", "tag", tag_name])
    if code != 0:
        print_flush("❌ git tag 失败")
        sys.exit(1)

    print_flush(f"\n→ 推送标签到 {remote}...")
    code, _, _ = run_cmd(["git", "push", remote, tag_name])
    if code != 0:
        print_flush(f"❌ git push {remote} tag 失败")
        sys.exit(1)
    print_flush("✅ 完成")

    # 创建 Release
    print_flush(f"\n→ 创建 Release...")
    repo = "Cherish95279/DesktopWidget" if remote == "github" else "Cherish95279/DesktopWidget"

    if remote == "github":
        success = create_github_release(repo, tag_name, release_title, notes, token)
    else:
        success = create_gitee_release(repo, tag_name, release_title, notes, token)

    if not success:
        print_flush("⚠️ Release 创建失败，但代码和标签已推送")
        sys.exit(1)

    print_flush("\n" + "=" * 50)
    print_flush("✅ 全部完成！")
    print_flush("=" * 50)
    print_flush(f"   - 发布说明: {notes}")
    print_flush(f"   - 版本: {version}")
    print_flush(f"   - Release 标题: {release_title}")
    print_flush(f"   - 远程仓库: {remote}")
    print_flush(f"   - 分支: {branch.strip()}")


if __name__ == "__main__":
    main()