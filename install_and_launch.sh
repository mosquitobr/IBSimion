#!/bin/bash
# =============================================================================
# IBSimion 2.0.1.e3l - Launcher & Installer (Pipeline Automatizado)
# Native Linux (Debian/Ubuntu) deployment orchestrator
# =============================================================================
set -e

# Colors for a premium console look
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}================================================================${NC}"
echo -e "${GREEN}    IBSimion v2.0.1.e3l - Installer & Launcher (Versão de Produção E3)   ${NC}"
echo -e "${CYAN}================================================================${NC}"

# Get absolute path of this script to keep execution localized
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &>/dev/null && pwd )"
cd "$SCRIPT_DIR"

echo -e "\n${BLUE}[0/5] Executando rotina de limpeza de memória e processos antigos...${NC}"
# Kill orphaned processes safely
echo -e "  * Encerrando processos órfãos anteriores..."
pkill -f "python3.*E/E3/frontend/main.py" || true
pkill -f "python3.*E/E3/frontend/splash.py" || true
pkill -f "ibsimu_wrapper" || true
if [ -f "$SCRIPT_DIR/early_splash.pid" ]; then
    rm -f "$SCRIPT_DIR/early_splash.pid"
fi

# Launch early background splash screen if dependencies exist
if [ -d "$SCRIPT_DIR/.venv" ] && [ -f "$SCRIPT_DIR/.venv/bin/python3" ]; then
    echo -e "  * Disparando Splash Screen antecipado em background..."
    "$SCRIPT_DIR/.venv/bin/python3" "$SCRIPT_DIR/frontend/splash.py" &
elif python3 -c "import PySide6" &>/dev/null; then
    echo -e "  * Disparando Splash Screen antecipado em background (system Python)..."
    python3 "$SCRIPT_DIR/frontend/splash.py" &
fi

# Clean temp files and compiler garbage under E/E3
echo -e "  * Removendo arquivos temporários e caches de simulação..."
find "$SCRIPT_DIR" -type f \( -name "*.tmp" -o -name "*.log" -o -name "pout_*.txt" -o -name "field.txt" -o -name "potential.txt" -o -name "charge_density.dat" -o -name "potential_field.dat" -o -name "trajectory_density.dat" -o -name "tof.txt" -o -name "tof_histo.txt" -o -name "tof_out.txt" -o -name "trajectories.txt" -o -name "geometry.obj" -o -name "config_scenario.json" \) -delete 2>/dev/null || true
echo -e "  * [OK] Limpeza concluída!"

# 1. Environment & Display Server Checks
echo -e "\n${BLUE}[1/5] Checking environment & display server...${NC}"
IS_WSL=false
if grep -qE "(Microsoft|WSL)" /proc/version 2>/dev/null; then
    IS_WSL=true
    echo -e "  * WSL Environment detected."
fi

if [ -n "$DISPLAY" ]; then
    echo -e "  * Display server found: DISPLAY=$DISPLAY"
elif [ -n "$WAYLAND_DISPLAY" ]; then
    echo -e "  * Wayland server found: WAYLAND_DISPLAY=$WAYLAND_DISPLAY"
else
    if [ "$IS_WSL" = true ]; then
        echo -e "${YELLOW}  ! No DISPLAY variable set in WSL. Setting fallback display (:0)...${NC}"
        export DISPLAY=:0
    else
        echo -e "${RED}  ! WARNING: No Display server detected (DISPLAY/WAYLAND_DISPLAY is empty).${NC}"
        echo -e "${YELLOW}    The graphical interface might fail to launch. If running headless,${NC}"
        echo -e "${YELLOW}    please run inside an active desktop session or configure X11/VcXsrv forwarding.${NC}"
    fi
fi

# 2. Check Debian/Ubuntu system packages
echo -e "\n${BLUE}[2/5] Checking system compiler tools and library dependencies...${NC}"
MISSING_SYS_PACKAGES=()

