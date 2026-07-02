#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键推送 + 创建 Release（GitHub 自动上传 exe，Gitee 手动上传）
用法: python tools/push.py "发布说明" v1.2.6 "Release 标题" --remote github --token xxx
"""

import os
import sys
import json
import glob
import subprocess
import urllib.request
import urllib.error
import requests


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
        for line in result.stdout.strip().split('\n'):
            if line:
                print_flush(f"  {line}")
    if result.stderr:
        for line in result.stderr.strip().split('\n'):
            if line:
                print_flush(f"  [错误] {line}")
    return result.returncode, result.stdout, result.stderr


def find_exe_file(project_root, version):
    dist_dir = os.path.join(project_root, "dist")
    if not os.path.exists(dist_dir):
        print_flush(f"⚠️ dist 目录不存在: {dist_dir}")
        return None
    pattern = f"DesktopWidget-v{version.lstrip('v')}-win64-Cherish-Setup.exe"
    exe_path = os.path.join(dist_dir, pattern)
    if os.path.exists(exe_path):
        return exe_path
    exe_files = glob.glob(os.path.join(dist_dir, "DesktopWidget-v*.exe"))
    if exe_files:
        exe_files.sort(key=os.path.getmtime, reverse=True)
        print_flush(f"ℹ️ 使用最新的 exe 文件: {os.path.basename(exe_files[0])}")
        return exe_files[0]
    print_flush(f"⚠️ 未找到 exe 文件")
    return None


def upload_github_asset(repo, release_id, file_path, token):
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    print_flush(f"  📤 上传 {file_name} ({file_size / 1024 / 1024:.1f} MB) 到 GitHub...")
    url = f"https://uploads.github.com/repos/{repo}/releases/{release_id}/assets?name={file_name}"
    headers = {"Authorization": f"token {token}", "Content-Type": "application/octet-stream"}
    with open(file_path, 'rb') as f:
        file_data = f.read()
    req = urllib.request.Request(url, data=file_data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            print_flush(f"  ✅ 上传成功: {result.get('browser_download_url', '')}")
            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        if "already_exists" in error_body:
            print_flush(f"  ℹ️ 文件已存在，跳过上传")
            return True
        print_flush(f"  ❌ 上传失败: {error_body}")
        return False


def get_github_release_id(repo, tag, token):
    url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    try:
        req = urllib.request.Request(url, headers=headers, method='GET')
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('id')
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print_flush(f"  ℹ️ 未找到已有的 Release: {tag}")
            return None
        print_flush(f"  ❌ 获取 Release ID 失败: {e}")
        return None


def get_gitee_release_id(repo, tag, token):
    url = f"https://gitee.com/api/v5/repos/{repo}/releases"
    params = {"access_token": token, "per_page": 100}
    try:
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            print_flush(f"  ❌ 获取 Release 列表失败: HTTP {resp.status_code}")
            return None
        releases = resp.json()
        for release in releases:
            if release.get('tag_name') == tag:
                return release.get('id')
        print_flush(f"  ℹ️ 未找到 tag '{tag}' 对应的 Release")
        return None
    except Exception as e:
        print_flush(f"  ❌ 获取 Gitee Release ID 异常: {e}")
        return None


def create_github_release(repo, tag, title, body, token):
    url = f"https://api.github.com/repos/{repo}/releases"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    data = {"tag_name": tag, "name": title, "body": body, "draft": False, "prerelease": False}
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            print_flush(f"  ✅ Release 创建成功: {result.get('html_url', '')}")
            return result.get('id')
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        if "already_exists" in error_body:
            print_flush(f"  ℹ️ Release 已存在，尝试获取已有 Release ID...")
            return get_github_release_id(repo, tag, token)
        print_flush(f"  ❌ Release 创建失败: {error_body}")
        return None


def create_gitee_release(repo, tag, title, body, token):
    url = f"https://gitee.com/api/v5/repos/{repo}/releases"
    headers = {"Content-Type": "application/json"}
    data = {"access_token": token, "tag_name": tag, "name": title, "body": body, "target_commitish": "main", "draft": False, "prerelease": False}
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            print_flush(f"  ✅ Release 创建成功: {result.get('html_url', '')}")
            return result.get('id')
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        if "已经存在" in error_body or "already" in error_body:
            print_flush(f"  ℹ️ Release 已存在，尝试获取已有 Release ID...")
            return get_gitee_release_id(repo, tag, token)
        print_flush(f"  ❌ Release 创建失败: {error_body}")
        return None


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

    for i, arg in enumerate(sys.argv):
        if arg == "--remote" and i + 1 < len(sys.argv):
            remote = sys.argv[i + 1]
        if arg == "--token" and i + 1 < len(sys.argv):
            token = sys.argv[i + 1]

    if not token:
        print_flush("❌ 未提供 Token！请使用 --token 参数")
        sys.exit(1)

    if remote == "github":
        remote_name = "origin"
        repo = "Cherish95279/DesktopWidget"
    else:
        remote_name = "gitee"
        repo = "Cherish95279/DesktopWidget"

    root = os.getcwd()
    print_flush(f"ℹ️ 当前目录: {root}")
    print_flush(f"ℹ️ 目标远程仓库: {remote_name} ({remote})")

    code, branch, _ = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if code != 0:
        print_flush("❌ 无法获取当前分支")
        sys.exit(1)
    branch = branch.strip()
    print_flush(f"ℹ️ 当前分支: {branch}")

    exe_path = find_exe_file(root, version)
    if exe_path:
        print_flush(f"ℹ️ 找到 exe 文件: {os.path.basename(exe_path)}")
    else:
        print_flush(f"⚠️ 未找到 exe 文件")

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
    code, stdout, _ = run_cmd(["git", "commit", "-m", notes])
    if code != 0:
        if "nothing to commit" in stdout or "nothing to commit" in str(stdout):
            print_flush("ℹ️ 没有新的变更需要提交，跳过提交步骤")
        else:
            print_flush("❌ git commit 失败")
            sys.exit(1)
    else:
        print_flush("✅ 完成")

    print_flush(f"\n→ 推送到 {remote_name}...")
    code, _, _ = run_cmd(["git", "push", remote_name, branch])
    if code != 0:
        print_flush(f"❌ git push {remote_name} 失败")
        sys.exit(1)
    print_flush("✅ 完成")

    tag_name = version
    print_flush(f"\n→ 打标签: {tag_name}...")
    code, stdout, stderr = run_cmd(["git", "tag", tag_name])
    if code != 0:
        if "already exists" in stderr or "already exists" in stdout:
            print_flush(f"ℹ️ 标签 {tag_name} 已存在，跳过")
        else:
            print_flush("❌ git tag 失败")
            sys.exit(1)
    else:
        print_flush("✅ 完成")

    print_flush(f"\n→ 推送标签到 {remote_name}...")
    code, _, _ = run_cmd(["git", "push", remote_name, tag_name])
    if code != 0:
        print_flush(f"⚠️ git push {remote_name} tag 失败，继续...")
    else:
        print_flush("✅ 完成")

    print_flush(f"\n→ 创建 Release...")
    release_id = None
    if remote == "github":
        release_id = create_github_release(repo, tag_name, release_title, notes, token)
    else:
        release_id = create_gitee_release(repo, tag_name, release_title, notes, token)

    if not release_id:
        print_flush("⚠️ 无法获取 Release ID，跳过 exe 上传")
    else:
        if exe_path and os.path.exists(exe_path):
            if remote == "github":
                print_flush("\n→ 上传 exe 文件...")
                success = upload_github_asset(repo, release_id, exe_path, token)
                if success:
                    print_flush("✅ exe 上传完成！")
                else:
                    print_flush("⚠️ exe 上传失败，请手动上传")
            else:
                # Gitee：不自动上传，给出清晰的手动指引
                print_flush("\n" + "=" * 50)
                print_flush("📌 Gitee 手动上传指引")
                print_flush("=" * 50)
                print_flush(f"   Release 已创建，请手动上传 exe 文件：")
                print_flush(f"   1. 打开链接：")
                print_flush(f"      https://gitee.com/{repo}/releases/edit/{release_id}")
                print_flush(f"   2. 在页面下方「附件」区域拖拽上传：")
                print_flush(f"      {exe_path}")
                print_flush("=" * 50)
        else:
            print_flush("\nℹ️ 没有 exe 文件需要上传")

    print_flush("\n" + "=" * 50)
    print_flush("✅ 全部完成！")
    print_flush("=" * 50)
    print_flush(f"   - 发布说明: {notes}")
    print_flush(f"   - 版本: {version}")
    print_flush(f"   - Release 标题: {release_title}")
    print_flush(f"   - 远程仓库: {remote_name} ({remote})")
    print_flush(f"   - 分支: {branch}")
    if exe_path:
        if remote == "github":
            print_flush(f"   - exe 文件: {os.path.basename(exe_path)} ✅ 已自动上传")
        else:
            print_flush(f"   - exe 文件: {os.path.basename(exe_path)} ⚠️ 请按上方指引手动上传")


if __name__ == "__main__":
    main()