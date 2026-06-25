<img src="frontend/ibsimion_icon.png" width="90" align="right" />

# IBSimion v2.0.1.e3l (Ambiente Integrado Linux/WSL)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/Version-v2.0.1.e3l-brightgreen.svg)](#)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%28Ubuntu%2FDebian%29%20%7C%20WSLg-orange.svg)](#)

**IBSimion** é uma suíte de software projetada para engenharia de óptica de partículas carregadas, realizando simulações de trajetória e cálculo de carga espacial auticonsistente em sistemas nativos Linux (incluindo WSL/WSLg).

**IBSimion** is a software suite designed for charged particle optics engineering, executing trajectory tracking and self-consistent space-charge calculations on native Linux systems (including WSL/WSLg).

---

## 🛠️ Requisitos de Sistema / System Requirements

| Componente / Component | Especificação Requerida / Specification | Função / Purpose |
| :--- | :--- | :--- |
| **Compilador / Compiler** | `g++` (C++11+) & `make`/`cmake` | Compilação do resolvedor nativo `ibsimu_wrapper` / Builds the native C++ solver. |
| **Python** | Python 3.10+ & `python3-venv` | Interface gráfica de usuário (PySide6) / Runs PySide6 GUI. |
| **Bibliotecas / Libraries** | `libgsl-dev` (GSL), `libfontconfig1-dev`, `libfreetype6-dev`, `libxcb-cursor0` | Cálculo matemático e renderização gráfica OpenGL/VTK / OpenGL/VTK rendering & GSL math solver. |
| **Física Core / Physics Core** | **IBSimu (Ion Beam Simulator)** v1.0.6dev | Biblioteca física de óptica de partículas carregadas / Particle optics simulation core library. <br> *Ref:* [Kalvas et al., RSI 2010](https://pubs.aip.org/aip/rsi/article-abstract/81/2/02B703/1071990/IBSIMU-A-three-dimensional-simulation-software-for) |


---

## 📂 Estrutura de Arquivos / Project Manifest

Consulte o arquivo [MANIFEST.md](MANIFEST.md) para obter a listagem completa e detalhada dos arquivos e scripts. / Refer to the [MANIFEST.md](MANIFEST.md) file for a complete and detailed catalog of all files and scripts.

* **[install_and_launch.sh](install_and_launch.sh)**:
  * **PT**: Script de pipeline automatizado para verificação de dependências, compilação e inicialização.
  * **EN**: Automated pipeline script for dependency verification, compilation, and execution.
* **[uninstall.sh](uninstall.sh)**:
  * **PT**: Script de remoção limpa do ambiente de desenvolvimento, caches, binários e atalhos.
  * **EN**: Clean removal script for development virtual environment, caches, binaries, and system shortcuts.
* **backend/**:
  * **PT**: Código-fonte C++ e Makefile do resolvedor nativo.
  * **EN**: Native C++ solver source code and compilation Makefile.
* **frontend/**:
  * **PT**: Interface gráfica em PySide6 e componentes gráficos 3D (PyVista/VTK).
  * **EN**: GUI implementation in PySide6 and 3D viewport modules (PyVista/VTK).
* **data/**:
  * **PT**: Modelos CAD (DXF) e tabelas de mapeamento de solenoides.
  * **EN**: Electrode geometry files (DXF) and magnetostatic solenoid lookup tables.
* **bent/**:
  * **PT**: Suíte de regressão para validação física automatizada.
  * **EN**: Automated regression suite for physical benchmark validation.

---


## 🚀 Instalação e Execução / Installation & Execution

### Português (PT)
Para auditar as dependências do sistema, criar o ambiente virtual, instalar os pacotes Python, compilar o wrapper C++ e iniciar a interface gráfica, execute o script de pipeline automatizado no terminal:

```bash
chmod +x install_and_launch.sh
./install_and_launch.sh
```

- **Acesso Global**: O instalador registra atalhos globais de terminal (`ibsimion`, `ibsimion2.0.1` ou `IBSimion2.0.1`) no diretório `/usr/local/bin/`.
- **Atalho de Desktop**: Um arquivo de atalho nativo é adicionado a `$HOME/.local/share/applications/ibsimion.desktop` para permitir a inicialização via menu de aplicativos.

---

### English (EN)
To verify system dependencies, build the local Python virtual environment, install packages, compile the C++ backend wrapper, and launch the user interface, execute the automated pipeline script in your shell:

```bash
chmod +x install_and_launch.sh
./install_and_launch.sh
```

- **Global CLI Invocation**: The installer registers system links (`ibsimion`, `ibsimion2.0.1`, or `IBSimion2.0.1`) under `/usr/local/bin/` for global command execution.
- **Desktop Launcher**: A standard application launcher is generated at `$HOME/.local/share/applications/ibsimion.desktop` to enable starting the tool from your system app menus.