# Check compilation tools
for cmd in g++ make cmake pkg-config python3 python3-venv; do
    if [ "$cmd" = "python3-venv" ]; then
        if python3 -c "import venv" &>/dev/null; then
            echo -e "  * Tool 'python3-venv' is installed (verified via python3 -c 'import venv')."
            continue
        fi
    fi

    if ! command -v "$cmd" &>/dev/null; then
        echo -e "  * Missing tool: $cmd"
        if [ "$cmd" = "g++" ]; then
            MISSING_SYS_PACKAGES+=("g++")
        elif [ "$cmd" = "make" ]; then
            MISSING_SYS_PACKAGES+=("make")
        elif [ "$cmd" = "cmake" ]; then
            MISSING_SYS_PACKAGES+=("cmake")
        elif [ "$cmd" = "pkg-config" ]; then
            MISSING_SYS_PACKAGES+=("pkg-config")
        elif [ "$cmd" = "python3" ]; then
            MISSING_SYS_PACKAGES+=("python3")
        elif [ "$cmd" = "python3-venv" ]; then
            MISSING_SYS_PACKAGES+=("python3-venv")
        fi
    else
        echo -e "  * Tool '$cmd' is installed."
    fi
done

# Libraries check using dpkg
declare -A lib_packages=(
    ["libgsl-dev"]="libgsl-dev"
    ["libfontconfig1-dev"]="libfontconfig1-dev"
    ["libfreetype6-dev"]="libfreetype6-dev"
    ["nlohmann-json3-dev"]="nlohmann-json3-dev"
)

for lib in "${!lib_packages[@]}"; do
    if ! dpkg -l | grep -q "^ii  $lib" 2>/dev/null; then
        echo -e "  * Missing library: $lib"
        MISSING_SYS_PACKAGES+=("${lib_packages[$lib]}")
    else
        echo -e "  * Library '$lib' is installed."
    fi
done

# Verify IBSimu package presence
if ! pkg-config --exists ibsimu-1.0.6dev &>/dev/null; then
    echo -e "${YELLOW}  ! Warning: pkg-config could not detect 'ibsimu-1.0.6dev'.${NC}"
    echo -e "    Ensure IBSimu is compiled and installed on this machine (normally in /usr/local)."
fi

