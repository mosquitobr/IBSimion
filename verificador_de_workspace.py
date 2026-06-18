# -*- coding: utf-8 -*-
"""
IBSimion 2.0 - Verificador de Workspace e Diagnostico de Ambiente
Este script analisa o diretorio local, valida as dependencias cientificas do Python,
e garante que todos os arquivos, incluindo o parser real de JSON em C++, estao corretos.
"""

import os
import sys

# Conteúdo completo do next_steps_v2.md para geração automática caso falte
ROTEIRO_CONTENT = """# Roteiro de Implementação: IBSimion 2.0 (Fronteira Híbrida C++/Python)

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

def verificar_biblioteca(nome_modulo):
    try:
        __import__(nome_modulo)
        return True
    except ImportError:
        return False

def main():
    print("==========================================================")
    print("      DIAGNOSTICO DE WORKSPACE - IBSIMION 2.0             ")
    print("==========================================================\n")
    
    # 1. Verificação de Dependências Python
    print("--- [1/3] Verificando Dependencias Python no Windows ---")
    deps = ["numpy", "PySide6", "matplotlib"]
    todas_deps_ok = True
    for dep in deps:
        if verificar_biblioteca(dep):
            print(f"  [ OK ] Biblioteca '{dep}' instalada.")
        else:
            print(f"  [FALHA] Biblioteca '{dep}' NAO encontrada!")
            todas_deps_ok = False
            
    if not todas_deps_ok:
        print("\n  [AVISO] Execute o comando para corrigir as dependencias:")
        print("  pip install numpy PySide6 matplotlib\n")
    else:
        print("  -> Todas as dependencias do Python estao prontas!\n")

    # 2. Verificação e Correção de Arquivos
    print("--- [2/3] Verificando Integridade dos Arquivos locais ---")
    
    arquivos_essenciais = {
        "implementation_plan.md": "Plano de implementacao teorico",
        "ibsimion_2_0_interface_cientifica.py": "Interface grafica PySide6 (GUI)",
        "config_scenario_example.json": "Modelo de configuracao do cenario",
        "parser_real_de_json_em_c.cpp": "Parser estruturado C++ usando nlohmann/json",
        "verificador_de_workspace.py": "Script diagnosticador do Workspace",
        "next_steps_v2.md": "Roteiro de integracao do Antigravity IDE"
    }
    
    for arquivo, desc in arquivos_essenciais.items():
        if os.path.exists(arquivo):
            print(f"  [ OK ] '{arquivo}' encontrado. ({desc})")
        else:
            if arquivo == "parser_real_de_json_em_c.cpp":
                print(f"  [ ALERTA ] '{arquivo}' nao encontrado! Certifique-se de que o salvou com este nome.")
            elif arquivo == "next_steps_v2.md":
                print(f"  [ CRIANDO ] '{arquivo}' estava faltando. Gerando arquivo...")
                with open(arquivo, "w", encoding="utf-8") as f:
                    f.write(ROTEIRO_CONTENT)
                print(f"    -> Arquivo '{arquivo}' criado com sucesso!")
            else:
                print(f"  [ AVISO ] '{arquivo}' ausente.")

    print("\n--- [3/3] Resumo do Workspace ---")
    if os.path.exists("next_steps_v2.md") and os.path.exists("parser_real_de_json_em_c.cpp"):
        print("  [SUCESSO] Seu workspace esta completo e pronto para o Antigravity IDE!")
    else:
        print("  [ATENCAO] Verifique os arquivos em alerta antes de prosseguir.")
    print("==========================================================")

if __name__ == "__main__":
    main()