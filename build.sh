#!/usr/bin/env bash
# Cloudflare Pages 构建入口（也可手工执行）。
# 数据 JSON 已随仓库提交，构建时不依赖外部网络。
set -euo pipefail

if command -v python3 >/dev/null 2>&1; then
  python3 build.py
else
  python build.py
fi