# Prompt for sudo install if packages are missing
if [ ${#MISSING_SYS_PACKAGES[@]} -ne 0 ]; then
    echo -e "\n${YELLOW}Missing required system packages: ${MISSING_SYS_PACKAGES[*]}${NC}"
    echo -e "Installing them via apt-get (requires administrative/sudo privileges)..."
    echo -e "  * Updating package indexes..."
    if [ -t 0 ]; then
        sudo apt-get update
        echo -e "  * Installing packages..."
        sudo apt-get install -y "${MISSING_SYS_PACKAGES[@]}"
    else
        echo -e "  * Non-interactive mode detected. Using non-interactive sudo..."
        sudo -n apt-get update &>/dev/null || true
        echo -e "  * Installing packages..."
        sudo -n apt-get install -y "${MISSING_SYS_PACKAGES[@]}" &>/dev/null || true
    fi
else
    echo -e "${GREEN}  * All native compilation and system dependencies are satisfied.${NC}"
fi

# 3. Setup Python Virtual Environment and dependencies
echo -e "\n${BLUE}[3/5] Initializing Python virtual environment...${NC}"
if [ ! -d ".venv" ]; then
    echo -e "  * Creating new virtual environment in .venv..."
    python3 -m venv .venv
fi

echo -e "  * Activating virtual environment..."
source .venv/bin/activate

echo -e "  * Upgrading pip..."
pip install --upgrade pip

echo -e "  * Installing required python packages (PySide6, PyVistaQt, SciPy, NumPy, EzDXF)...${NC}"
pip install PySide6 ezdxf pyvistaqt scipy numpy matplotlib pyvista trame

# 4. Compile Backend
echo -e "\n${BLUE}[4/5] Compiling native C++ backend wrapper (ibsimu_wrapper)...${NC}"
if [ -d "backend" ]; then
    cd backend
    echo -e "  * Building ibsimu_wrapper..."
    make clean || true
    make
    if [ -f "ibsimu_wrapper" ]; then
        echo -e "${GREEN}  * Backend compiled successfully!${NC}"
    else
        echo -e "${RED}  ! Error: Compilation failed. 'ibsimu_wrapper' was not found.${NC}"
        exit 1
    fi
    cd ..
else
    echo -e "${RED}  ! Error: 'backend/' directory not found in the deploy workspace.${NC}"
    exit 1
fi

# 5. Launch application
echo -e "\n${GREEN}[5/5] Launching IBSimion v2.0.1.e3l UI...${NC}"
export QT_QPA_PLATFORM=xcb
export QT_X11_NO_MITSHM=1
export RE_INITIALIZE_VTK_WINDOW=1

echo "  * Configurando atalho de aplicativo profissional (.desktop)..."
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"
INSTALL_DIR="$SCRIPT_DIR"
ICON_PATH="$INSTALL_DIR/frontend/ibsimion_icon.png"

cat << EOF > "$DESKTOP_DIR/ibsimion.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=IBSimion 2.0.1.e3l
Comment=Simulador PIC Nativo Linux
Exec=bash -c "cd $INSTALL_DIR && ./install_and_launch.sh"
Icon=$ICON_PATH
Terminal=false
Categories=Science;Development;
EOF

chmod +x "$DESKTOP_DIR/ibsimion.desktop"
echo "  * [OK] Atalho criado automaticamente! Busque por 'IBSimion' no seu menu de aplicativos."

echo "  * Criando invólucro para acesso global via terminal..."
WRAPPER_TEMP=$(mktemp)
cat << EOF > "$WRAPPER_TEMP"
#!/bin/bash
cd "$INSTALL_DIR" && ./install_and_launch.sh "\$@"
EOF
chmod +x "$WRAPPER_TEMP"

echo "  * Instalando comandos globais em /usr/local/bin..."
if [ -t 0 ]; then
    if sudo cp "$WRAPPER_TEMP" /usr/local/bin/ibsimion && \
       sudo ln -sf /usr/local/bin/ibsimion /usr/local/bin/ibsimion2.0.1 && \
       sudo ln -sf /usr/local/bin/ibsimion /usr/local/bin/IBSimion2.0.1; then
        echo -e "${GREEN}  * [OK] Comandos globais instalados com sucesso! Você pode digitar 'ibsimion', 'ibsimion2.0.1' ou 'IBSimion2.0.1' no terminal.${NC}"
    else
        echo -e "${YELLOW}  ! Falha ao instalar comandos globais. Verifique as permissões de sudo.${NC}"
    fi
else
    if sudo -n cp "$WRAPPER_TEMP" /usr/local/bin/ibsimion &>/dev/null && \
       sudo -n ln -sf /usr/local/bin/ibsimion /usr/local/bin/ibsimion2.0.1 &>/dev/null && \
       sudo -n ln -sf /usr/local/bin/ibsimion /usr/local/bin/IBSimion2.0.1 &>/dev/null; then
        echo -e "${GREEN}  * [OK] Comandos globais instalados em background (sudo sem senha).${NC}"
    else
        echo -e "${YELLOW}  ! Falha ao instalar comandos globais em background (requer senha de sudo).${NC}"
    fi
fi
rm -f "$WRAPPER_TEMP"

if [ "$IS_WSL" = true ]; then
    if [[ "$CURRENT_DIR" =~ \/mnt\/c\/Users\/([^/]+) ]]; then
        WIN_USER="${BASH_REMATCH[1]}"
        WIN_DESKTOP="/mnt/c/Users/$WIN_USER/Desktop"
        if [ -d "$WIN_DESKTOP" ]; then
            echo "  * Configurando atalho silencioso do Windows (.bat) na Área de Trabalho..."
            cat << EOF > "$WIN_DESKTOP/IBSimion.bat"
@echo off
wsl bash -c "cd '$CURRENT_DIR' && ./install_and_launch.sh"
EOF
            echo "  * [OK] Atalho Windows criado na Área de Trabalho do Host!"
        fi
    fi
fi

# First, attempt to launch with the system default OpenGL renderer (enabling hardware acceleration)
echo -e "  * Launching with hardware acceleration enabled (default)..."
set +e
python3 frontend/main.py
EXIT_CODE=$?
set -e

# If the application exits with an error code, attempt automatic fallback to safe software rendering
if [ $EXIT_CODE -ne 0 ]; then
    echo -e "\n${YELLOW}  ! Warning: Application exited with code $EXIT_CODE.${NC}"
    echo -e "    This could be due to a graphics driver/WSLg rendering conflict (e.g. dual GPUs, VM, or Wayland)."
    echo -e "    Attempting automatic fallback to Safe Software Rendering Mode..."
    export LIBGL_ALWAYS_SOFTWARE=1
    python3 frontend/main.py
fi

echo -e "\n${CYAN}================================================================${NC}"
echo -e "${GREEN}                IBSimion has closed successfully.               ${NC}"
echo -e "${CYAN}================================================================${NC}"
