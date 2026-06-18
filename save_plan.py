# -*- coding: utf-8 -*-
"""
IBSimion 2.0 - Gerador Automatizado do Plano de Implementação Atualizado
Este script grava o arquivo 'implementation_plan.md' com o roteiro científico
e as soluções de engenharia reais validadas para o simulador.
"""

import os

plan_content = """# Plano de Implementação: IBSimion 2.0 (Estação de Trabalho Coaxial)

Este documento atua como o plano de arquitetura de software e engenharia física para o **IBSimion 2.0**. Ele consolida as soluções e descobertas técnicas obtidas durante a integração real entre a interface gráfica do Windows e o motor numérico de alta performance IBSimu executado no WSL2.

---

## 1. Engenharia da Fronteira Híbrida (Windows ↔ WSL2)

O acoplamento entre os dois sistemas opera de forma assíncrona, eliminando a necessidade de compilações cruzadas complexas de C++ no host Windows.

```mermaid
graph TD
    subgraph Windows Host (Interface Cientifica Python)
        GUI[Painel de Controle Tkinter]
        JSON_Out[config_scenario_example.json]
        Matplotlib[Visualizador 2D: Trajetorias e Equipotenciais]
    end

    subgraph Ponte de Dados (OneDrive Compartilhado)
        JSON_File[config_scenario_example.json]
        Field_File[potential.txt]
        Traj_File[trajectories.txt]
    end

    subgraph Linux Kernel (WSL2 C++ Backend)
        C_Parser[ibsimion_backend_v2]
        IBSimu_Eng[IBSimu 1.0.6dev]
        Solver[Poisson Solver BiCGSTAB]
        Integrator[Newton-Lorentz Integrator]
    end

    GUI -->|1. Salva Parametros| JSON_Out
    JSON_Out -->|OneDrive Sync| JSON_File
    GUI -->|2. Dispara QProcess/Subprocess| C_Parser
    JSON_File -->|3. Leitura e Parsing| C_Parser
    C_Parser -->|4. Aloca ID >= 7| IBSimu_Eng
    IBSimu_Eng -->|5. Resolve Campo| Solver
    Solver -->|6. Salva Matriz V z,r | Field_File
    IBSimu_Eng -->|7. Calcula F = q*E | Integrator
    Integrator -->|8. Salva Trajetorias| Traj_File
    Field_File -->|9. pcolormesh / contour| Matplotlib
    Traj_File -->|10. Renderiza Feixes| Matplotlib
```

---

## 2. Soluções e Descobertas de Engenharia Física

Durante a depuração do motor físico com a biblioteca industrial **IBSimu 1.0.6dev**, resolvemos três limitações críticas de baixo nível:

### A. Alocação de IDs de Sólidos e Fronteiras
* **O Problema:** Atribuir IDs arbitrários (como `5` ou `10`) aos eletrodos quebrava o vetor interno de sólidos (`_sdata`) do IBSimu, provocando falhas de segmentação de memória (*out-of-bounds*).
* **A Solução:** Reservamos estritamente os IDs de `1` a `4` para os contornos da câmara de vácuo. Os eletrodos do usuário são inseridos dinamicamente de forma sequencial contígua, iniciando obrigatoriamente no **ID `7`**. O próprio IBSimu cresce o vetor de memória sob demanda e atribui os limites Dirichlet perfeitamente.

### B. Verificação de Colisões e Absorção de Partículas
* **O Problema:** O método `Geometry::is_solid` (que retorna o ID do sólido em coordenadas discretas da malha) é privado dentro da classe, gerando erro de compilação quando acessado diretamente.
* **A Solução:** Implementamos a verificação através do método público de malha contínua **`geom.inside(s_id, pos)`**. O motor varre os eletrodos carregados ($ID \ge 7$) e, caso a posição física da partícula intercepte a parede matemática do metal, a integração é interrompida (colisão realista por absorção).

### C. Extração de Campo Vetorial Coaxial
* **O Problema:** A malha de potencial `EpotField` armazena apenas valores escalares ($\Phi$). A tentativa de obter o campo elétrico direto gerava falhas de compilação pela falta do membro `E`.
* **A Solução:** Instanciamos a classe especializada **`EpotEfield`** (com 'f' minúsculo, conforme os cabeçalhos da biblioteca) de forma acoplada: `EpotEfield efield(ep)`. A força real sobre elétrons e íons a cada passo de tempo é obtida diretamente de `efield(pos)`.

### D. Banco de Dados Especializado de Partículas
* **O Problema:** Tentar injetar partículas cilíndricas usando `ParticleDataBase2D` gerava erro de inconsistência de geometria (*Differing geometry modes*) ao tentar rodar simetria cilíndrica (`MODE_CYL`).
* **A Solução:** Alinhamos o banco de dados para utilizar a classe tipada **`ParticleDataBaseCyl`**, estabelecendo compatibilidade física absoluta entre o espaço amostral e o integrador cinemático.

---

## 3. Cronograma e Funcionalidades Implementadas (IBSimion 2.0)

### 🚀 Módulo C++ Integrado de Alta Fidelidade (`ibsimion_backend_v2.cpp`)
* Leitura dinâmica do arquivo `config_scenario_example.json` usando `nlohmann/json`.
* Malha de simetria cilíndrica $MODE\_CYL$ ajustada com passo refinado $h = 1\text{ mm}$ ($360 \times 35$ nós).
* Resolvedor elíptico de Poisson BiCGSTAB autoconsistente com zero de densidade de carga inicial.
* Integração de trajetórias clássica e relativística por passos de tempo cinemáticos estáveis (passo de integração proporcional a $\approx 3$ passos por célula de grade: $dt = 0.33 \cdot h / v_0$).
* Exportação da malha de potenciais em formato estruturado (`potential.txt`) e das trajetórias (`trajectories.txt`).

### 📊 Estação de Trabalho e Visualizador Científico (`ibsimion_2_0_interface_cientifica.py`)
* **Aba 1 (Trajetórias)**: Plotagem em milímetros ($mm$). Eletrodos cilíndricos reais desenhados de forma simétrica com preenchimento translúcido. Trajetórias com mapeamento categórico nítido: Íons de Xenônio ($136.2\text{ u}$) em Azul Neon, Elétrons ($0.00054\text{ u}$) em Rosa Neon.
* **Aba 2 (Contorno de Campos)**: Leitura assíncrona do mapa de potenciais gerado pelo IBSimu. Plotagem térmica contínua combinada com **Linhas Equipotenciais (Contornos)** reais e etiquetas de voltagem ($V$) sobrepostas ao longo de toda a câmara de voo.
* **Aba 3 (Configuração de Feixes)**: Controle em tempo real de parâmetros físicos de injeção diretamente no frontend, permitindo alterar a energia ($eV$), dispersão inicial ($mm$) e carga de múltiplos feixes de forma independente.
* **Terminal Retro-Cyberpunk**: Redirecionamento completo do log de iterações e warnings do compilador de física em C++ diretamente em um painel interativo.

---

## 4. Métricas de Validação Científica

O sistema é considerado **Aprovado** e pronto para produção acadêmica sob os seguintes critérios:
1. **Conservação de Trajetória Retilínea**: Com os eletrodos aterrados ($0\text{ V}$), o feixe deve cruzar a câmara em linha reta perfeita (campo $\vec{E} = 0$).
2. **Convergência Matemática**: O resíduo máximo da equação de Poisson deve decair de forma contínua até atingir tolerância $\le 10^{-5}$.
3. **Colisão Física**: Nenhuma partícula pode ultrapassar a parede de um eletrodo condutor (absorção total verificada no arquivo de saída).
4. **Resolução de Escalas**: Todas as coordenadas na interface Python devem bater exatamente com as dimensões de projeto do JSON, sem distorções de renderização.

---
*IBSimion 2.0 - Desenvolvido em Macaé, RJ, Brasil (2026).*
"""

# Cria e salva o plano de implementação
with open("implementation_plan.md", "w", encoding="utf-8") as f:
    f.write(plan_content)

print("[SUCESSO] Plano de Implementação 'implementation_plan.md' gerado!")