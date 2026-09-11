#!/usr/bin/env bash
#
# sudo-fun Installer Script
# -------------------------
# Automatically detects Linux distribution, installs dependencies, clones or
# downloads the latest release (or main branch if unreleased), sets up a Python
# virtual environment, and configures Bash, Zsh, and Fish shell integration.
#
set -eo pipefail

# ANSI color codes (disabled if non-interactive or NO_COLOR is set)
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
    BOLD=$'\033[1m'
    GREEN=$'\033[0;32m'
    BLUE=$'\033[0;34m'
    YELLOW=$'\033[0;33m'
    RED=$'\033[0;31m'
    NC=$'\033[0m'
else
    BOLD=""
    GREEN=""
    BLUE=""
    YELLOW=""
    RED=""
    NC=""
fi

# Output formatting helpers
info() {
    printf "${BLUE}${BOLD}[*]${NC} %s\n" "$*"
}

success() {
    printf "${GREEN}${BOLD}[+]${NC} %s\n" "$*"
}

warn() {
    printf "${YELLOW}${BOLD}[!]${NC} %s\n" "$*"
}

error() {
    printf "${RED}${BOLD}[-]${NC} %s\n" "$*" >&2
}

die() {
    error "$*"
    exit 1
}

# Configuration and defaults
REPO="${SUDO_FUN_REPO:-itsnyxdev/sudo-fun}"
DEFAULT_INSTALL_DIR="${HOME}/.local/share/sudo-fun"
DEFAULT_BIN_DIR="${HOME}/.local/bin"
INSTALL_DIR="${SUDO_FUN_DIR:-$DEFAULT_INSTALL_DIR}"
BIN_DIR="${SUDO_FUN_BIN:-$DEFAULT_BIN_DIR}"
BRANCH="${SUDO_FUN_BRANCH:-}"
SKIP_DEPS="${SUDO_FUN_SKIP_DEPS:-0}"
CONFIGURE_ALIAS=""
LOCAL_SOURCE=""

# Usage help
print_usage() {
    cat << EOF
${BOLD}sudo-fun Installer${NC}

Usage: ./install.sh [options]

Options:
  -h, --help            Show this help message and exit
  -d, --dir <path>      Installation directory (default: ~/.local/share/sudo-fun)
  -b, --bin-dir <path>  Binary executable directory (default: ~/.local/bin)
  --branch <branch>     Clone specific branch or tag from GitHub
  --skip-deps           Skip system package manager dependency installation
  --alias               Automatically configure 'alias sudo="sudo-fun"' in shells
  --no-alias            Skip shell alias configuration
  --local [path]        Install from local directory (default: current directory)

Environment Variables:
  SUDO_FUN_REPO         GitHub repository (default: itsnyxdev/sudo-fun)
  SUDO_FUN_DIR          Install directory (default: ~/.local/share/sudo-fun)
  SUDO_FUN_BIN          Binary directory (default: ~/.local/bin)
  SUDO_FUN_BRANCH       Branch to clone (default: latest release tag or main)
  SUDO_FUN_SKIP_DEPS    Set to 1 to skip system package manager
EOF
}

# Parse CLI arguments
parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            -h|--help)
                print_usage
                exit 0
                ;;
            -d|--dir)
                [ -n "${2:-}" ] || die "Option $1 requires a path argument."
                INSTALL_DIR="$2"
                shift 2
                ;;
            -b|--bin-dir)
                [ -n "${2:-}" ] || die "Option $1 requires a path argument."
                BIN_DIR="$2"
                shift 2
                ;;
            --branch)
                [ -n "${2:-}" ] || die "Option $1 requires a branch/tag argument."
                BRANCH="$2"
                shift 2
                ;;
            --skip-deps)
                SKIP_DEPS=1
                shift
                ;;
            --alias)
                CONFIGURE_ALIAS="yes"
                shift
                ;;
            --no-alias)
                CONFIGURE_ALIAS="no"
                shift
                ;;
            --local)
                if [ -n "${2:-}" ] && [[ "$2" != --* ]]; then
                    LOCAL_SOURCE="$2"
                    shift 2
                else
                    LOCAL_SOURCE="$(pwd)"
                    shift
                fi
                ;;
            *)
                die "Unknown argument: $1. Run with --help for usage."
                ;;
        esac
    done
}

