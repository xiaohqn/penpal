#!/usr/bin/env bash

# 输入：
# - 第一个位置参数可以是 `frontend`、`backend` 或明确的 `http://127.0.0.1:PORT` URL。
# - 可选环境变量 `TRYCLOUDFLARE_FRONTEND_URL`、`TRYCLOUDFLARE_BACKEND_URL` 用于覆盖默认目标地址。
# 输出：
# - 启动一个 TryCloudflare 临时隧道，并在终端输出 Cloudflare 返回的随机公网域名。
# - 脚本本身不会修改项目文件，只会启动 `cloudflared` 进程并把日志透传到当前终端。
# 作用：
# - 统一封装本项目本地服务暴露到公网的常见用法，避免每次手写 `cloudflared tunnel --url ...`
#   并反复记忆前端/后端端口。

set -euo pipefail

DEFAULT_FRONTEND_URL="${TRYCLOUDFLARE_FRONTEND_URL:-http://127.0.0.1:5173}"
DEFAULT_BACKEND_URL="${TRYCLOUDFLARE_BACKEND_URL:-http://127.0.0.1:8000}"

print_usage() {
  # 输入：
  # - 无，函数只读取当前脚本支持的参数约定。
  # 输出：
  # - 把使用方式打印到标准输出，便于调用者快速选择前端、后端或自定义 URL。
  # 作用：
  # - 当用户首次接触脚本或参数写错时，给出足够明确的自解释说明，减少来回查文档。
  cat <<EOF
Usage:
  ./scripts/trycloudflare.sh frontend
  ./scripts/trycloudflare.sh backend
  ./scripts/trycloudflare.sh http://127.0.0.1:9000

Default targets:
  frontend -> ${DEFAULT_FRONTEND_URL}
  backend  -> ${DEFAULT_BACKEND_URL}

Optional overrides:
  TRYCLOUDFLARE_FRONTEND_URL=http://127.0.0.1:4173
  TRYCLOUDFLARE_BACKEND_URL=http://127.0.0.1:9000
EOF
}

ensure_cloudflared() {
  # 输入：
  # - 无，函数只依赖当前系统 PATH。
  # 输出：
  # - 当 `cloudflared` 已安装时静默返回；未安装时打印安装提示并以非零状态退出。
  # 作用：
  # - 在真正发起隧道前先做依赖检查，让失败原因直观可见，而不是把后续报错留给用户猜测。
  if command -v cloudflared >/dev/null 2>&1; then
    return
  fi

  cat <<'EOF' >&2
`cloudflared` is required but was not found in PATH.

Install it on macOS with:
  brew install cloudflared

Then rerun this script.
EOF
  exit 1
}

resolve_target_url() {
  # 输入：
  # - `$1` 为用户传入的目标别名或显式 URL。
  # 输出：
  # - 返回最终应交给 `cloudflared tunnel --url` 的本地服务地址。
  # 作用：
  # - 把“前端/后端快捷别名”和“自定义 URL 透传”这两类调用入口收敛到一个地方，避免主流程里堆分支。
  local target="${1:-frontend}"

  case "${target}" in
    frontend)
      printf '%s\n' "${DEFAULT_FRONTEND_URL}"
      ;;
    backend)
      printf '%s\n' "${DEFAULT_BACKEND_URL}"
      ;;
    http://*|https://*)
      printf '%s\n' "${target}"
      ;;
    -h|--help|help)
      print_usage
      exit 0
      ;;
    *)
      printf 'Unsupported target: %s\n\n' "${target}" >&2
      print_usage >&2
      exit 1
      ;;
  esac
}

main() {
  # 输入：
  # - 读取命令行参数中声明的目标服务别名或 URL。
  # 输出：
  # - 在当前前台进程中持续运行 `cloudflared tunnel --url ...`，直到用户手动中断。
  # 作用：
  # - 作为脚本总入口，串起依赖检查、目标解析和隧道启动，并在启动前给出清晰的目标提示。
  local raw_target="${1:-frontend}"

  # `--help` 需要在未安装 cloudflared 的机器上也能正常查看，因此要在依赖检查前直接返回。
  case "${raw_target}" in
    -h|--help|help)
      print_usage
      return 0
      ;;
  esac

  local target_url
  target_url="$(resolve_target_url "${raw_target}")"

  ensure_cloudflared

  printf 'Starting TryCloudflare tunnel for %s\n' "${target_url}"
  printf 'Press Ctrl+C to stop the tunnel.\n'

  # TryCloudflare 会为每次会话分配随机的 `*.trycloudflare.com` 域名。
  # 这里不加额外参数，保持官方最简工作流，方便本地开发时直接复用。
  exec cloudflared tunnel --url "${target_url}"
}

main "$@"
