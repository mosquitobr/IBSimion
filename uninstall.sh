#!/bin/bash
# =============================================================================
# IBSimion 2.0.1.e3l - Uninstaller
# Native Linux (Debian/Ubuntu) clean removal script
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
echo -e "${GREEN}    IBSimion v2.0.1.e3l - Uninstaller (Versão de Produção E3)   ${NC}"
echo -e "${CYAN}================================================================${NC}"

# Get absolute path of this script to keep execution localized
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &>/dev/null && pwd )"
cd "$SCRIPT_DIR"

# 1. Remove virtual environment
echo -e "\n${BLUE}[1/4] Removendo ambiente virtual Python (.venv)...${NC}"
if [ -d ".venv" ]; then
    rm -rf .venv
    echo -e "  * Ambiente virtual (.venv) removido com sucesso."
else
    echo -e "  * Ambiente virtual (.venv) não encontrado."
fi

# 2. Clean compiled backend objects
echo -e "\n${BLUE}[2/4] Limpando binários e objetos compilados no backend...${NC}"
if [ -d "backend" ]; then
    if [ -f "backend/Makefile" ]; then
        echo -e "  * Executando 'make clean' no backend..."
        make -C backend clean || true
    else
        echo -e "  * Makefile não encontrado no backend. Removendo wrapper manualmente..."
        rm -f backend/ibsimu_wrapper backend/*.o
    fi
    echo -e "  * Limpeza de compilação de backend concluída."
else
    echo -e "  * Pasta 'backend/' não encontrada."
fi

# 3. Remove local __pycache__ directories and diagnostic files
echo -e "\n${BLUE}[3/4] Removendo caches locais (__pycache__)...${NC}"
find "$SCRIPT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo -e "  * Caches locais limpos."

# 4. Remove shortcuts and global terminal commands
echo -e "\n${BLUE}[4/4] Removendo atalhos e comandos globais...${NC}"

# Desktop launcher
DESKTOP_FILE="$HOME/.local/share/applications/ibsimion.desktop"
if [ -f "$DESKTOP_FILE" ]; then
    rm -f "$DESKTOP_FILE"
    echo -e "  * Atalho de desktop ($DESKTOP_FILE) removido."
else
    echo -e "  * Atalho de desktop não encontrado."
fi

# Global terminal links
GLOBAL_CMDS=("/usr/local/bin/ibsimion" "/usr/local/bin/ibsimion2.0.1" "/usr/local/bin/IBSimion2.0.1")
for cmd in "${GLOBAL_CMDS[@]}"; do
    if [ -f "$cmd" ] || [ -L "$cmd" ]; then
        echo -e "  * Removendo link global: $cmd..."
        if [ -t 0 ]; then
            sudo rm -f "$cmd" || echo -e "${YELLOW}  ! Não foi possível remover $cmd. Tente com privilégios de sudo.${NC}"
        else
            sudo -n rm -f "$cmd" &>/dev/null || true
        fi
    fi
done

# Host desktop shortcut if in WSL
IS_WSL=false
if grep -qE "(Microsoft|WSL)" /proc/version 2>/dev/null; then
    IS_WSL=true
fi
if [ "$IS_WSL" = true ]; then
    # Try both CURRENT_DIR and SCRIPT_DIR to cover possible Windows paths
    for path in "$SCRIPT_DIR" "$CURRENT_DIR"; do
        if [ -n "$path" ] && [[ "$path" =~ \/mnt\/c\/Users\/([^/]+) ]]; then
            WIN_USER="${BASH_REMATCH[1]}"
            WIN_DESKTOP="/mnt/c/Users/$WIN_USER/Desktop"
            if [ -d "$WIN_DESKTOP" ] && [ -f "$WIN_DESKTOP/IBSimion.bat" ]; then
                rm -f "$WIN_DESKTOP/IBSimion.bat"
                echo -e "  * Atalho na Área de Trabalho do Windows removido."
                break
            fi
        fi
    done
fi

echo -e "\n${GREEN}Desinstalação e limpeza concluídas com sucesso!${NC}"
echo -e "${CYAN}================================================================${NC}"