# Detect Linux distribution
detect_distro() {
    DISTRO_ID="unknown"
    DISTRO_LIKE=""

    if [ -f /etc/os-release ]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        DISTRO_ID="${ID:-unknown}"
        DISTRO_LIKE="${ID_LIKE:-}"
    elif [ -f /usr/lib/os-release ]; then
        # shellcheck disable=SC1091
        . /usr/lib/os-release
        DISTRO_ID="${ID:-unknown}"
        DISTRO_LIKE="${ID_LIKE:-}"
    fi

    # Convert to lowercase
    DISTRO_ID="$(echo "$DISTRO_ID" | tr '[:upper:]' '[:lower:]')"
    DISTRO_LIKE="$(echo "$DISTRO_LIKE" | tr '[:upper:]' '[:lower:]')"
}

# Run command with sudo if not root
run_privileged() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    else
        if command -v sudo >/dev/null 2>&1; then
            sudo "$@"
        else
            die "Elevated privileges required to install dependencies, but 'sudo' was not found. Please install dependencies manually or pass --skip-deps."
        fi
    fi
}

# Install system dependencies via native package manager
install_system_dependencies() {
    if [ "$SKIP_DEPS" -eq 1 ]; then
        info "Skipping system package dependencies (--skip-deps specified)."
        return 0
    fi

    info "Detecting system package manager for Linux distribution ($DISTRO_ID)..."

    case "$DISTRO_ID" in
        ubuntu|debian|linuxmint|pop|kali|raspbian|elementary)
            info "Installing system dependencies with apt-get..."
            run_privileged apt-get update -qq
            run_privileged apt-get install -y \
                python3 python3-pip python3-venv git curl \
                libportaudio2 libgl1 libglib2.0-0 \
                alsa-utils pulseaudio-utils
            ;;
        fedora|rhel|centos|rocky|almalinux|nobara)
            info "Installing system dependencies with dnf/yum..."
            local pkg_mgr="dnf"
            command -v dnf >/dev/null 2>&1 || pkg_mgr="yum"
            run_privileged "$pkg_mgr" install -y \
                python3 python3-pip git curl \
                portaudio mesa-libGL glib2 \
                alsa-utils pulseaudio-utils pipewire-utils
            ;;
        arch|manjaro|endeavouros|garuda|artix)
            info "Installing system dependencies with pacman..."
            run_privileged pacman -Sy --noconfirm --needed \
                python python-pip git curl \
                portaudio mesa glib2 alsa-utils
            ;;
        opensuse*|suse|sles)
            info "Installing system dependencies with zypper..."
            run_privileged zypper --non-interactive install \
                python3 python3-pip git curl \
                portaudio-devel libGL1 libglib-2_0-0 alsa-utils
            ;;
        alpine)
            info "Installing system dependencies with apk..."
            run_privileged apk add \
                python3 py3-pip git curl \
                portaudio-dev mesa-gl alsa-utils
            ;;
        void)
            info "Installing system dependencies with xbps-install..."
            run_privileged xbps-install -Sy \
                python3 python3-pip git curl portaudio alsa-utils
            ;;
        *)
            # Check ID_LIKE fallbacks
            if [[ "$DISTRO_LIKE" == *"debian"* ]] || [[ "$DISTRO_LIKE" == *"ubuntu"* ]]; then
                info "Installing system dependencies with apt-get (based on ID_LIKE)..."
                run_privileged apt-get update -qq
                run_privileged apt-get install -y \
                    python3 python3-pip python3-venv git curl \
                    libportaudio2 libgl1 libglib2.0-0 alsa-utils pulseaudio-utils
            elif [[ "$DISTRO_LIKE" == *"fedora"* ]] || [[ "$DISTRO_LIKE" == *"rhel"* ]]; then
                info "Installing system dependencies with dnf/yum (based on ID_LIKE)..."
                local pkg_mgr="dnf"
                command -v dnf >/dev/null 2>&1 || pkg_mgr="yum"
                run_privileged "$pkg_mgr" install -y \
                    python3 python3-pip git curl portaudio mesa-libGL glib2 alsa-utils
            elif [[ "$DISTRO_LIKE" == *"arch"* ]]; then
                info "Installing system dependencies with pacman (based on ID_LIKE)..."
                run_privileged pacman -Sy --noconfirm --needed \
                    python python-pip git curl portaudio mesa glib2 alsa-utils
            elif command -v apt-get >/dev/null 2>&1; then
                warn "Unrecognized distro '$DISTRO_ID', but found 'apt-get'. Attempting install..."
                run_privileged apt-get update -qq
                run_privileged apt-get install -y python3 python3-pip python3-venv git curl libportaudio2 libgl1 alsa-utils
            elif command -v dnf >/dev/null 2>&1; then
                warn "Unrecognized distro '$DISTRO_ID', but found 'dnf'. Attempting install..."
                run_privileged dnf install -y python3 python3-pip git curl portaudio mesa-libGL glib2 alsa-utils
            elif command -v pacman >/dev/null 2>&1; then
                warn "Unrecognized distro '$DISTRO_ID', but found 'pacman'. Attempting install..."
                run_privileged pacman -Sy --noconfirm --needed python python-pip git curl portaudio mesa alsa-utils
            else
                warn "Could not determine appropriate package manager for distro '$DISTRO_ID'."
                warn "Please ensure Python >= 3.10, git, portaudio, and alsa-utils are installed."
            fi
            ;;
    esac

    success "System dependencies verified."
}

