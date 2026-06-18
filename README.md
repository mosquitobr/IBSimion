# IBSimion 2.0 — Plataforma de Simulação de Óptica de Partículas / Particle Optics Simulation Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Version](https://img.shields.io/badge/version-2.2.0--Beta-blue)
![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-lightgrey)

---

## 🇧🇷 Português

### 🚀 Sobre o Projeto
O **IBSimion 2.0** é uma interface gráfica generalista de alta performance desenvolvida em PySide6 para o motor de simulação **IBSimu (Ion Beam Simulator)**. Ele permite projetar, simular e otimizar lentes eletrostáticas, solenóides magnéticos e sistemas de tempo de voo (TOF) diretamente no ecossistema Windows moderno (10/11), utilizando processamento paralelo e renderização tridimensional interativa.

### 💎 Recursos Principais
* **Ingestão CAD em Lote (.DXF):** Importação automática de múltiplas camadas geométricas simultaneamente com atribuição dinâmica de potenciais de Dirichlet.
* **Mapeamento Magnético Universal (.TXT):** Leitura algébrica e escalonamento automático de mapas de campo axial para simulação de solenóides.
* **Injeção de Feixe 3D Avançada:** Definição completa de feixes contínuos (CW) utilizando bases ortonormais arbitrárias para controle angular preciso da trajetória.
* **Pipeline de Diagnóstico Automatizado:** Análise em tempo real de matrizes de fase com cálculo de parâmetros Twiss (\alpha, \beta, \epsilon) e espectrometria de Tempo de Voo (TOF).

### 🛠️ Pré-requisitos para Execução (Windows)
* Sistema Operacional Windows 10 ou 11 (64-bit).
* Microsoft Visual C++ Redistributable x64 instalado.

---

## 🇺🇸 English

### 🚀 About the Project
**IBSimion 2.0** is a high-performance, general-purpose graphical user interface developed in PySide6 for the **IBSimu (Ion Beam Simulator)** engine. It enables the design, simulation, and optimization of electrostatic lenses, magnetic solenoids, and Time-Of-Flight (TOF) systems directly within a modern Windows environment (10/11), leveraging parallel processing and interactive 3D rendering.

### 💎 Key Features
* **Batch CAD Ingestion (.DXF):** Automatic importing of multiple geometric layers simultaneously with dynamic Dirichlet potential mapping.
* **Universal Magnetic Mapping (.TXT):** Algebraic parsing and automatic scaling of axial field maps for solenoid simulations.
* **Advanced 3D Beam Injection:** Full definition of continuous-wave (CW) beams utilizing arbitrary orthonormal bases for precise angular trajectory control.
* **Automated Diagnostic Pipeline:** Real-time phase-space matrix analysis with Twiss parameter (\alpha, \beta, \epsilon) calculation and Time-Of-Flight (TOF) spectrometry.

### 🛠️ Execution Prerequisites (Windows)
* Windows 10 or 11 Operating System (64-bit).
* Microsoft Visual C++ Redistributable x64 installed.

---

## 📊 Galeria de Validação / Validation Gallery

| 🇧🇷 Diagnóstico Avançado 2D | 🇺🇸 Interactive 3D Trajectories |
|---|---|
| ![Campos 2D](./docs/images/image_86b062.jpg) | ![Trajetórias 3D](./docs/images/image_53ebca.jpg) |
| *Escala de potenciais e densidade de carga.* | *Feixe de Argônio focalizado transpassando a Lente.* |

| 🇧🇷 Espectro de Tempo de Voo (TOF) | 🇺🇸 Transverse Phase Space (X vs Y) |
|---|---|
| ![TOF](./docs/images/image_53e903.png) | ![Fase Transversal](./docs/images/image_53e8e1.jpg) |
| *Resolução temporal com erro relativo de 0.02%.* | *Distribuição espacial de dispersão no detector.* |

---

## 📜 Licença / License
Este projeto está licensed sob a Licença MIT - veja o arquivo LICENSE para detalhes.
This project is licensed under the MIT License - see the LICENSE file for details.
