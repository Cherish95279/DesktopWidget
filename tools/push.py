#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键推送脚本（仅推送代码，不打标签）
用法: python tools/push.py "提交信息"
"""

import os
import sys
import subprocess


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


def main():
    if len(sys.argv) < 2:
        print_flush("❌ 请指定提交信息！")
        print_flush("用法: python tools/push.py \"提交信息\"")
        sys.exit(1)

    msg = sys.argv[1]

    root = os.getcwd()
    print_flush(f"ℹ️ 当前目录: {root}")

    code, branch, _ = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if code != 0:
        print_flush("❌ 无法获取当前分支")
        sys.exit(1)
    branch = branch.strip()
    print_flush(f"ℹ️ 当前分支: {branch}")

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
    code, stdout, _ = run_cmd(["git", "commit", "-m", msg])
    if code != 0:
        if "nothing to commit" in stdout or "nothing to commit" in str(stdout):
            print_flush("ℹ️ 没有新的变更需要提交，跳过提交步骤")
        else:
            print_flush("❌ git commit 失败")
            sys.exit(1)
    else:
        print_flush("✅ 完成")

    print_flush(f"\n→ 推送到 origin...")
    code, _, _ = run_cmd(["git", "push", "origin", branch])
    if code != 0:
        print_flush("❌ git push 失败")
        sys.exit(1)
    print_flush("✅ 完成")

    print_flush("\n" + "=" * 50)
    print_flush("✅ 全部完成！")
    print_flush("=" * 50)
    print_flush(f"   - 提交: {msg}")
    print_flush(f"   - 分支: {branch}")


if __name__ == "__main__":
    main()