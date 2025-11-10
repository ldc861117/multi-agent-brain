#!/bin/bash
# Multi-Agent Brain DEMO 启动脚本

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# 检查 Python 版本
check_python() {
    print_info "检查 Python 版本..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未安装，请先安装 Python 3.8+"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo "当前 Python 版本: $PYTHON_VERSION"
    
    # 检查版本是否满足要求
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        print_success "Python 版本检查通过"
    else
        print_error "Python 版本过低，需要 3.8 或更高版本"
        exit 1
    fi
}

# 检查虚拟环境
check_venv() {
    print_info "检查虚拟环境..."
    
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        print_success "已激活虚拟环境: $VIRTUAL_ENV"
    else
        print_warning "未检测到虚拟环境"
        print_info "建议使用虚拟环境来隔离依赖"
        
        # 询问是否创建虚拟环境
        read -p "是否创建新的虚拟环境？(y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "创建虚拟环境..."
            python3 -m venv .venv
            source .venv/bin/activate
            print_success "虚拟环境创建并激活完成"
        fi
    fi
}

# 安装依赖
install_dependencies() {
    print_info "检查并安装依赖..."
    
    if [[ -f "requirements.txt" ]]; then
        print_info "从 requirements.txt 安装依赖..."
        pip install -r requirements.txt
        print_success "依赖安装完成"
    else
        print_warning "requirements.txt 不存在，跳过依赖安装"
    fi
}

# 检查环境配置
check_env_config() {
    print_info "检查环境配置..."
    
    # 检查 .env 文件
    if [[ ! -f ".env" ]]; then
        if [[ -f ".env.example" ]]; then
            print_warning ".env 文件不存在，从 .env.example 创建..."
            cp .env.example .env
            print_info "请编辑 .env 文件，配置你的 API 密钥和端点"
            print_warning "配置完成后请重新运行此脚本"
            exit 1
        else
            print_error ".env.example 文件不存在"
            exit 1
        fi
    else
        print_success ".env 文件存在"
        
        # 检查关键环境变量
        if grep -q "CHAT_API_KEY=" .env && ! grep -q "CHAT_API_KEY=$" .env; then
            print_success "CHAT_API_KEY 已配置"
        else
            print_warning "CHAT_API_KEY 未配置或为空"
        fi
    fi
    
    # 检查 config.yaml 文件
    if [[ ! -f "config.yaml" ]]; then
        if [[ -f "config.default.yaml" ]]; then
            print_warning "config.yaml 文件不存在，从 config.default.yaml 创建..."
            cp config.default.yaml config.yaml
            print_success "已创建 config.yaml，请根据需要自定义配置"
        else
            print_warning "config.yaml 和 config.default.yaml 都不存在，将使用内置默认配置"
        fi
    else
        print_success "config.yaml 文件存在"

        set +e
        VALIDATION_OUTPUT=$(python3 -m utils.config_validator --path config.yaml --default config.default.yaml 2>&1)
        VALIDATION_STATUS=$?
        set -e

        if [[ $VALIDATION_STATUS -ne 0 ]]; then
            print_error "config.yaml 验证失败，请根据以下输出修复:"
            echo "$VALIDATION_OUTPUT"

            if [[ -f "config.default.yaml" ]]; then
                if [[ "${AUTO_REPAIR_CONFIG:-0}" == "1" ]]; then
                    python3 -m utils.config_validator --path config.yaml --default config.default.yaml --repair
                    print_success "已从模板修复 config.yaml (原文件已备份)"

                    set +e
                    VALIDATION_OUTPUT=$(python3 -m utils.config_validator --path config.yaml --default config.default.yaml 2>&1)
                    VALIDATION_STATUS=$?
                    set -e

                    if [[ $VALIDATION_STATUS -ne 0 ]]; then
                        print_error "修复后的 config.yaml 仍未通过验证，请手动检查:"
                        echo "$VALIDATION_OUTPUT"
                        exit 1
                    else
                        print_success "config.yaml 验证通过"
                    fi
                elif [[ -t 0 ]]; then
                    read -p "是否使用 config.default.yaml 修复 config.yaml？(y/N): " -n 1 -r
                    echo
                    if [[ $REPLY =~ ^[Yy]$ ]]; then
                        python3 -m utils.config_validator --path config.yaml --default config.default.yaml --repair
                        print_success "已从模板修复 config.yaml (原文件已备份)"

                        set +e
                        VALIDATION_OUTPUT=$(python3 -m utils.config_validator --path config.yaml --default config.default.yaml 2>&1)
                        VALIDATION_STATUS=$?
                        set -e

                        if [[ $VALIDATION_STATUS -ne 0 ]]; then
                            print_error "修复后的 config.yaml 仍未通过验证，请手动检查:"
                            echo "$VALIDATION_OUTPUT"
                            exit 1
                        else
                            print_success "config.yaml 验证通过"
                        fi
                    else
                        print_warning "已保留原始 config.yaml，请根据提示手动修复后重试。"
                        exit 1
                    fi
                else
                    print_warning "检测到非交互式环境。设置 AUTO_REPAIR_CONFIG=1 以自动修复或运行 python3 -m utils.config_validator --repair"
                    exit 1
                fi
            else
                print_error "config.default.yaml 不存在，无法自动修复 config.yaml。"
                exit 1
            fi
        else
            print_success "config.yaml 验证通过"
        fi
    fi
}

