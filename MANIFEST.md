# IBSimion E3 - Catálogo de Arquivos e Manifesto Técnico

Este manifesto cataloga e descreve detalhadamente os componentes da **Versão de Produção E3** (Ambiente Integrado Linux/WSL) do ecossistema **IBSimion v2.0.1.e3l**.

---

## 📂 Árvore de Diretórios / Directory Tree

```
E/E3/
├── install_and_launch.sh  # Script de pipeline automatizado (instalação/inicialização)
├── uninstall.sh           # Script de desinstalação limpa do ecossistema E3
├── MANIFEST.md            # Este arquivo de catálogo de componentes
├── README.md              # Guia de introdução e requisitos rápidos
├── MANUAL.md              # Manual de modelagem física e otimização científica
├── walkthrough.md         # Registro técnico de engenharia e decisões de projeto
├── LICENSE                # Licença de distribuição
├── backend/               # Código do motor físico C++ e resolvedor local
│   ├── Makefile           # Instruções de compilação C++ do wrapper
│   ├── ibsimu_wrapper.cpp # Implementação do wrapper para biblioteca IBSimu
│   ├── ibsimu_wrapper     # Binário nativo compilado do resolvedor
│   └── pdb.dat            # Banco de dados de propriedades de partículas
├── frontend/              # Interface gráfica e componentes visuais
│   ├── main.py            # Ponto de entrada gráfico em PySide6
│   ├── pyvista_widget.py  # Módulo de integração da renderização 3D PyVista/VTK
│   ├── splash.py          # Splash screen inicial leve de inicialização
│   └── ibsimion_icon.png  # Logotipo oficial do software
├── data/                  # Malhas CAD/DXF e tabelas de mapeamento de campo
│   ├── einzel3d.dxf       # Malha de eletrodos da lente de foco de Einzel 3D
│   ├── tofl203d.dxf       # Malha de eletrodos do espectrômetro TOF
│   └── sol.txt            # Tabela bidimensional de campo magnético do solenoide
└── bent/                  # Testes de regressão e validação numérica (benchmarks)
    ├── run_pipeline.py    # Pipeline automatizado de execução dos testes
    ├── teste1/            # Arquivos do benchmark de regressão do TOF
    ├── teste2/            # Arquivos do benchmark da lente de Einzel
    └── teste3/            # Arquivos do benchmark do Solenoide
```

---

## 🛠️ Descrição Detalhada dos Scripts e Arquivos de Suporte

### 🚀 [install_and_launch.sh](file:///c:/Users/mosqu/OneDrive/Antigravity/IBSimion/E/E3/install_and_launch.sh)
Script em Bash que gerencia todo o ciclo de instalação e inicialização da aplicação:
- **Passo [0/5]**: Executa a limpeza preventiva de processos antigos e cria o splash screen em background.
- **Passo [1/5]**: Valida as conexões do servidor gráfico de display (X11 / WSLg).
- **Passo [2/5]**: Realiza a verificação e instalação automatizada das dependências nativas (`g++`, `make`, `cmake`, `libgsl-dev`, `libfontconfig1-dev`, `libfreetype6-dev`, `nlohmann-json3-dev`).
- **Passo [3/5]**: Inicializa e atualiza o ambiente virtual do Python (`.venv`) instalando os pacotes necessários (`PySide6`, `pyvista`, `ezdxf`, etc.).
- **Passo [4/5]**: Compila o backend nativo em C++ chamando o `Makefile`.
- **Passo [5/5]**: Registra atalhos de sistema/globais e dispara a interface principal do simulador.

### 🗑️ [uninstall.sh](file:///c:/Users/mosqu/OneDrive/Antigravity/IBSimion/E/E3/uninstall.sh)
Script em Bash para remoção limpa do ecossistema local:
- Remove de forma segura o diretório do ambiente virtual Python (`.venv`).
- Aciona o `make clean` no subdiretório `backend/` para eliminar os binários (`ibsimu_wrapper`) e arquivos objetos compilados.
- Realiza a limpeza recursiva de caches locais do Python (`__pycache__`).
- Desvincula as associações do sistema operacional, removendo o arquivo launcher (`ibsimion.desktop`), os atalhos de terminal globais em `/usr/local/bin/` (`ibsimion`, `ibsimion2.0.1`, `IBSimion2.0.1`) e atalhos na Área de Trabalho do Windows (quando em WSL).
