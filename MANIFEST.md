# IBSimion E4 - Catálogo de Arquivos e Manifesto Técnico / Technical Manifest & File Catalog

Este manifesto cataloga e descreve detalhadamente os componentes da **Versão de Produção E4** (Ambiente Integrado Linux/WSL/Nativo) do ecossistema **IBSimion v2.0.1.e4l**.

This manifesto catalogs and describes in detail the components of **Production Version E4** (Integrated Linux/WSL/Native Environment) of the **IBSimion v2.0.1.e4l** ecosystem.

---

## 📂 Árvore de Diretórios / Directory Tree

```
E/E4/
├── .gitignore             # Regras de exclusão de artefatos e binários / Exclusion rules for build artifacts & binaries
├── install_and_launch.sh  # Script de pipeline automatizado (instalação/inicialização) / Automated pipeline script
├── uninstall.sh           # Script de desinstalação limpa / Clean uninstallation script
├── MANIFEST.md            # Este arquivo de manifesto / This manifest file
├── README.md              # Guia rápido de introdução / Quick introduction guide
├── MANUAL.md              # Manual de modelagem e física / Physics modeling manual
├── LICENSE                # Licença / License
├── backend/               # Código do motor físico C++ / C++ physical engine code
│   ├── Makefile           # Instruções de compilação C++ / C++ compilation Makefile
│   ├── ibsimu_wrapper.cpp # Implementação do wrapper para biblioteca IBSimu / IBSimu wrapper code
│   ├── config_scenario_example.json # Modelo de configuração de cenário JSON / Reference scenario configuration JSON
│   ├── config_scenario_test4.json   # Configuração de teste para geometrias STL / Test configuration for STL geometries
│   └── config_pic_test.json         # Configuração de teste para simulações PIC / Test configuration for PIC simulations
├── frontend/              # Interface gráfica e componentes / GUI and components
│   ├── main.py            # Ponto de entrada gráfico em PySide6 / PySide6 entry point
│   ├── pyvista_widget.py  # Integração do visualizador PyVista / PyVista viewer integration
│   ├── splash.py          # Splash screen inicial leve / Lightweight splash screen
│   ├── ibsimion_icon.png  # Logotipo oficial / Official logo
│   └── methods.txt        # Mapeamento de métodos do frontend / Frontend methods reference
├── data/                  # Malhas CAD/DXF/STL e mapas magnéticos / CAD/DXF/STL meshes and magnetic maps
│   ├── einzel3d.dxf       # Lente de Einzel 3D / 3D Einzel lens
│   ├── tofl203d.dxf       # Espectrômetro TOF 3D / 3D TOF spectrometer
│   ├── sol.txt            # Campo do solenoide / Solenoid magnetic field map
│   ├── slit_assembly_plasma_1.stl  # Malha 3D STL - Eletrodo de Plasma / 3D STL Mesh - Plasma Electrode
│   ├── slit_assembly_puller_2.stl  # Malha 3D STL - Eletrodo Puller / 3D STL Mesh - Puller Electrode
│   └── slit_assembly_gnd_3.stl     # Malha 3D STL - Eletrodo de Terra / 3D STL Mesh - Ground Electrode
└── bent/                  # Testes de regressão e validação / Regression benchmarks
    ├── run_pipeline.py    # Execução automatizada de testes / Automated regression pipeline
    ├── teste1/            # Benchmark TOF
    │   ├── Makefile       # Compilação do benchmark TOF / TOF benchmark Makefile
    │   ├── tofl203d.cpp   # Código C++ do benchmark TOF / TOF benchmark C++ code
    │   ├── tofl203d.dxf   # Geometria DXF TOF / TOF DXF geometry
    │   └── config_scenario1.json # Cenário de simulação TOF / TOF simulation scenario
    ├── teste2/            # Benchmark Einzel
    │   ├── Makefile       # Compilação do benchmark Einzel / Einzel benchmark Makefile
    │   ├── einzel3d.cpp   # Código C++ do benchmark Einzel / Einzel benchmark C++ code
    │   ├── einzel3d.dxf   # Geometria DXF Einzel / Einzel DXF geometry
    │   └── regression_test.py # Script de verificação de regressão / Regression check script
    ├── teste3/            # Benchmark Solenoide
    │   ├── Makefile       # Compilação do benchmark Solenoide / Solenoid benchmark Makefile
    │   ├── solenoid.cpp   # Código C++ do benchmark Solenoide / Solenoid benchmark C++ code
    │   └── sol.txt        # Mapa de campo magnético axial / Magnetic field map
    ├── teste4/            # Benchmark Slit3D STL
    │   ├── Makefile       # Compilação do benchmark STL / STL benchmark Makefile
    │   ├── slit3d.cpp     # Código C++ do benchmark STL / STL benchmark C++ code
    │   ├── analysis.cpp   # Ferramenta C++ de análise de trajetórias / C++ trajectory analysis tool
    │   ├── read_stl.py    # Utilitário de leitura de STL / STL reader utility script
    │   ├── slit_assembly_plasma_1.stl  # Eletrodo de Plasma STL / Plasma Electrode STL
    │   ├── slit_assembly_puller_2.stl  # Eletrodo Puller STL / Puller Electrode STL
    │   └── slit_assembly_gnd_3.stl     # Eletrodo Terra STL / Ground Electrode STL
    └── teste5/            # Benchmark Plasma 2D DXF
        ├── Makefile       # Compilação do benchmark Plasma / Plasma benchmark Makefile
        ├── plasma.cpp     # Código C++ do benchmark Plasma / Plasma benchmark C++ code
        └── plasma.dxf     # Geometria DXF de extração de plasma / Plasma extraction DXF geometry
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