# Verify Python >= 3.10
verify_python() {
    info "Verifying Python version..."
    if ! command -v python3 >/dev/null 2>&1; then
        die "python3 is not installed or not in PATH."
    fi

    local py_ver
    py_ver="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    local major minor
    major="$(echo "$py_ver" | cut -d. -f1)"
    minor="$(echo "$py_ver" | cut -d. -f2)"

    if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 10 ]; }; then
        die "Python 3.10 or higher is required (detected Python $py_ver)."
    fi

    success "Python $py_ver detected."
}

# Obtain the source code into INSTALL_DIR
fetch_source_code() {
    # Check if running in a local clone without explicit flag
    if [ -z "$LOCAL_SOURCE" ] && [ -f "./pyproject.toml" ] && [ -d "./src/sudo_fun" ]; then
        if grep -q 'name = "sudo-fun"' "./pyproject.toml" 2>/dev/null; then
            LOCAL_SOURCE="$(pwd)"
            info "Detected local sudo-fun repository at: $LOCAL_SOURCE"
        fi
    fi

    mkdir -p "$INSTALL_DIR"

    if [ -n "$LOCAL_SOURCE" ]; then
        info "Installing from local source: $LOCAL_SOURCE"
        if [ "$(realpath "$LOCAL_SOURCE")" != "$(realpath "$INSTALL_DIR" 2>/dev/null)" ]; then
            info "Syncing local files to $INSTALL_DIR..."
            if command -v rsync >/dev/null 2>&1; then
                rsync -a --exclude='.venv' --exclude='__pycache__' --exclude='.git' --exclude='.pytest_cache' "$LOCAL_SOURCE/" "$INSTALL_DIR/"
            else
                cp -a "$LOCAL_SOURCE"/. "$INSTALL_DIR/"
                rm -rf "$INSTALL_DIR/.venv" "$INSTALL_DIR/.pytest_cache"
            fi
        fi
        ensure_audio_assets
        return 0
    fi

    local target_tag="$BRANCH"

    if [ -z "$target_tag" ]; then
        info "Checking for latest release of ${REPO} on GitHub..."
        local release_json=""
        if command -v curl >/dev/null 2>&1; then
            release_json="$(curl -sSL "https://api.github.com/repos/${REPO}/releases/latest" 2>/dev/null || true)"
        fi

        # Try to download prepared release package if available
        local asset_url=""
        if [ -n "$release_json" ]; then
            asset_url="$(echo "$release_json" | grep -o '"browser_download_url": *"[^"]*sudo-fun-[^"]*\.tar\.gz"' | head -n 1 | cut -d '"' -f 4 || true)"
        fi

        if [ -n "$asset_url" ] && command -v tar >/dev/null 2>&1; then
            info "Downloading release package from $asset_url..."
            rm -rf "${INSTALL_DIR:?}"/*
            if { curl -sSL "$asset_url" | tar -xz --strip-components=1 -C "$INSTALL_DIR" 2>/dev/null || curl -sSL "$asset_url" | tar -xz -C "$INSTALL_DIR" 2>/dev/null; } && [ -f "$INSTALL_DIR/pyproject.toml" ]; then
                ensure_audio_assets
                success "Source code prepared at $INSTALL_DIR"
                return 0
            fi
        fi

        # Parse tag_name if present
        local parsed_tag=""
        if [ -n "$release_json" ]; then
            parsed_tag="$(echo "$release_json" | grep -o '"tag_name": *"[^"]*"' | head -n 1 | cut -d '"' -f 4 || true)"
        fi

        if [ -n "$parsed_tag" ]; then
            target_tag="$parsed_tag"
            info "Found latest release: $target_tag"
        else
            info "No published release found on GitHub yet. Falling back to default 'main' branch."
            target_tag="main"
        fi
    fi

    # Fallback to git clone if release asset not used
    if ! command -v git >/dev/null 2>&1; then
        die "git is required to clone sudo-fun. Please install git."
    fi

    info "Cloning ${REPO} (branch/tag: ${target_tag}) into ${INSTALL_DIR}..."

    if [ -d "$INSTALL_DIR/.git" ]; then
        info "Existing git repository found at ${INSTALL_DIR}. Updating..."
        git -C "$INSTALL_DIR" fetch --depth 1 origin "$target_tag"
        git -C "$INSTALL_DIR" checkout -f "$target_tag" 2>/dev/null || git -C "$INSTALL_DIR" checkout -f -B "$target_tag" "origin/$target_tag"
    else
        rm -rf "${INSTALL_DIR:?}"/*
        git clone --depth 1 --branch "$target_tag" "https://github.com/${REPO}.git" "$INSTALL_DIR"
    fi

    ensure_audio_assets
    success "Source code prepared at $INSTALL_DIR"
}

# Ensure audio assets exist in INSTALL_DIR/assets
ensure_audio_assets() {
    local assets_dir="$INSTALL_DIR/assets"
    mkdir -p "$assets_dir"
    if [ ! -s "$assets_dir/failed.mp3" ]; then
        info "Downloading failed.mp3 asset..."
        curl -sSL "http://sudo-fun.imnyx.dev/assets/failed.mp3" -o "$assets_dir/failed.mp3" 2>/dev/null || true
    fi
    if [ ! -s "$assets_dir/failed.wav" ]; then
        info "Downloading failed.wav asset..."
        curl -sSL "http://sudo-fun.imnyx.dev/assets/failed.wav" -o "$assets_dir/failed.wav" 2>/dev/null || true
    fi
}

# Create Python venv and install sudo-fun
setup_python_environment() {
    local venv_dir="$INSTALL_DIR/venv"
    info "Setting up Python virtual environment in ${venv_dir}..."

    if command -v uv >/dev/null 2>&1; then
        info "Using 'uv' for ultra-fast virtual environment & dependency management..."
        uv venv "$venv_dir"
        VIRTUAL_ENV="$venv_dir" uv pip install -e "$INSTALL_DIR"
    else
        python3 -m venv "$venv_dir"
        "$venv_dir/bin/pip" install --upgrade pip --quiet
        "$venv_dir/bin/pip" install -e "$INSTALL_DIR" --quiet
    fi

    # Verify installation
    if ! "$venv_dir/bin/sudo-fun" --help >/dev/null 2>&1; then
        die "Failed to execute sudo-fun inside the virtual environment."
    fi

    success "Python virtual environment configured successfully."
}

# Create wrapper binary in BIN_DIR
create_binary_launcher() {
    info "Creating binary launcher in ${BIN_DIR}..."
    mkdir -p "$BIN_DIR"

    local launcher="$BIN_DIR/sudo-fun"
    cat << EOF > "$launcher"
#!/usr/bin/env bash
# Auto-generated launcher for sudo-fun
exec "$INSTALL_DIR/venv/bin/sudo-fun" "\$@"
EOF
    chmod +x "$launcher"

    success "Executable launcher installed at $launcher"
}

# Configure Bash, Zsh, and Fish shell PATH & alias
configure_shells() {
    info "Configuring shell environments (Bash, Zsh, Fish)..."

    # Handle interactive alias prompt if not specified via CLI flags
    if [ -z "$CONFIGURE_ALIAS" ]; then
        if [ -t 0 ] && [ -t 1 ]; then
            printf "\n"
            read -r -p "Would you like to alias 'sudo' to 'sudo-fun' in your shell configurations? [y/N]: " alias_choice
            case "$alias_choice" in
                [yY][eE][sS]|[yY])
                    CONFIGURE_ALIAS="yes"
                    ;;
                *)
                    CONFIGURE_ALIAS="no"
                    ;;
            esac
        else
            CONFIGURE_ALIAS="no"
        fi
    fi

    # 1. Bash configuration
    local bash_rc="$HOME/.bashrc"
    if [ -f "$bash_rc" ] || [ -f "$HOME/.bash_profile" ]; then
        [ -f "$bash_rc" ] || bash_rc="$HOME/.bash_profile"
        
        # Check PATH
        if ! grep -q "sudo-fun PATH" "$bash_rc" 2>/dev/null && ! grep -q "$BIN_DIR" "$bash_rc" 2>/dev/null; then
            cat >> "$bash_rc" << EOF

# sudo-fun PATH
if [[ ":\$PATH:" != *":$BIN_DIR:"* ]]; then
    export PATH="$BIN_DIR:\$PATH"
fi
EOF
            info "Added $BIN_DIR to PATH in $bash_rc"
        fi

        # Check Alias
        if [ "$CONFIGURE_ALIAS" = "yes" ]; then
            if ! grep -q 'alias sudo="sudo-fun"' "$bash_rc" 2>/dev/null; then
                cat >> "$bash_rc" << EOF

# sudo-fun alias
alias sudo="sudo-fun"
EOF
                info "Added 'alias sudo=\"sudo-fun\"' to $bash_rc"
            fi
        fi
    fi

    # 2. Zsh configuration
    local zsh_rc="$HOME/.zshrc"
    if [ -f "$zsh_rc" ] || command -v zsh >/dev/null 2>&1; then
        touch "$zsh_rc"
        if ! grep -q "sudo-fun PATH" "$zsh_rc" 2>/dev/null && ! grep -q "$BIN_DIR" "$zsh_rc" 2>/dev/null; then
            cat >> "$zsh_rc" << EOF

# sudo-fun PATH
if [[ ":\$PATH:" != *":$BIN_DIR:"* ]]; then
    export PATH="$BIN_DIR:\$PATH"
fi
EOF
            info "Added $BIN_DIR to PATH in $zsh_rc"
        fi

        if [ "$CONFIGURE_ALIAS" = "yes" ]; then
            if ! grep -q 'alias sudo="sudo-fun"' "$zsh_rc" 2>/dev/null; then
                cat >> "$zsh_rc" << EOF

# sudo-fun alias
alias sudo="sudo-fun"
EOF
                info "Added 'alias sudo=\"sudo-fun\"' to $zsh_rc"
            fi
        fi
    fi

    # 3. Fish configuration
    local fish_config_dir="$HOME/.config/fish"
    local fish_config="$fish_config_dir/config.fish"
    if [ -d "$fish_config_dir" ] || command -v fish >/dev/null 2>&1; then
        mkdir -p "$fish_config_dir"
        touch "$fish_config"

        if ! grep -q "sudo-fun PATH" "$fish_config" 2>/dev/null && ! grep -q "$BIN_DIR" "$fish_config" 2>/dev/null; then
            cat >> "$fish_config" << EOF

# sudo-fun PATH
if not contains "$BIN_DIR" \$PATH
    fish_add_path "$BIN_DIR"
end
EOF
            info "Added $BIN_DIR to PATH in $fish_config"
        fi

        if [ "$CONFIGURE_ALIAS" = "yes" ]; then
            if ! grep -q 'alias sudo="sudo-fun"' "$fish_config" 2>/dev/null && ! grep -q 'alias sudo "sudo-fun"' "$fish_config" 2>/dev/null; then
                cat >> "$fish_config" << EOF

# sudo-fun alias
alias sudo="sudo-fun"
EOF
                info "Added 'alias sudo=\"sudo-fun\"' to $fish_config"
            fi
        fi
    fi

    success "Shell configuration updated."
}

# Print post-install summary
print_summary() {
    printf "\n"
    printf "${GREEN}${BOLD}===============================================${NC}\n"
    printf "${GREEN}${BOLD}      sudo-fun successfully installed! ⚡       ${NC}\n"
    printf "${GREEN}${BOLD}===============================================${NC}\n"
    printf "\n"
    printf "Binary Location: %s/sudo-fun\n" "$BIN_DIR"
    printf "Source & Venv:   %s\n" "$INSTALL_DIR"
    printf "\n"
    printf "To start using sudo-fun in your current shell session, run:\n"
    if [[ "$SHELL" == *"fish"* ]]; then
        printf "  ${BOLD}source ~/.config/fish/config.fish${NC}\n"
    elif [[ "$SHELL" == *"zsh"* ]]; then
        printf "  ${BOLD}source ~/.zshrc${NC}\n"
    else
        printf "  ${BOLD}source ~/.bashrc${NC}\n"
    fi
    printf "\n"
    if [ "$CONFIGURE_ALIAS" != "yes" ]; then
        printf "Tip: To replace regular 'sudo' with interactive challenges, add this to your shell config:\n"
        printf "  ${YELLOW}alias sudo=\"sudo-fun\"${NC}\n\n"
    fi
    printf "Try running: ${BOLD}sudo-fun --dry-run whoami${NC}\n\n"
}

# Main entrypoint
main() {
    parse_args "$@"
    detect_distro
    install_system_dependencies
    verify_python
    fetch_source_code
    setup_python_environment
    create_binary_launcher
    configure_shells
    print_summary
}

main "$@"
