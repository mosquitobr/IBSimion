# -*- coding: utf-8 -*-
"""
IBSimion 2.0 - Gerador Automatizado do Roteiro de Integracao
Este script resolve o problema de copia/colagem do navegador e grava o arquivo
'next_steps_v2.md' com a formatacao Markdown original intacta.
"""

import os

roteiro_content = """# Roteiro de Implementação: IBSimion 2.0 (Fronteira Híbrida C++/Python)

Este documento descreve as etapas de codificação que devem ser repassadas ao agente do **Antigravity IDE** para construir a integração real entre a interface gráfica (Windows) e o resolvedor físico IBSimu (WSL2).

## Passo 1: O Pipeline de Execução Híbrida (Python -> WSL2)

O frontend em Python não deve chamar funções C++ diretamente via bindings complexos (como Swig ou Pybind11), que exigem compilação cruzada difícil no Windows. Em vez disso, utilizaremos um **pipeline de subprocessos via CLI**:

1. A GUI do Windows salva o arquivo de configuração do cenário em `config_scenario.json`.

2. A classe de execução no Python inicia uma chamada assíncrona usando `QProcess`:

   ```
   process = QtCore.QProcess()
   process.start("wsl", ["./ibsimion_backend", "config_scenario.json"])
   ```

3. O `QProcess` captura a saída padrão (`stdout`) do C++ em tempo real e emite sinais para atualizar a janela de Log e a barra de progresso da GUI.

## Passo 2: O Parser Dinâmico de Geometria em C++

No backend C++, precisaremos ler o arquivo JSON. Recomenda-se o uso da biblioteca leve `nlohmann/json` (header-only). O motor C++ deve ler as chaves de configuração e instanciar dinamicamente os objetos geométricos do IBSimu:

* **Tratamento de Malhas e STL:** O IBSimu suporta o mapeamento de sólidos complexos através da classe `STLGeometry` ou definindo funções de contorno matemáticas. Sólidos importados via STL devem ter suas coordenadas transladadas e rotacionadas com base nas matrizes especificadas pelo JSON antes de inicializar o resolvedor de Poisson.

* **Atribuição de Fronteiras:** A malha de potencial (`Ep2D` ou `Ep3D`) deve varrer os IDs dos eletrodos informados no JSON e aplicar a condição de contorno correspondente: Dirichlet (potencial fixo $V$) ou Neumann (derivada nula).

## Passo 3: Algoritmo de Sub-Stepping Temporal para Elétrons (Modo PIC)

Para simular elétrons de forma estável ao lado de íons pesados sem violar a condição de estabilidade de Courant-Friedrichs-Lewy (CFL):

1. Durante a integração de trajetória na classe `TrajectoryDiagnostics` ou no loop PIC customizado do IBSimu, verifique a massa $m$ da partícula.

2. Se $m < 0.1 \\text{ u}$ (elétrons):

   * O passo de tempo local $dt_{sub}$ é reduzido: $dt_{sub} = dt_{global} / 1000$.

   * A partícula realiza 1000 micro-iterações de aceleração (Lorentz Force Solver) e translação para cada único passo $dt_{global}$ dado pelos íons pesados.

3. Isso garante estabilidade matemática, impede que o elétron seja deletado por sair dos limites da malha em uma única iteração e mantém o tempo de processamento dos íons rápido.

## Passo 4: Exportação de Campos 3D para Análise na GUI

Após a convergência do resolvedor de Poisson, o backend C++ deve exportar os resultados em matrizes binárias ou estruturadas simples em formato `.txt` na pasta temporária de intercâmbio de dados:

* `potential_field.dat`: Arquivo estruturado contendo $X, Y, Z, V$ para plotagem de curvas equipotenciais.

* `charge_density.dat`: Densidade de carga espacial $\\rho(x,y,z)$ para a aba de densidades.

* `trajectories.txt`: Coordenadas das trajetórias de partículas contendo $X, Y, Z, m, q, t$, permitindo que o PyVista as diferencie por cores discretas no frontend.
"""

filepath = "next_steps_v2.md"
with open(filepath, "w", encoding="utf-8") as f:
    f.write(roteiro_content)

print(f"[SUCESSO] O arquivo '{filepath}' foi gravado com a formatacao perfeita!")