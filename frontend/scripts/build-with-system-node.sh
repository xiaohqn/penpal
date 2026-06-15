#!/bin/sh

# 输入：
# - 可选环境变量 PENPAL_NODE_BIN，用于显式指定构建时应使用的 Node 可执行文件。
# - 当前前端项目目录中的 node_modules、TypeScript 与 Vite CLI 入口文件。
# 输出：
# - 依次执行 TypeScript 构建与 Vite 生产构建；成功时在 dist/ 生成前端产物。
# 作用：
# - 优先绕开 Codex.app 自带 Node 对 Rollup 原生模块的签名校验限制，尽量选择系统或 Homebrew Node，
#   让 `npm run build` 在当前 macOS 环境下稳定可用；若没有更合适的 Node，再回退到当前 PATH 中的 node。

set -eu

resolve_node_bin() {
  if [ -n "${PENPAL_NODE_BIN:-}" ] && [ -x "${PENPAL_NODE_BIN}" ]; then
    printf '%s\n' "${PENPAL_NODE_BIN}"
    return 0
  fi

  for candidate in \
    /opt/homebrew/bin/node \
    /opt/homebrew/opt/node@20/bin/node \
    /usr/local/bin/node
  do
    if [ -x "${candidate}" ]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done

  if command -v node >/dev/null 2>&1; then
    printf '%s\n' "$(command -v node)"
    return 0
  fi

  printf '%s\n' "node not found" >&2
  return 1
}

NODE_BIN="$(resolve_node_bin)"

"${NODE_BIN}" ./node_modules/typescript/bin/tsc -b
"${NODE_BIN}" ./node_modules/vite/bin/vite.js build
