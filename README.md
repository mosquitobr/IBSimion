# IBSimion: Simulador de Ótica de Partículas de Alta Performance (Modo PIC e CW)

O **IBSimion** é um software de simulação interativa em 3D voltado para o cálculo e otimização de trajetórias de íons e ótica de feixes de partículas. O sistema integra uma interface gráfica moderna em ambiente Windows com o robusto motor físico em C++ do IBSimu rodando em ambiente Linux de alta performance.

---

## 🛠️ Requisitos de Sistema e Pré-requisitos

Para executar o IBSimion em outros computadores com Windows 10 ou 11, o ambiente híbrido precisa ser configurado seguindo os passos abaixo:

### 1. No Ambiente Windows (Frontend)
O aplicativo principal é portável e não exige instalação de Python global.
* **Arquitetura:** Windows 10 ou 11 (64-bits).
* **Dependência Gráfica:** Drivers de GPU atualizados com suporte a OpenGL (para renderização 3D do PyVista).

### 2. No Ambiente Linux (Backend via WSL2)
O motor físico exige uma distribuição Linux ativa no Windows.

1. **Instalar o WSL2 e Ubuntu:**
   Abra o PowerShell como Administrador e execute:
   ```bash
   wsl --install -d Ubuntu
   ```

2. **Instalar Dependências de Compilação e Bibliotecas de Física:**
   Dentro do terminal do Ubuntu, instale os compiladores e a biblioteca GSL (GNU Scientific Library):
   ```bash
   sudo apt update && sudo apt install -y build-essential cmake libgsl-dev pkg-config
   ```

3. **Instalar o Motor IBSimu:**
   O binário do IBSimu deve ser compilado ou referenciado no PATH do ambiente WSL para que o wrapper C++ faça as chamadas de cálculo de transporte de carga espacial.

---

## 🚀 Como Executar
1. Baixe a última versão estável na aba Releases do GitHub.
2. Certifique-se de que o seu terminal WSL esteja configurado.
3. Dê um duplo clique no arquivo `run_ibsimion.bat` na raiz da pasta. Ele fará a ponte automática entre o executável Windows e o ambiente de simulação.

---

## 📜 Licença e Termos de Uso
Este projeto está licenciado sob a Licença MIT - permitindo o uso, modificação e distribuição livre para fins acadêmicos, de pesquisa e comerciais, desde que mantidos os direitos autorais.

---

## 🤖 Créditos e Governança de IA
O IBSimion foi desenvolvido através de uma arquitetura de engenharia colaborativa tripartite composta por:
* **Especialista de Domínio (Humano):** Concepção física, modelagem de cenários, validação matemática e gerência do projeto.
* **Antigravity IDE:** Orquestração de agentes autônomos, gerenciamento de dependências e automação de compilação (PyInstaller).
* **Gemini (Google):** Geração de código assistida, refinamento de algoritmos genéticos de otimização, resolução de bugs estruturais de interface e monitoramento da condição de Courant-Friedrichs-Lewy (CFL).

Desenvolvido em Macaé, RJ, Brasil — 2026.
