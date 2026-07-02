#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键推送脚本
用法: python tools/push.py "提交信息" [tag]
"""

import os
import sys
import subprocess


def print_flush(msg):
    """打印并立即刷新输出缓冲"""
    print(msg)
    sys.stdout.flush()


def run_cmd(cmd, capture=True):
    """执行命令并实时输出（强制刷新，禁用交互）"""
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


def main():
    if len(sys.argv) < 2:
        print_flush("❌ 请指定提交信息！")
        print_flush("用法: python tools/push.py \"提交信息\" [tag]")
        sys.exit(1)

    msg = sys.argv[1]
    with_tag = len(sys.argv) > 2 and sys.argv[2] == "tag"

    root = os.getcwd()
    print_flush(f"ℹ️ 当前目录: {root}")

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

    print_flush(f"\n→ 提交: {msg}...")
    code, _, _ = run_cmd(["git", "commit", "-m", msg])
    if code != 0:
        print_flush("❌ git commit 失败")
        sys.exit(1)
    print_flush("✅ 完成")

    print_flush(f"\n→ 推送到 {branch.strip()}...")
    code, _, _ = run_cmd(["git", "push", "origin", branch.strip()])
    if code != 0:
        print_flush("❌ git push 失败")
        sys.exit(1)
    print_flush("✅ 完成")

    if with_tag:
        print_flush("\n→ 打标签...")
        constants_path = os.path.join(root, "src", "constants.py")
        version = "unknown"
        if os.path.exists(constants_path):
            with open(constants_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('VERSION = '):
                        version = line.split('"')[1]
                        break
        tag_name = version
        print_flush(f"  标签名: {tag_name}")

        code, _, _ = run_cmd(["git", "tag", tag_name])
        if code != 0:
            print_flush("❌ git tag 失败")
            sys.exit(1)

        print_flush("\n→ 推送标签...")
        code, _, _ = run_cmd(["git", "push", "origin", tag_name])
        if code != 0:
            print_flush("❌ git push tag 失败")
            sys.exit(1)
        print_flush("✅ 完成")

    print_flush("\n" + "=" * 50)
    print_flush("✅ 全部完成！")
    print_flush("=" * 50)
    print_flush(f"   - 提交: {msg}")
    print_flush(f"   - 分支: {branch.strip()}")


if __name__ == "__main__":
    main()