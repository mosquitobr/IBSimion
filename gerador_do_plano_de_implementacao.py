# -*- coding: utf-8 -*-
"""
IBSimion 2.0 - Gerador Automatizado do Plano de Implementacao
Este script resolve o problema de copia/colagem do navegador e grava o arquivo
'implementation_plan.md' com a formatacao Markdown original intacta.
"""

import os

markdown_content = """# Plano de Implementação: IBSimion 2.0 (Generic Particle Simulation Platform)

Desenvolvimento da evolução do IBSimion para uma plataforma genérica, modular e interativa de simulação de ótica de partículas em 3D. O software deixa de ser um script amarrado ao caso de teste VUV-TOF e passa a atuar como um ambiente dinâmica onde o usuário importa geometrias arbitrárias, define eletrodos interativamente, parametriza múltiplos feixes de forma independente e analisa campos escalares/vetoriais complexos.

---

## 1. Nova Arquitetura e Engenharia de Sistema Desacoplada

A comunicação rígida por argumentos de linha de comando será substituída por uma arquitetura baseada em arquivos de configuração dinâmica e geração em tempo real de cenários físicos.

```mermaid
graph TD
    subgraph Windows Host (Frontend PySide6)
        Tree[Árvore de Fluxo do Projeto]
        CAD[Módulo de Setup Interativo STL]
        Vis3D[PyVista Advanced Viewport]
        Plots[Módulo de Contornos e Seções]
        Log[Terminal de Log Integrado]
    end

    subgraph Configuração e Dados
        JSON[Cenário Dinâmico: config_scenario.json]
        MatField[Matrizes 3D: V, E, rho, J]
    end

    subgraph WSL2 / Linux (Backend C++)
        GenApp[Executável C++ Genérico IBSimion]
        Engine[Motor IBSimu 1.0.6]
        SubStep[Módulo de Sub-Stepping Temporal PIC]
        Poisson[Resolvedor de Poisson & Depósito na Malha]
    end

    Tree --> CAD
    CAD --> JSON
    JSON -- Subprocess Pipeline --> GenApp
    GenApp --> Engine
    Engine --> SubStep
    SubStep --> Poisson
    Poisson -- Exportação de Campos --> MatField
    MatField -- Stream/Leitura de Matrizes --> Vis3D
    MatField --> Plots
    GenApp -- Redirecionamento Std::Cout --> Log
```

* **Geração Dinâmica de Geometria:** O Python lê e renderiza arquivos STL/DXF. O usuário clica nos volumes e atribui potenciais. Essa árvore de dados é exportada como um arquivo `config_scenario.json`.

* **Backend C++ Universal:** O código fonte em C++ lê o arquivo JSON, utiliza os construtores geométricos do IBSimu dinamicamente (`Geometry`, `SolidSphere`, `SolidCylinder`, ou malhas de triângulos do STL importado) e monta o domínio de simulação em tempo real.

* **Redirecionamento de Stream (Terminal):** Captura do `stdout` e `stderr` do subprocesso do WSL2 em tempo real, jogando as iterações do resolvedor de Poisson diretamente em uma área dedicada da interface gráfica.

---

## 2. Funcionalidades Detalhadas da Versão 2.0

### A. Módulo CAD Interativo e Árvore de Projeto

* **Estrutura Hierárquica:** Substituição das abas fixas por um painel lateral em árvore (`QTreeView`), permitindo gerenciar:
  * **Geometria:** Adicionar múltiplos arquivos STL/DXF.
  * **Solucionadores de Campo:** Configurar tamanhos de malha ($h$) refinados.
  * **Feixes de Partículas:** Botão `[+ Add New Beam]` para criar e parametrizar feixes independentes na mesma simulação.

* **Mapeamento de Eletrodos via STL:** Ao carregar um arquivo STL, cada sólido fechado (casca) é identificado independentemente. O usuário clica no sólido diretamente na janela 3D e define interativamente seu potencial elétrico ($V$) e o tipo de fronteira (eletrodo ou dielétrico).

### B. Módulo de Física Avançado e Multi-Feixes

* **Parametrização Isolada por Feixe:** Definição individual de parâmetros para cada feixe adicionado: quantidade de macro-partículas, carga ($e$), massa ($u$), corrente total ($A$), emanação e temperaturas iniciais do plasma (paralela e transversal).

* **Solucionador Dinâmico para Elétrons (Sub-Stepping PIC):**
  * Implementação de uma condicional de passo temporal no loop transiente Particle-in-Cell (PIC).
  * Partículas com massa eletrônica ($m_e \\approx 1/1836 \\text{ u}$) disparam automaticamente um sub-passo temporal ($dt_{eletron} = dt_{global} / 1000$) para evitar violação drástica da condição de Courant-Friedrichs-Lewy (CFL: $dt \\le \\frac{h}{v_{\\max}}$), impedindo que elétrons saltem a malha espacial e desapareçam da simulação.

* **Mapeamento Categórico de Cores:** Substituição da escala contínua de cores por coloração categórica discreta no PyVista (ex: Íons de Massa X em Verde, Massa Y em Vermelho, Elétrons em Azul Elétrico), gerando contraste visual instantâneo.

### C. Extração e Visualização de Campos Físicos (Simion/IBSimu Style)

* **Depósito na Malha (Mesh Deposit):** O motor C++ computará a cada ciclo o acúmulo de carga espacial nos nós da malha, gerando as distribuições de:
  * **Densidade de Carga** ($\\rho$)
  * **Densidade de Corrente** ($J$)

* **Exportação de Matrizes:** O backend exportará matrizes estruturadas binárias tri-dimensionais dos campos escalares de voltagem $V(x,y,z)$ e vetoriais do campo elétrico $\\vec{E}(x,y,z)$.

* **Ferramentas de Análise Pós-Ciclo no PyVista:**
  * **Cortes de Seção (Fatiamento):** Planos de corte interativos nos eixos XY, YZ e XZ.
  * **Curvas Equipotenciais:** Plotagem de linhas de contorno de voltagem sobrepostas ao mapa de densidade de carga.
  * **Glow/Volume Rendering:** Renderização volumétrica translúcida para nuvens de densidade de corrente de feixe.

---

## 3. Cronograma de Desenvolvimento (Fases)

### 📅 Fase 1: Motor C++ Dinâmico e Parser JSON

1. Desenvolvimento do parser JSON em C++ (usando bibliotecas leves como `nlohmann/json`).
2. Adaptação do arquivo principal do motor físico para instanciar objetos do IBSimu com base na leitura do arquivo JSON (eliminando variáveis estáticas no código compilado).
3. Implementação da lógica de sub-stepping de tempo para a dinâmica de partículas leves (elétrons).

### 📅 Fase 2: Nova GUI Genérica e Setup STL Interativo

1. Construção da interface com o painel lateral em árvore (`QTreeView`) e gerenciamento de múltiplos feixes.
2. Implementação do algoritmo de ray-casting/seleção no PyVista para permitir o clique em um eletrodo STL e abertura do pop-up de definição de voltagem.
3. Criação do widget de terminal acoplável com atualização assíncrona baseada em `QThread` e `QProcess`.

### 📅 Fase 3: Renderização de Campos e Extração de Gráficos

1. Escrita das rotinas C++ para despejo das matrizes de campo ($\\vec{E}$, $\\rho$, $J$).
2. Implementação no Python dos filtros de fatiamento (`.slice()`) e curvas de nível (`.contour()`) para visualização de equipotenciais.
3. Adição de painel de gráficos interativos com Matplotlib para exibição de curvas de emitação, transmitância histórica e histogramas de tempo de voo (TOF) customizáveis.

---

## 4. Métricas de Verificação e Validação

* **Validação do Sub-Stepping:** Testar a inserção de um feixe puramente eletrônico em uma malha com passos de milímetros e verificar se os elétrons completam suas trajetórias e colidem com os eletrodos coletores em vez de serem deletados por estouro de malha no primeiro quadro.

* **Fidelidade das Equipotenciais:** Comparar os mapas de campo elétrico gerados pelo fatiamento 3D do IBSimion 2.0 com saídas padrão do resolvedor nativo do IBSimu, garantindo erro relativo de interpolação inferior a $0.1\\%$.

* **Estabilidade do Terminal:** Garantir que o envio massivo de dados de log do resolvedor de Poisson via WSL não trave a interface gráfica (GUI thread) do Windows Host.
"""

filepath = "implementation_plan.md"
with open(filepath, "w", encoding="utf-8") as f:
    f.write(markdown_content)

print(f"[SUCESSO] O arquivo '{filepath}' foi gravado com a formatacao perfeita!")