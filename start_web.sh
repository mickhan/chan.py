#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
python="$repo_root/.venv/bin/python"

if [[ ! -x "$python" ]]; then
  printf 'Python 虚拟环境不存在：%s\n请先按 web/README.md 安装依赖。\n' "$python" >&2
  exit 1
fi

if [[ ! -f "$repo_root/web/frontend/dist/index.html" ]]; then
  printf '提示：前端尚未构建，网页首页不可用；构建方法见 web/README.md。\n' >&2
fi

cd "$repo_root"
exec "$python" -m web
