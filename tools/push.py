#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键推送 + 创建 Release + 自动上传 exe（支持 Release 已存在时重试）
用法: python tools/push.py "发布说明" v1.2.6 "Release 标题" --remote github --token xxx
"""

import os
import sys
import json
import glob
import subprocess
import urllib.request
import urllib.error
import base64
import requests  # 需要安装 requests 库


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
    """查找 dist 目录下的 exe 文件"""
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
    """上传文件到 GitHub Release"""
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    print_flush(f"  📤 上传 {file_name} ({file_size / 1024 / 1024:.1f} MB) 到 GitHub...")

    url = f"https://uploads.github.com/repos/{repo}/releases/{release_id}/assets?name={file_name}"
    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/octet-stream"
    }

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


def upload_gitee_asset(repo, release_id, file_path, token):
    """上传文件到 Gitee Release（使用 requests 库）"""
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    print_flush(f"  📤 上传 {file_name} ({file_size / 1024 / 1024:.1f} MB) 到 Gitee...")

    if not release_id:
        print_flush(f"  ❌ release_id 为空，无法上传")
        return False

    url = f"https://gitee.com/api/v5/repos/{repo}/releases/{release_id}/assets"
    params = {
        "access_token": token
    }
    files = {
        "file": (file_name, open(file_path, 'rb'), 'application/octet-stream')
    }
    try:
        resp = requests.post(url, params=params, files=files)
        if resp.status_code in (200, 201):
            result = resp.json()
            print_flush(f"  ✅ 上传成功: {result.get('browser_download_url', '')}")
            return True
        else:
            error_text = resp.text
            if "已存在" in error_text or "already exists" in error_text:
                print_flush(f"  ℹ️ 文件已存在，跳过上传")
                return True
            print_flush(f"  ❌ 上传失败: HTTP {resp.status_code} - {error_text}")
            return False
    except Exception as e:
        print_flush(f"  ❌ 上传异常: {e}")
        return False


def get_github_release_id(repo, tag, token):
    """获取 GitHub Release ID（通过 API）"""
    url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
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
    """获取 Gitee Release ID（通过 API）"""
    url = f"https://gitee.com/api/v5/repos/{repo}/releases/tags/{tag}"
    params = {
        "access_token": token
    }
    try:
        resp = requests.get(url, params=params)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('id')
        elif resp.status_code == 404:
            print_flush(f"  ℹ️ 未找到已有的 Gitee Release: {tag}")
            return None
        else:
            print_flush(f"  ❌ 获取 Gitee Release ID 失败: HTTP {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print_flush(f"  ❌ 获取 Gitee Release ID 异常: {e}")
        return None


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
    """创建 Gitee Release"""
    url = f"https://gitee.com/api/v5/repos/{repo}/releases"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "access_token": token,
        "tag_name": tag,
        "name": title,
        "body": body,
        "target_commitish": "main",
        "draft": False,
        "prerelease": False
    }
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

    # 远程仓库名称映射
    if remote == "github":
        remote_name = "origin"
        repo = "Cherish95279/DesktopWidget"
    else:
        remote_name = "gitee"
        repo = "Cherish95279/DesktopWidget"

    root = os.getcwd()
    print_flush(f"ℹ️ 当前目录: {root}")
    print_flush(f"ℹ️ 目标远程仓库: {remote_name} ({remote})")

    # 获取分支名
    code, branch, _ = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if code != 0:
        print_flush("❌ 无法获取当前分支")
        sys.exit(1)
    branch = branch.strip()
    print_flush(f"ℹ️ 当前分支: {branch}")

    # 查找 exe 文件
    exe_path = find_exe_file(root, version)
    if exe_path:
        print_flush(f"ℹ️ 找到 exe 文件: {os.path.basename(exe_path)}")
    else:
        print_flush(f"⚠️ 未找到 exe 文件，将只创建 Release 而不上传附件")

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
        print_flush(f"⚠️ git push {remote_name} tag 失败（可能标签已存在或网络问题），继续...")
    else:
        print_flush("✅ 完成")

    # 创建 Release（如果已存在，则获取已有 ID）
    print_flush(f"\n→ 创建 Release...")

    release_id = None
    if remote == "github":
        release_id = create_github_release(repo, tag_name, release_title, notes, token)
    else:
        release_id = create_gitee_release(repo, tag_name, release_title, notes, token)

    if not release_id:
        print_flush("⚠️ 无法获取 Release ID，跳过 exe 上传")
    else:
        # 上传 exe 文件
        if exe_path and os.path.exists(exe_path):
            print_flush("\n→ 上传 exe 文件...")
            if remote == "github":
                success = upload_github_asset(repo, release_id, exe_path, token)
            else:
                success = upload_gitee_asset(repo, release_id, exe_path, token)

            if success:
                print_flush("✅ exe 上传完成！")
            else:
                print_flush("⚠️ exe 上传失败，但 Release 已创建")
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
        upload_status = "✅ 已上传" if release_id else "⚠️ 未上传（Release ID 缺失）"
        print_flush(f"   - exe 文件: {os.path.basename(exe_path)} {upload_status}")


if __name__ == "__main__":
    main()