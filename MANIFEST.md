# IBSimion E4 - Catálogo de Arquivos e Manifesto Técnico / Technical Manifest & File Catalog

Este manifesto cataloga e descreve detalhadamente os componentes da **Versão de Produção E4** (Ambiente Integrado Linux/WSL/Nativo) do ecossistema **IBSimion v2.0.1.e4l**.

This manifesto catalogs and describes in detail the components of **Production Version E4** (Integrated Linux/WSL/Native Environment) of the **IBSimion v2.0.1.e4l** ecosystem.

---

## 📂 Árvore de Diretórios / Directory Tree

```
E/E4/
├── install_and_launch.sh  # Script de pipeline automatizado (instalação/inicialização) / Automated pipeline script
├── uninstall.sh           # Script de desinstalação limpa / Clean uninstallation script
├── MANIFEST.md            # Este arquivo de manifesto / This manifest file
├── README.md              # Guia rápido de introdução / Quick introduction guide
├── MANUAL.md              # Manual de modelagem e física / Physics modeling manual
├── LICENSE                # Licença / License
├── backend/               # Código do motor físico C++ / C++ physical engine code
│   └── Makefile           # Instruções de compilação C++ / C++ compilation Makefile
│   └── ibsimu_wrapper.cpp # Implementação do wrapper para biblioteca IBSimu / IBSimu wrapper code
├── frontend/              # Interface gráfica e componentes / GUI and components
│   ├── main.py            # Ponto de entrada gráfico em PySide6 / PySide6 entry point
│   ├── pyvista_widget.py  # Integração do visualizador PyVista / PyVista viewer integration
│   ├── splash.py          # Splash screen inicial leve / Lightweight splash screen
│   └── ibsimion_icon.png  # Logotipo oficial / Official logo
├── data/                  # Malhas CAD/DXF e mapas magnéticos / CAD/DXF meshes and magnetic maps
│   ├── einzel3d.dxf       # Lente de Einzel 3D / 3D Einzel lens
│   ├── tofl203d.dxf       # Espectrômetro TOF 3D / 3D TOF spectrometer
│   └── sol.txt            # Campo do solenoide / Solenoid magnetic field map
└── bent/                  # Testes de regressão e validação / Regression benchmarks
    ├── run_pipeline.py    # Execução automatizada de testes / Automated regression pipeline
    ├── teste1/            # Benchmark TOF
    ├── teste2/            # Benchmark Einzel
    ├── teste3/            # Benchmark Solenoide
    ├── teste4/            # Benchmark Slit3D STL
    └── teste5/            # Benchmark Plasma 2D DXF
```

---

## 🛠️ Descrição dos Scripts de Suporte / Support Scripts Description

### 🚀 [install_and_launch.sh](file:///C:/Antigravity/IBSimion/E/E4/install_and_launch.sh)
- **PT-BR**: Script em Bash que gerencia todo o ciclo de instalação e inicialização da aplicação:
  - **Passo 0**: Limpeza preventiva de processos antigos e execução assíncrona do splash screen.
  - **Passo 1**: Validação de servidor gráfico de display (X11 / WSLg).
  - **Passo 2**: Verificação e instalação de pacotes nativos do sistema (`g++`, `make`, `cmake`, `libgsl-dev`, etc.).
  - **Passo 3**: Isolamento de dependências Python no ambiente virtual `.venv`.
  - **Passo 4**: Compilação limpa do backend nativo C++ (`make clean && make`).
  - **Passo 5**: Integração com o sistema operacional (criação de launchers e atalhos globais) e lançamento do frontend.
- **EN**: Bash script managing the complete installation and launch cycle:
  - **Step 0**: Preventive process cleanup and asynchronous splash screen execution.
  - **Step 1**: Graphical display server validation (X11 / WSLg).
  - **Step 2**: System package check and installation (`g++`, `make`, `cmake`, `libgsl-dev`, etc.).
  - **Step 3**: Python dependency encapsulation inside a `.venv` virtual environment.
  - **Step 4**: Autonomous clean build of the C++ backend wrapper (`make clean && make`).
  - **Step 5**: Desktop launcher integration, terminal symlinks, and application startup.

### 🗑️ [uninstall.sh](file:///C:/Antigravity/IBSimion/E/E4/uninstall.sh)
- **PT-BR**: Script em Bash para desinstalação completa e limpa:
  - Elimina o ambiente virtual do Python (`.venv`).
  - Executa a limpeza do diretório backend chamando o `make clean` para remover binários e objetos.
  - Remove atalhos do sistema criados em `/usr/local/bin` e arquivos `.desktop` globais do gerenciador de janelas.
- **EN**: Bash script for complete and clean uninstallation:
  - Removes the Python virtual environment directory (`.venv`).
  - Calls `make clean` in the backend directory to wipe compiled objects and executables.
  - Deletes symlinks from `/usr/local/bin` and global desktop files from the system menus.
