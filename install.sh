#!/bin/bash

PYTHON_CMD=""
PYTHON_MIN_MAJOR=3
PYTHON_MIN_MINOR=10

info()    { printf "\033[36m[INFO]\033[0m %s\n" "$1"; }
ok()      { printf "\033[32m[OK]\033[0m   %s\n" "$1"; }
warn()    { printf "\033[33m[WARN]\033[0m %s\n" "$1"; }
error()   { printf "\033[31m[ERROR]\033[0m %s\n" "$1"; }

check_python() {
    if ! command -v python3 &>/dev/null; then
        return 1
    fi
    local ver
    ver=$(python3 --version 2>&1)
    if python3 -c "import sys; exit(0 if sys.version_info >= ($PYTHON_MIN_MAJOR, $PYTHON_MIN_MINOR) else 1)" 2>/dev/null; then
        PYTHON_CMD="python3"
        ok "Python 已安装: $ver"
        return 0
    else
        warn "Python 版本过低: $ver（需要 ≥ $PYTHON_MIN_MAJOR.$PYTHON_MIN_MINOR）"
        return 1
    fi
}

install_python() {
    info "正在获取最新 Python 版本列表..."
    local page
    page=$(curl -sf "https://www.python.org/ftp/python/") || {
        error "无法访问 python.org，请检查网络连接"
        exit 1
    }

    local versions
    versions=$(echo "$page" | grep -oE 'href="(3\.[0-9]+\.[0-9]+)/"' | grep -oE '3\.[0-9]+\.[0-9]+' | sort -Vr)

    local selected=""
    local installer_url=""
    for v in $versions; do
        local test_url="https://www.python.org/ftp/python/$v/python-$v-macos11.pkg"
        local http_code
        http_code=$(curl -sI -o /dev/null -w "%{http_code}" "$test_url")
        if [ "$http_code" = "200" ]; then
            selected=$v
            installer_url=$test_url
            break
        fi
    done

    if [ -z "$selected" ]; then
        error "未找到可用的 Python 3 macOS 安装包"
        exit 1
    fi

    ok "最新稳定版本: Python $selected"

    local tmp_pkg="/tmp/python-$selected-macos11.pkg"
    info "正在下载 Python $selected 安装包..."
    curl -L -o "$tmp_pkg" "$installer_url" --progress-bar 2>&1
    if [ ! -f "$tmp_pkg" ]; then
        error "下载失败: $installer_url"
        exit 1
    fi
    ok "下载完成"

    info "正在安装 Python $selected（需要管理员密码）..."
    sudo installer -pkg "$tmp_pkg" -target /
    local install_exit=$?
    rm -f "$tmp_pkg"
    if [ $install_exit -ne 0 ]; then
        error "Python 安装失败"
        exit 1
    fi
    ok "Python $selected 安装完成"

    hash -r 2>/dev/null || true
}

if [ ! -f "requirements.txt" ]; then
    error "请在项目根目录运行此脚本（requirements.txt 所在目录）"
    exit 1
fi

if ! check_python; then
    install_python
    if ! check_python; then
        error "Python 安装后仍无法识别，请尝试重启终端后重试"
        exit 1
    fi
fi

info "检查 pip..."
$PYTHON_CMD -m pip --version &>/dev/null
if [ $? -ne 0 ]; then
    warn "pip 未安装，正在安装..."
    $PYTHON_CMD -m ensurepip --upgrade
    if [ $? -ne 0 ]; then
        error "pip 安装失败"
        exit 1
    fi
    ok "pip 安装成功"
else
    ok "pip 已就绪"
fi

if [ ! -d "venv" ]; then
    info "创建虚拟环境..."
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        error "虚拟环境创建失败"
        exit 1
    fi
    ok "虚拟环境已创建"
else
    ok "虚拟环境已存在"
fi

info "安装项目依赖..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    error "虚拟环境激活失败"
    exit 1
fi
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    error "依赖安装失败，请检查网络或 requirements.txt"
    exit 1
fi
ok "所有依赖安装完成"

info "启动应用..."
echo ""
printf "\033[32m    打开浏览器访问: http://127.0.0.1:5004\033[0m\n"
echo ""
python wsgi.py
