#!/usr/bin/env bash
set -u

############################
# 基本配置
############################
SERVER_ID=""
API_ENDPOINT="https://yuntester.yunsilicon.com/api"
HEARTBEAT_INTERVAL=180     # 3 分钟
RETRY_INTERVAL=30
LOG_FILE="/var/log/server_daemon.log"

PROFILE_FILE="/etc/profile"
MARK_START="# WARNING_MESSAGE_START"
MARK_END="# WARNING_MESSAGE_END"

############################
# 日志函数
############################
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [server-daemon] $*" | tee -a "$LOG_FILE"
}

############################
# 参数解析
############################
while [[ $# -gt 0 ]]; do
    case "$1" in
        --server-id)
            SERVER_ID="$2"
            shift 2
            ;;
        --api-endpoint)
            API_ENDPOINT="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done

# 如果命令行没有指定，尝试从环境变量读取
if [[ -z "$SERVER_ID" ]]; then
    SERVER_ID="${SERVER_ID:-}"
fi

if [[ -z "$SERVER_ID" ]]; then
    log "ERROR: --server-id is required or SERVER_ID environment variable must be set"
    exit 1
fi

API_ENDPOINT="${API_ENDPOINT%/}"

############################
# 更新 /etc/profile
############################
update_profile() {
    local user="$1"
    local remain_seconds="$2"
    local expire_time=""

    # 先删除旧内容
    sed -i "/$MARK_START/,/$MARK_END/d" "$PROFILE_FILE" 2>/dev/null

    if [[ -n "$user" && "$remain_seconds" =~ ^[0-9]+$ && "$remain_seconds" -gt 0 ]]; then
        # 计算截止时间
        expire_time=$(date -d "+${remain_seconds} seconds" "+%Y-%m-%d %H:%M:%S")

        cat >> "$PROFILE_FILE" <<EOF
$MARK_START
echo -e "\\033[5;31m"
echo "██╗    ██╗ █████╗ ██████╗ ███╗   ██╗██╗██╗██╗"
echo "██║    ██║██╔══██╗██╔══██╗████╗  ██║██║██║██║"
echo "██║ █╗ ██║███████║██████╔╝██╔██╗ ██║██║██║██║"
echo "██║███╗██║██╔══██║██╔══██╗██║╚██╗██║╚═╝╚═╝╚═╝"
echo "╚███╔███╔╝██║  ██║██║  ██║██║ ╚████║██╗██╗██╗"
echo " ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝╚═╝╚═╝"
echo -e "\\033[0m"
echo ""
echo "🚫 服务器已被占用！请立即退出！ 🚫"
echo "================================================"
echo "👤 使用人: $user"
echo "⏰ 占用截止: $expire_time"
echo "🔗 管理页面: https://yuntester.yunsilicon.com/devices"
echo ""
echo "💡 可登录管理页面，在[服务器管理]中查看其余可用服务器"
echo "================================================"
$MARK_END
EOF
    else
        cat >> "$PROFILE_FILE" <<EOF
$MARK_START
echo "-----------------------------------------------------------------------------"
echo "提示：当前服务器无人使用！"
echo "请先登录: https://yuntester.yunsilicon.com/devices 在[服务器管理]完成'占用服务器'后继续使用"
echo "-----------------------------------------------------------------------------"
$MARK_END
EOF
    fi

}

############################
# 发送心跳
############################
send_heartbeat() {
    local body user time next_checkin

    body=$(curl -sSk -m 10 -X "GET" \
        -H "accept: application/json" \
        "$API_ENDPOINT/api/servers/$SERVER_ID/heartbeat") || return 1

    user=$(echo "$body" | sed -n 's/.*"user"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    time=$(echo "$body" | sed -n 's/.*"time"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
    next_checkin=$(echo "$body" | sed -n 's/.*"next_checkin"[[:space:]]*:[[:space:]]*\([0-9]\+\).*/\1/p')

    [[ -n "$next_checkin" ]] && HEARTBEAT_INTERVAL="$next_checkin"

    update_profile "$user" "$time"
    log "Heartbeat OK (interval=${HEARTBEAT_INTERVAL}s)"

    return 0
}

############################
# 主循环
############################
log "Starting server daemon for $SERVER_ID"

# 捕获信号，优雅退出
cleanup() {
    log "Daemon shutting down"
    exit 0
}

trap cleanup SIGTERM SIGINT

while true; do
    if send_heartbeat; then
        sleep "$HEARTBEAT_INTERVAL"
    else
        sleep "$RETRY_INTERVAL"
    fi
done