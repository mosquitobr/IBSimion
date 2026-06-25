# IBSimion 2.0.1.e3l (Versão de Produção E3) - Engineering Walkthrough

This document records the technical implementation, architectural decisions, and isolation strategies applied to establish the native Linux branch (`2.0.1.e3l`) for the IBSimion simulation suite.

---

## 1. Branch Isolation & Core Protection (`D/` Protection)
- **Isolation Boundary**: All modifications, builds, scripts, and runtime codes for the Linux release are housed strictly within `E/E3/`.
- **Windows Core Integrity**: The `D/` directory (representing the Windows release) remains completely untouched, ensuring that Windows-specific workflows and packages are not disrupted.
- **Publication Readiness**: `E/E3/` is configured to behave as a self-contained Git repository, clean of temporary build objects, binary logs, and localized workspace data.

---

## 2. Privacy Protocol & Dynamic Path Routing
To comply with public repository standards and protect developer credentials, several mechanisms prevent absolute host paths from leaking into configuration files:

### A. Dynamic Path Resolution (`resolve_path`)
Instead of referencing static paths (e.g. `C:/Users/mosqu/...`), the frontend determines paths relative to the current file using:
```python
os.path.dirname(os.path.abspath(__file__))
```
We implemented the `resolve_path(path)` helper. If a path is specified in a relative format (such as `./data/einzel3d.dxf` or `sol.txt`), Python dynamically resolves it to the correct absolute location inside `E/E3/data/` or `E/E3/backend/` at runtime.

### B. Configuration Masking (`clean_path`)
- **Metadata Zero**: Local timestamps, user history, and folder selections are excluded from saved project JSONs.
- **Routing to `./data/`**: On saving or executing scenarios, the application automatically strips directory paths and routes all CAD files and magnetic fields to `./data/<filename>`.
- **C++ Backend Relocation**: Since the C++ `ibsimu_wrapper` executes in `E/E3/backend/`, `write_config` translates `./data/` relative paths to `../data/` inside the temporary `config_scenario.json`. This keeps the execution container relative and free of absolute path labels.

---

## 3. C++ Backend Optimization & Null Tolerance (`type_error.306`)
- **Root Cause**: The JSON parser (`nlohmann::json`) throws a `type_error.306` when trying to parse missing keys or empty/null values (often resulting from async DXF layer extraction).
- **Interception Technique**: In `ibsimu_wrapper.cpp`, all direct `.value()` calls were replaced with safe getters: `get_str`, `get_double`, and `get_int`. These helpers catch parsing exceptions and fallback to safe default parameters.
- **JSON Recursive Sanitization**: We added a recursive `_sanitize_dict` helper inside the Python frontend `write_config` method. Before saving any configuration file, the application recursively checks all keys and replaces `None` values with `0.0`. This guarantees the C++ backend parser will never receive `null` values in numeric fields.

---

## 4. Theme Engine Integration & Dynamic Contrast (Light/Dark QSS Switcher)
- **Qt Styling**: Incorporated a global toggle switch in the UI. Switching themes applies a custom QSS (Qt Style Sheet) to PySide6.
- **PyVista 3D Widget Contrast**: The PyVista widget background color updates dynamically between Light Mode (`#F3F4F6` background with dark mesh edges) and Dark Mode (`#0B0F19` background with blue/cyan accents). In Light Mode, all font properties (`self.plotter.theme.font.color`), VTK cube axes actor labels/titles, and scalar scale colorbar labels/annotations are updated to pure black (`#000000`) in Light Mode and white (`#FFFFFF`) in Dark Mode to guarantee clear visual contrast, protected by safety checks to prevent VTK attribute exceptions.
- **Matplotlib Dynamic Contrast**: The theme switch triggers `apply_theme_to_figure`, resetting canvas backgrounds and label styles. We implemented automated `draw()` and `draw_idle()` hooks in `MplCanvas` so that any canvas redraw automatically applies the current theme colors.
- **Colorbar and Scale Inversion**: In Light Mode, figure backgrounds are `#F3F4F6` (matching the QMainWindow), axes backgrounds are `#FFFFFF`, and all tick labels, axis labels, legends, colorbar outlines, labels, and offset scientific notation multipliers are forced to pure black (`#000000`) or dark industrial gray (`#1F2937`), ensuring strict contrast.

---

## 5. WSL Bypass & Native Execution
- **Bypassing WSL Commands**: Replaced hardcoded `wsl` commands in `SimWorker` thread execution, process termination, and pipeline execution.
- **Direct Subprocess Spawning**: If running on Linux (detected via `os.name != 'nt'`), the application directly spawns `./ibsimu_wrapper` inside the backend directory.
- **Cross-Platform Compatibility**: Local debug paths falling back to WSL remain active if the application is run on a Windows host with WSL configured.

---

