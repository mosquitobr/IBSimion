# Plano de Implementação: IBSimion

Desenvolvimento de uma aplicação desktop moderna para Windows (IBSimion) com suporte bilíngue (Português/Inglês) que atua como interface visual e otimizadora para o resolvedor de física de feixes e ótica de partículas **IBSimu** (C++).

---

## 1. Arquitetura e Engenharia do Sistema

A aplicação utilizará uma **arquitetura híbrida Windows/WSLg**:

```mermaid
graph TD
    subgraph Windows Host (Frontend)
        UI[GUI PySide6 / PyQt6]
        Vis[PyVista 3D Viewport]
        Opt[Módulo de Otimização - SciPy/Optuna]
        UI --> Vis
        UI --> Opt
    end

    subgraph WSLg (Backend)
        CLI[Wrapper C++ / CLI IBSimu]
        Solv[Poisson Solver / Trajectory Solver]
        PIC[Módulo PIC & CW]
        CLI --> Solv
        CLI --> PIC
    end

    UI -- WSL command (wsl make / exec) --> CLI
    CLI -- Arquivos de Saída (tof.txt, geom.dat) --> UI
```

* **Frontend (Windows):** Interface gráfica moderna construída com **PySide6 (Qt para Python)**. Integração de um painel de renderização 3D dinâmico usando **PyVista / VTK** e gráficos de análise temporal com **Matplotlib**.
* **Backend (WSLg):** O motor de cálculo **IBSimu (C++)** roda compilado nativamente sob WSLg, aproveitando o compilador GCC e a biblioteca GSL de Linux.
* **Comunicação:** O Python no Windows orquestra a execução enviando comandos via `subprocess` (ex: `wsl make` e `wsl ./tofl203d`) e trocando dados via arquivos estruturados (DXF, STL, formatos de saída como `tof.txt` e `tofgeom.dat` gerados pelo IBSimu).

---

## 2. Funcionalidades Detalhadas por Módulo

### Módulo de Geometria e Malha (Mesh)
* **Importação CAD:** Permite carregar arquivos **3D STL** (eletrodos volumétricos) e **2D DXF** (perfis e coordenadas de grades/lentes).
* **Painel de Alinhamento na GUI:** Interface gráfica para manipular os sólidos importados antes de rodar a simulação:
  * Translação nos eixos $X, Y, Z$.
  * Rotação e Escala (para converter facilmente de mm/polegadas para metros exigidos pelo IBSimu).
* **Parâmetros da Malha (Mesh):** Configuração gráfica do tamanho da malha ($h$) global e das dimensões da caixa de simulação (`Geometry geom`), mapeando diretamente para o código C++.

### Módulo de Simulação (CW e PIC)
* **Estado Estacionário (CW):** Configurações para feixes contínuos e cálculo iterativo de carga espacial auto-consistente.
* **Dinâmica Temporal (PIC):**
  * Configuração do passo de tempo ($dt$) e tempo final de voo ($T_{final}$).
  * Aviso visual de violação da condição de Courant-Friedrichs-Lewy (CFL: $dt < h/v_{max}$) para garantir a convergência.
  * Agendamento automático e geração de snapshots temporais (`pout_t.txt`).

### Módulo de Otimização Paramétrica
* **Loop de Otimização no Python:** Utiliza a biblioteca `scipy.optimize` (ex: Nelder-Mead) ou `optuna` (Otimização Bayesiana) para ajustar as tensões dos eletrodos em lote.
* **Função Objetivo Ponderada (Híbrida):**
  $$\text{Loss} = - W_{\text{trans}} \cdot \text{Transmissão} + W_{\text{emit}} \cdot \text{Emitância}_{\text{RMS}} + W_{\text{tof}} \cdot \text{FWHM}_{\text{TOF}}$$
  O usuário define os pesos ($W$) na GUI para focar em transmissão, colimação ou resolução de tempo de voo.
* **Acompanhamento Gráfico:** Gráfico de convergência da função objetivo em tempo real.

### Visualização Gráfica 3D & 2D
* **Visualizador PyVista/VTK:** Exibição interativa da caixa de simulação com os sólidos 3D (STL) renderizados.
* **Renderização de Trajetórias:** Traça as linhas de trajetória no espaço 3D, colorindo-as dinamicamente por massa, carga ou energia dos íons.
* **Plots 2D (ZX, ZY, XY) e Animações:** Exibição dinâmica de trajetórias e criação automática de vídeos/GIFs a partir dos snapshots do PIC.

---

## 3. Plano de Desenvolvimento

### Fase 1: Setup do Projeto e Wrapper C++
1. Estruturação do repositório no Windows.
2. Criação do compilador/Makefile dentro do WSLg.
3. Criação de um executável C++ parametrizado que aceita argumentos de linha de comando ou arquivo JSON de configuração para tensões, tamanho de malha ($h$), partículas e tempos de simulação.

### Fase 2: Interface Gráfica (GUI) em PySide6
1. Design de tela moderno, premium (Dark Mode, layout fluído, suporte multilíngue PT/EN).
2. Abas de: Configuração Geral, Importação de Geometrias (STL/DXF), Configuração de Feixe/Modo (CW vs. PIC) e Otimização.

### Fase 3: Integração 3D (PyVista) e Comunicação
1. Implementação do widget 3D na GUI com PyVista para mostrar a geometria da malha e trajetórias de partículas lidas dos outputs (`tof.txt`).
2. Parser para ler arquivos de geometria e trajetórias gerados pelo IBSimu.

### Fase 4: Loop de Otimização e Gráficos de Análise
1. Implementação do algoritmo de otimização em Python alimentando as iterações de simulação.
2. Integração de histogramas de tempo de voo e gráficos de convergência.

---

## 4. Plano de Verificação

### Testes de Integração
* **Build e Linkage:** Comando automatizado para compilar o IBSimu sob o WSLg e testar a comunicação entre o Python (Windows) e o binário gerado (Linux).
* **Paridade de Resultados:** Simulação do caso de teste `tofl203d.cpp` original pelo app visual e validação de que os dados finais de TOF (`tof_histo.txt`) coincidem exatamente com o histórico gerado previamente.

### Validação Manual de Usabilidade
* Carregamento de um arquivo STL personalizado na GUI, translação no visualizador, e execução de uma simulação curta com e sem otimizador para verificar se os potenciais alteram as trajetórias no painel 3D.