# 运行环境检查
run_env_check() {
    print_info "运行环境检查..."
    
    if python3 -m demos.setup; then
        print_success "环境检查通过"
    else
        print_error "环境检查失败，请根据提示修复问题"
        exit 1
    fi
}

# 启动 OpenAgents 网络（可选）
start_openagents() {
    print_info "检查 OpenAgents 网络状态..."
    
    # 检查是否已经有 OpenAgents 进程在运行
    if pgrep -f "openagents network" > /dev/null; then
        print_success "OpenAgents 网络已在运行"
        return 0
    fi
    
    # 询问是否启动 OpenAgents
    read -p "是否启动 OpenAgents 网络？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "启动 OpenAgents 网络..."
        
        # 后台启动 OpenAgents
        if command -v openagents &> /dev/null; then
            openagents network start config.yaml &
            OPENAGENTS_PID=$!
            
            # 等待网络启动
            sleep 3
            
            # 检查是否启动成功
            if kill -0 $OPENAGENTS_PID 2>/dev/null; then
                print_success "OpenAgents 网络启动成功 (PID: $OPENAGENTS_PID)"
                echo $OPENAGENTS_PID > .openagents_pid
            else
                print_error "OpenAgents 网络启动失败"
                exit 1
            fi
        else
            print_warning "OpenAgents 命令未找到，跳过网络启动"
            print_info "DEMO 仍可运行，但某些功能可能受限"
        fi
    else
        print_info "跳过 OpenAgents 网络启动"
    fi
}

# 运行 DEMO
run_demo() {
    print_header "启动 Multi-Agent Brain DEMO"
    
    # 检查 DEMO 参数
    MODE=${1:-"interactive"}
    
    case $MODE in
        "interactive"|"automated"|"benchmark"|"verify-routing")
            print_info "运行模式: $MODE"
            ;;
        *)
            print_warning "未知模式: $MODE，使用默认的 interactive 模式"
            MODE="interactive"
            ;;
    esac
    
    # 运行 DEMO 或验证脚本
    print_info "启动 DEMO..."
    if [[ "$MODE" == "verify-routing" ]]; then
        python3 verify_multi_expert_dispatch.py
    else
        python3 -m demos.runner --mode "$MODE"
    fi
}

# 清理函数
cleanup() {
    print_info "清理资源..."
    
    # 停止 OpenAgents 网络
    if [[ -f ".openagents_pid" ]]; then
        OPENAGENTS_PID=$(cat .openagents_pid)
        if kill -0 $OPENAGENTS_PID 2>/dev/null; then
            print_info "停止 OpenAgents 网络 (PID: $OPENAGENTS_PID)..."
            kill $OPENAGENTS_PID
            rm .openagents_pid
        fi
    fi
    
    print_success "清理完成"
}

# 设置信号处理
trap cleanup EXIT INT TERM

# 显示帮助信息
show_help() {
    echo "Multi-Agent Brain DEMO 启动脚本"
    echo ""
    echo "用法: $0 [选项] [模式]"
    echo ""
    echo "模式:"
    echo "  interactive     交互式模式（默认）"
    echo "  automated       自动化模式"
    echo "  benchmark       性能测试模式"
    echo "  verify-routing  离线验证 multi-expert 路由与协作"
    echo ""
    echo "选项:"
    echo "  -h, --help    显示此帮助信息"
    echo "  --no-check    跳过环境检查"
    echo "  --no-deps     跳过依赖安装"
    echo ""
    echo "示例:"
    echo "  $0                       # 交互式模式"
    echo "  $0 automated             # 自动化模式"
    echo "  $0 benchmark             # 性能测试模式"
    echo "  $0 verify-routing        # 验证多专家路由与协作"
    echo "  $0 --no-check interactive # 跳过检查运行交互模式"
}

# 解析命令行参数
SKIP_CHECK=false
SKIP_DEPS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        --no-check)
            SKIP_CHECK=true
            shift
            ;;
        --no-deps)
            SKIP_DEPS=true
            shift
            ;;
        interactive|automated|benchmark|verify-routing)
            MODE=$1
            shift
            ;;
        *)
            print_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 主流程
main() {
    print_header "Multi-Agent Brain DEMO 启动器"
    
    # 检查 Python
    check_python
    
    # 检查虚拟环境
    check_venv
    
    # 安装依赖（如果需要）
    if [[ "$SKIP_DEPS" != true ]]; then
        install_dependencies
    fi
    
    # 检查环境配置
    check_env_config
    
    # 运行环境检查（如果需要）
    if [[ "$SKIP_CHECK" != true ]]; then
        run_env_check
    fi
    
    # 启动 OpenAgents 网络（可选）
    start_openagents
    
    # 运行 DEMO
    run_demo ${MODE:-"interactive"}
}

# 执行主流程
main "$@"