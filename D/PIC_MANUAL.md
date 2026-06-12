# Manual de Simulação e Animação no Modo PIC (Particle-in-Cell)

Este manual descreve o fluxo de trabalho completo para configurar, executar, animar e exportar simulações dinâmicas de ótica de íons no modo **PIC** utilizando o **IBSimion**.

---

## 1. O que é a Simulação PIC no IBSimion?

Ao contrário do modo **CW (Continuous Wave / Estado Estacionário)** — no qual as partículas são tratadas como correntes contínuas e as trajetórias são calculadas de ponta a ponta com carga espacial estática —, o modo **PIC (Particle-in-Cell)** resolve a dinâmica temporal. 

As partículas são agrupadas em pacotes compactos no tempo ($t=0$) e propagadas através da malha eletrostática em passos discretos de tempo ($dt$). A cada passo de tempo:
1. A posição e a velocidade de cada partícula são atualizadas.
2. A densidade de carga espacial na malha é recalculada.
3. A equação de Poisson é resolvida para atualizar o potencial elétrico e os campos de força de forma auto-consistente.
4. Snapshots do estado físico das partículas são salvos no disco no formato `pout_<tempo>.txt`.

Este modo é vital para projetar **Espectrômetros de Tempo de Voo (TOF-MS)** e analisar a dispersão temporal, resoluções de pico de massa e perfis de extração pulsada.

---

## 2. Guia Passo a Passo

### Passo 2.1: Iniciar o Aplicativo
Abra a pasta `D` no Windows Explorer e dê um duplo clique em **`run_ibsimion.bat`** (ou execute diretamente o `dist/IBSimion/IBSimion.exe`). A interface gráfica moderna (Dark Mode) em português e inglês se abrirá.

### Passo 2.2: Carregar a Geometria CAD
1. Vá para a aba **Importação & CAD** (CAD & Import).
2. Selecione o **Modo de Importação** (Import Mode):
   - **DXF (2D):** Utiliza o perfil bidimensional rotacionado definido em um arquivo DXF (ex: `tofl203d.dxf` padrão da pasta `backend`).
   - **STL (3D):** Habilita caixas individuais para carregar arquivos de malha 3D (.stl) para cada eletrodo (Detector de Elétrons, Grade Positiva, Grade Negativa, Lente, Tubo de Drift e Detector de Íons).
3. Ajuste os offsets de translação tridimensional (Offset X, Y, Z) em metros, se for necessário alinhar o centro ou deslocar os eletrodos fisicamente.

### Passo 2.3: Configurar Tensões, Feixes e Malha
Na aba **Parâmetros Gerais**:
1. Configure as tensões aplicadas a cada eletrodo usando os sliders ou caixas de texto.
2. Na caixa de **Parâmetros do Feixe**, configure a contagem de partículas por espécie (`Npart1`, `Npart2`, `Npart3`), carga e massas em unidades de massa atômica (u) (ex: `136.2`, `137.2`, `138.2`).
3. Em **Dimensões da Malha**, configure o passo espacial $h$ (ex: `0.0005` m para alta fidelidade ou `0.001` m para simulações de teste rápido).

### Passo 2.4: Ativar o Modo PIC e Ajustar o Tempo
Na aba **Simular e Otimizar**:
1. No painel **Modo de Simulação**, altere o dropdown **Modo** de `CW` para `PIC`. Os campos de tempo serão habilitados.
2. Defina o passo de tempo **dt (s)** (ex: `5.0e-8` s) e o tempo final **T_final (s)** (ex: `5.1e-6` s).
3. **Monitore a Condição CFL (Courant-Friedrichs-Lewy):**
   - Logo abaixo dos campos de tempo, o monitor dinâmico verificará a estabilidade matemática do passo de tempo em relação ao tamanho da malha $h$ e à velocidade máxima estimada dos íons ($v_{\text{max}} = \sqrt{\frac{2 q V_{\text{drift}}}{m}}$).
   - Se o passo de tempo for adequado ($dt < h/v_{\text{max}}$), o monitor exibirá **`CFL: OK`** em verde.
   - Caso o passo seja excessivo ($dt \ge h/v_{\text{max}}$), o monitor alertará em vermelho: **`⚠️ Aviso CFL: dt >= h/v_max! Risco de divergência.`**, sugerindo a redução de $dt$ para garantir que as partículas não pulem células de malha inteiras em um único passo.

### Passo 2.5: Executar a Simulação
1. Clique no botão **Executar Simulação Simples** (Run Simple Simulation).
2. Uma barra de rolagem infinita aparecerá, e o motor de física IBSimu será invocado de forma assíncrona no WSL. A interface gráfica continuará responsiva.
3. Ao concluir, o console de status mostrará o tempo total de execução.

### Passo 2.6: Renderizar e Animar os Snapshots 3D
1. Navegue até a aba **Visualizador 3D**.
2. Clique no botão **Carregar Geometria e Trajetórias 3D** (Load 3D Geometry and Trajectories).
3. O painel PyVista lerá a caixa tridimensional dos eletrodos e escaneará todos os arquivos de snapshot `pout_*.txt` gerados na pasta de simulação.
4. **Controle de Animação PIC:**
   - O painel de animação na barra lateral esquerda será ativado.
   - Clique no botão **Animar (Play)**. O visualizador 3D começará a atualizar continuamente a cena de forma interativa, mostrando a propagação das nuvens de partículas (esferas vermelhas) se deslocando através do sistema de lentes e do tubo de drift.
   - Clique em **Pausar (Pause)** a qualquer momento para pausar a animação física.
   - Utilize a barra de **Linha do Tempo (Slider)** para arrastar o cursor e ver o estado exato das partículas em qualquer instante da simulação. O cronômetro exibirá o tempo atualizado (ex: `Tempo: 1.50e-07 s`).

---

## 3. Exportando a Animação como um GIF Animado

Para compartilhar ou utilizar as animações em relatórios acadêmicos, apresentações ou documentações, você pode exportar a sequência temporal em um arquivo GIF animado usando a ferramenta auxiliar integrada no projeto.

1. Certifique-se de que a simulação PIC terminou de rodar no aplicativo e gerou os snapshots `pout_*.txt` na pasta `backend`.
2. Abra um terminal do PowerShell (ou CMD) na pasta `D`.
3. Ative o ambiente virtual e execute o script de exportação:
   ```powershell
   # Ativar ambiente virtual
   .venv\Scripts\activate
   
   # Executar exportador de GIF
   python export_gif.py
   ```
4. O script lerá automaticamente as nuvens de pontos de todos os arquivos temporais em sequência e usará o Matplotlib + Pillow para gerar os frames bidimensionais da trajetória longitudinal.
5. Ao finalizar, o arquivo **`pic_simulation.gif`** será gerado diretamente na pasta `D`. Você pode abri-lo em qualquer navegador web ou visualizador de imagens para assistir ao feixe de íons sendo focalizado e propagado através do tubo de drift.