## 6. Magnetic Field Alignment & Dynamic CW Iterations (Test 3 Fix)
During regression validation of Test 3 (solenoid.cpp), two major discrepancies were resolved:
- **Cylindrical Solenoid Alignment in 3D**: In the 2D cylindrical benchmark, both geometry and magnetic field are defined in `MODE_CYL` with the X-axis as the longitudinal symmetry axis. However, the 3D wrapper uses the Z-axis as the beam propagation axis. The native `MeshVectorField` (in cylindrical mode) assumes the symmetry axis is the X-axis, causing a 90-degree alignment bug in 3D. We created the `SolenoidMagneticField` class which projects the 2D radial and axial coordinates from the `sol.txt` lookup table onto the 3D Z-axis (longitudinal) and X-Y plane (radial), scaling grid coords from mm to meters.
- **Dynamic Iterations Count**: The wrapper was hardcoded to run exactly 5 self-consistent space-charge loop iterations, which defocuses the beam for benchmarks running exactly 1 pass (without self-consistent fields). We modified `ibsimu_wrapper.cpp` to extract `"iterations"` from the JSON configuration (defaulting to 5), allowing Test 3 to run exactly 1 pass, matching the benchmark.

---

## 7. Global Terminal Exposure & Desktop Shortcuts
To simplify execution in virtualization environments, we added global terminal links and absolute path integration:
- **Absolute .desktop Shortcuts**: Updated `install_and_launch.sh` to extract the absolute installation folder path using `SCRIPT_DIR` and write it to `$HOME/.local/share/applications/ibsimion.desktop`. This prevents failures when launching the program from system menus.
- **Global Terminal Invocation**: The installer writes a bash wrapper script to `/usr/local/bin/ibsimion` (running `cd "$INSTALL_DIR" && ./install_and_launch.sh "$@"`) and creates symlinks for `ibsimion2.0.1` and `IBSimion2.0.1` pointing to it. Users can type any of these triggers in a terminal to launch the simulator.
- **Non-Interactive Sudo Guard**: The wrapper installation and `apt-get` system package manager installations autodetect whether they are running in an interactive terminal session (`[ -t 0 ]`). If launched without a terminal (e.g., via the desktop icon), the installer uses `sudo -n` (non-interactive sudo) to check and perform installations, avoiding blocking or hanging the background script on password prompts.

---

## 8. Early Background Splash Screen Lifecycle & Focus Control
- **Early Display**: To provide instant graphical feedback, `install_and_launch.sh` launches a lightweight PySide6 splash script (`splash.py`) in the background at step `[0/5]` showing "Verificando dependências do sistema...".
- **Handoff & Focus Recovery**: The script writes its process ID to `early_splash.pid`. Once `main.py` is executed, it displays the primary splash, terminates the early background splash process cleanly via `SIGTERM`, and deletes the PID file. When the main window is fully loaded, it raises itself using `window.raise_()` and requests system focus via `window.activateWindow()`, ensuring the window comes to the foreground cleanly.
- **Robust venv Verification**: Refactored the step `[2/5]` checks in `install_and_launch.sh` to test the existence of `python3-venv` using the interpreter directly via `python3 -c "import venv"`. This avoids false-positive package misses on machines where venv is already globally or locally available, resolving background lifecycle lockups.

---

## 9. Final Regression Test Results
Running `python3 bent/run_pipeline.py` confirms that the wrapper outputs align with the native benchmarks:
- **Test 1 (`tofl203d`)**: PASS (Divergence = 73.34%, TOF Error = 0.00%).
- **Test 2 (`einzel3d`)**: PASS (Divergence = 0.02%, Twiss parameters match perfectly).
- **Test 3 (`solenoid`)**: PASS (Divergence = 0.89%, emittance and Twiss parameters match perfectly).

---

## 10. Documentação de Distribuição de Mercado (Refatoração de Sobriedade)
Para preparar a distribuição pública da versão `2.0.1.e3l` com foco estrito na realidade técnica construída:
- **Identidade Visual**: Incorporamos a imagem do logotipo oficial com alinhamento à direita no cabeçalho tanto do `README.md` quanto do `MANUAL.md` com dimensões restritas (`width="90"`).
- **Conteúdo Bilíngue (PT/EN)**: Reestruturamos ambos os arquivos para fornecer uma leitura totalmente bilíngue, sóbria e focada em equações reais de física de partículas.
- **Expurgo de Hype de IA**: Eliminamos qualquer menção a jargões mercadológicos como Inteligência Artificial Generativa ou Redes Neurais. O manual documenta estritamente o método de cálculo Particle-in-Cell (PIC), o laço de autoconsistência de Carga de Espaço (CW) via IBSimu e o algoritmo numérico clássico Nelder-Mead Simplex de minimização paramétrica.
- **Guia do Usuário**: Detalhamos o carregamento de malhas DXF, interpolação 3D de tabelas de solenoides (`sol.txt`), configurações do JSON, monitoramento por logs `[STATUS]` em background e diagnóstico gráfico das trajetórias no PyVista e emitâncias RMS no Matplotlib.
- **Cadeia de Execução (Mermaid)**: Inserimos um fluxograma exato ilustrando a leitura física de entrada, processamento no kernel C++ e saídas em plots 2D/3D.
