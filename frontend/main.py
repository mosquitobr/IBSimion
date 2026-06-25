# -*- coding: utf-8 -*-
# main.py
# Refactored PySide6 Application for IBSimion 2.0

import os
os.environ["QT_QPA_PLATFORM"] = "xcb"
os.environ["QT_X11_NO_MITSHM"] = "1"
import sys
import subprocess
import json
import time
import numpy as np
import matplotlib
matplotlib.use('qtagg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, 
    QHBoxLayout, QGridLayout, QLabel, QLineEdit, QSlider, QPushButton, 
    QComboBox, QFileDialog, QGroupBox, QTableWidget, QTableWidgetItem,
    QProgressBar, QMessageBox, QDoubleSpinBox, QSpinBox, QCheckBox,
    QDialog, QMenuBar, QTextEdit, QSplitter, QListWidget, QAbstractItemView
)

from pyvista_widget import PyVistaWidget

import shutil

def resolve_resource(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_path = os.path.join(script_dir, "..", filename)
    if os.path.exists(parent_path):
        return os.path.abspath(parent_path)
    grandparent_path = os.path.join(script_dir, "..", "..", filename)
    if os.path.exists(grandparent_path):
        return os.path.abspath(grandparent_path)
    return os.path.abspath(os.path.join(script_dir, "..", filename))

def resolve_path(path):
    if not path:
        return ""
    p = path.replace("\\", "/")
    if p.startswith("./data/") or p.startswith("data/") or p.startswith("../data/"):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(script_dir)
        if p.startswith("../data/"):
            normalized = p[3:]
        else:
            normalized = p.lstrip("./")
        return os.path.abspath(os.path.join(repo_root, normalized))
    if not os.path.dirname(p):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(script_dir)
        data_path = os.path.join(repo_root, "data", p)
        if os.path.exists(data_path):
            return os.path.abspath(data_path)
        backend_path = os.path.join(repo_root, "backend", p)
        if os.path.exists(backend_path):
            return os.path.abspath(backend_path)
    return os.path.abspath(path)

def get_backend_dir():
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        dist_dir = os.path.dirname(exe_dir)
        d_dir = os.path.dirname(dist_dir)
        backend_dir = os.path.join(d_dir, "backend")
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        d_dir = os.path.dirname(script_dir)
        backend_dir = os.path.join(d_dir, "backend")
    return os.path.abspath(backend_dir)

def get_dxf_layers(filepath):
    filepath = resolve_path(filepath)
    if not filepath or not os.path.exists(filepath):
        return []
    venv_python = sys.executable
    
    py_code = (
        "import ezdxf, sys, json; "
        "doc = ezdxf.readfile(sys.argv[1]); "
        "layers = {entity.dxf.layer for entity in doc.modelspace() if hasattr(entity.dxf, 'layer') and entity.dxf.layer}; "
        "print(json.dumps(sorted(list(layers))))"
    )
    try:
        res = subprocess.run(
            [venv_python, "-c", py_code, filepath],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if res.returncode == 0:
            import json
            return json.loads(res.stdout.strip())
        else:
            print(f"Subprocess error reading DXF layers: {res.stderr}")
    except Exception as e:
        print(f"Exception invoking subprocess for DXF layers: {e}")
        
    try:
        import ezdxf
        doc = ezdxf.readfile(filepath)
        layers_with_entities = set()
        for entity in doc.modelspace():
            if hasattr(entity.dxf, 'layer') and entity.dxf.layer:
                layers_with_entities.add(entity.dxf.layer)
        return sorted(list(layers_with_entities))
    except Exception as e:
        print(f"Error reading DXF layers directly: {e}")
        return []

def parse_trajectories(traj_path):
    if not os.path.exists(traj_path):
        return []
    trajectories = []
    current_traj = None
    try:
        with open(traj_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("TID"):
                    parts = line.strip().split()
                    tid = int(parts[1])
                    mass = float(parts[2])
                    charge = float(parts[3])
                    curr = float(parts[4])
                    current_traj = {
                        "id": tid, 
                        "mass": mass, 
                        "charge": charge, 
                        "curr": curr, 
                        "points": []
                    }
                    trajectories.append(current_traj)
                else:
                    parts = line.strip().split()
                    if len(parts) == 4 and current_traj is not None:
                        t, x, y, z = map(float, parts)
                        current_traj["points"].append([t, x, y, z])
    except Exception as e:
        print(f"Error parsing trajectories: {e}")
    return trajectories

def load_numpy_file_safe(filepath, is_binary=False, max_retries=5, delay=0.1):
    """Safely loads numpy files from disk under potential disk write race conditions."""
    import warnings
    if not os.path.exists(filepath):
        return None
        
    for attempt in range(max_retries):
        try:
            if os.path.exists(filepath):
                sz = os.path.getsize(filepath)
                if sz > 0:
                    with open(filepath, 'rb') as f:
                        pass
                    if is_binary:
                        data = np.fromfile(filepath, dtype=np.uint8)
                    else:
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore", UserWarning)
                            data = np.loadtxt(filepath)
                        
                    if data is not None:
                        if data.ndim == 1:
                            data = np.expand_dims(data, axis=0)
                        if data.size > 0:
                            return data
        except Exception as e:
            print(f"Attempt {attempt+1} loading {filepath} failed: {e}")
            
        time.sleep(delay)
        
    try:
        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            if is_binary:
                data = np.fromfile(filepath, dtype=np.uint8)
            else:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    data = np.loadtxt(filepath)
            if data is not None:
                if data.ndim == 1:
                    data = np.expand_dims(data, axis=0)
                if data.size > 0:
                    return data
    except Exception as e:
        print(f"Final safe load attempt for {filepath} failed: {e}")
        
    return None

def fit_multi_gaussian(bin_centers, counts):
    import scipy.signal
    import scipy.optimize
    
    mask = ~np.isnan(counts) & ~np.isnan(bin_centers)
    x = bin_centers[mask]
    y = counts[mask]
    
    if len(x) < 5:
        return None, None
        
    peaks, _ = scipy.signal.find_peaks(y, height=np.max(y)*0.05, distance=3)
    n_peaks = len(peaks)
    
    if n_peaks == 0:
        p0 = [np.max(y), x[np.argmax(y)], np.std(x)]
    else:
        p0 = []
        for pk in peaks:
            p0.extend([y[pk], x[pk], (x.max() - x.min()) / (2.0 * max(1, n_peaks))])
            
    def model(t, *params):
        res = np.zeros_like(t, dtype=float)
        for i in range(0, len(params), 3):
            A = params[i]
            mu = params[i+1]
            sigma = params[i+2]
            res += A * np.exp(-((t - mu) ** 2) / (2 * (sigma ** 2) + 1e-20))
        return res
        
    try:
        lower_bounds = []
        upper_bounds = []
        for i in range(len(p0)//3):
            lower_bounds.extend([0.0, x.min(), 1e-12])
            upper_bounds.extend([np.max(y)*10, x.max(), (x.max() - x.min())])
        
        popt, pcov = scipy.optimize.curve_fit(
            model, x, y, p0=p0, 
            bounds=(lower_bounds, upper_bounds),
            maxfev=10000
        )
        return popt, model
    except Exception as e:
        print(f"Multi-peak Gaussian fit failed: {e}. Trying single peak...")
        try:
            p0_single = [np.max(y), x[np.argmax(y)], np.std(x)]
            def single_model(t, A, mu, sigma):
                return A * np.exp(-((t - mu) ** 2) / (2 * (sigma ** 2) + 1e-20))
            popt, _ = scipy.optimize.curve_fit(single_model, x, y, p0=p0_single, maxfev=2000)
            return list(popt), lambda t, *p: single_model(t, p[0], p[1], p[2])
        except Exception:
            return None, None

def ensure_2d_grid_at_least_2x2(zs, xs, matrix, h=0.001):
    if zs is None or xs is None or matrix is None:
        return zs, xs, matrix
    
    # Copy arrays to avoid modifying cache
    zs = np.array(zs, copy=True)
    xs = np.array(xs, copy=True)
    matrix = np.array(matrix, copy=True)
    
    if len(xs) == 1:
        xs = np.array([xs[0] - h, xs[0] + h])
        matrix = np.repeat(matrix, 2, axis=0)
        
    if len(zs) == 1:
        zs = np.array([zs[0] - h, zs[0] + h])
        matrix = np.repeat(matrix, 2, axis=1)
        
    return zs, xs, matrix

TRANSLATIONS = {
    "PT": {
        "lbl_plane_orient": "Orientação do Plano:",
        "lbl_map_2d": "Tipo de Mapa 2D:",
        "sub_tab_phase": "Espaço Fásico (X vs X' & Y vs Y')",
        "sub_tab_emittance": "Histograma de Emitância RMS",
        "btn_apply_pic_suggestion": "Aplicar Sugestões PIC",
        "plane_xy": "Plano XY (Z = coord)",
        "plane_xz": "Plano XZ (Y = coord)",
        "plane_yz": "Plano YZ (X = coord)",
        "map_potential": "Potencial Elétrico",
        "map_rho": "Densidade de Carga (Rho) - Trajetórias",
        "map_j": "Densidade de Corrente (J) - Trajetórias",
        "win_title": "IBSimion v2.0.1.e3l - Core Pipeline Estável",
        "btn_theme_dark": "Modo Escuro",
        "btn_theme_light": "Modo Claro",
        "menu_file": "Arquivo",
        "action_open": "Abrir Projeto (.JSON)",
        "action_save": "Salvar Projeto (.JSON)",
        "action_exit": "Sair",
        "menu_tests": "Testes",
        "action_run_tests": "Executar Roteiro de Testes",
        "menu_help": "Ajuda",
        "action_manual": "Manual de Uso",
        "action_about": "Sobre",
        "tab_settings": "Configurações & Feixes",
        "tab_solids": "Workstation 3D & Sólidos",
        "tab_simulate": "Simular & Otimizar",
        "tab_diagnostics": "Diagnósticos Avançados",
        "mesh_box": "Arquitetura de Malhas e Mapas Magnéticos",
        "lbl_h": "Passo da Malha h (m):",
        "lbl_zmax": "Limite longitudinal Z max (m):",
        "lbl_rmax": "Limite radial R max (m):",
        "lbl_bfield": "Mapear Campo Magnético Externo (.TXT):",
        "chk_bfield": "Habilitar",
        "btn_browse": "Procurar...",
        "regime_box": "Configuração de Regime e Simulação",
        "lbl_regime": "Modo de Regime:",
        "lbl_dt": "Passo de tempo PIC dt (s):",
        "lbl_tfinal": "Tempo de simulação final T (s):",
        "beams_box": "Configuração Fina de Feixes",
        "btn_add_beam": "[+] Adicionar Feixe",
        "btn_remove_beam": "[-] Remover Selecionado",
        "btn_import_beams": "Importar Tabela de Feixes",
        "beam_editor_box": "Painel Sintético de Leitura",
        "lbl_beam_name": "Nome do Feixe:",
        "lbl_beam_particles": "Macropartículas:",
        "lbl_beam_current": "Corrente (mA):",
        "lbl_beam_mass": "Massa (u):",
        "lbl_beam_charge": "Carga (e):",
        "lbl_beam_energy": "Energia (eV):",
        "lbl_beam_emittance": "Emitância (m-rad):",
        "lbl_beam_dist": "Distribuição:",
        "lbl_beam_orig": "Origem Z, X, Y (m):",
        "lbl_beam_dir": "Direção ux, uz:",
        "btn_close_sim": "Fechar Simulação",
        "status_hold": "Estado: Espera (Pausa Ativa)",
        "solids_box": "Gerenciador de Geometrias e Sólidos",
        "btn_add_solid": "[+] Inserir Sólido (STL/DXF)",
        "btn_remove_solid": "[-] Excluir Sólido",
        "geom_editor_box": "Editor de Objeto Físico Selecionado",
        "lbl_editor_name": "Nome do Objeto:",
        "lbl_editor_file": "Caminho do Arquivo:",
        "lbl_editor_btype": "Tipo de Fronteira:",
        "lbl_editor_voltage": "Potencial Elétrico (V):",
        "lbl_editor_translation": "Offsets de Translação (m):",
        "lbl_editor_scale": "Escala (STL/DXF):",
        "lbl_editor_layer": "Camada DXF (Layer):",
        "lbl_editor_mapping": "Modo de Sólido 3D:",
        "btn_apply_edits": "Aplicar Edições",
        "lbl_view_mode": "Visualização:",
        "lbl_traj_color": "Colorir Trajetórias:",
        "btn_reload_3d": "Recarregar 3D",
        "pic_anim_box": "Controle de Animação PIC",
        "btn_play_pic": "Animar (Play)",
        "btn_pause_pic": "Pausar (Pause)",
        "lbl_pic_time": "Tempo: 0.0s",
        "actions_box": "Ações de Controle",
        "btn_start_sim": "Executar Simulação Simples",
        "btn_start_opt": "Iniciar Otimização Nelder-Mead",
        "btn_stop_opt": "Interromper Otimização",
        "opt_params_box": "Parâmetros do Otimizador",
        "lbl_opt_w_trans": "Peso Transmissão:",
        "lbl_opt_w_emit": "Peso Emitância:",
        "lbl_opt_w_tof": "Peso TOF FWHM:",
        "lbl_opt_max_iter": "Iterações Máximas:",
        "dumps_box": "Configuração de Execução e Dumps",
        "lbl_threads": "Threads Computacionais:",
        "chk_dump_potential": "Exportar Potencial Elétrico (Central Slice)",
        "chk_dump_charge": "Exportar Densidade de Carga (Central Slice)",
        "chk_dump_trajdens": "Exportar Densidade de Trajetórias",
        "chk_dump_tof": "Exportar Espectrometria TOF",
        "console_box": "Logs do Kernel de Simulação Linux",
        "diag_ctrl_box": "Configurações do Plano de Corte",
        "lbl_plane_mode": "Modo de Plano:",
        "lbl_plane_z": "Coordenada Z do Plano (m):",
        "btn_update_diagnostics": "Atualizar Diagnósticos",
        "btn_clip_plane": "Configurar Plano de Corte",
        "tof_opt_box": "Estilo & Exportação TOF",
        "lbl_tof_style": "Estilo Histograma:",
        "btn_export_tof": "Exportar Dados TOF (.TXT)",
        "metrics_box": "Métricas Científicas",
        "metric_transmission": "Transmissão (%)",
        "metric_emittance": "Emitância RMS X (m·rad)",
        "metric_tof": "FWHM do Tempo de Voo (ns)",
        "sub_tab_tof": "Espectro de Tempo de Voo (TOF)",
        "sub_tab_profile": "Perfil Transversal de Corte (X vs Y)",
        "sub_tab_contours": "Mapa de Campo 2D & Equipotenciais",
        "status_ready": "Pronto.",
        "about_title": "Sobre o IBSimion",
        "dxf_mapping_rotz": "Rotação Simétrica (Eixo Z)",
        "dxf_mapping_linear": "Extrusão Planar Linear",
        "view_persp": "3D Perspectiva",
        "view_zx": "Plano ZX (2D)",
        "view_zy": "Plano ZY (2D)",
        "view_xy": "Plano XY (2D)",
        "color_species": "Espécie",
        "color_mass": "Massa",
        "color_charge": "Carga",
        "color_energy": "Energia (Z-Grad)",
        "color_current": "Corrente",
        "plane_auto": "Automático (Detector)",
        "plane_arbitrary": "Arbitrário",
        "style_bars": "Barras Preenchidas",
        "style_line": "Linha Suavizada",
        "style_scatter": "Dispersão com Tendência",
        "beam_headers": [
            "Nome", "Partículas", "Corrente (mA)", "Massa (u)", "Carga (e)", "Energia (eV)", "Emit. (m-rad)", "Distrib.",
            "Orig. Z (m)", "Orig. X (m)", "Orig. Y (m)", "Dir. X (ux)", "Dir. Z (uz)"
        ],
        "geom_headers": ["Nome", "Arquivo", "Tipo", "Modo Sólido", "Potencial (V)", "Z-Offset (m)"],
        "metric_headers": ["Métrica", "Valor"],
        "tooltip_h": "Tamanho da célula cúbica do grid em metros.",
        "tooltip_zmax": "Comprimento longitudinal total do grid de simulação.",
        "tooltip_rmax": "Limite do raio transversal da malha cilíndrica.",
        "tooltip_bfield": "Selecione se deseja importar mapa magnético externo customizado.",
        "tooltip_regime": "Contínuo (CW) ou Simulação de Carga Espacial Temporal (PIC).",
        "tooltip_dt": "Passo de integração temporal para simulação de partículas PIC.",
        "tooltip_tfinal": "Tempo total de simulação para as partículas cruzarem o domínio.",
        "status_canceling": "Cancelando...",
        "status_test_success": "Roteiro de testes: SUCESSO",
        "status_test_fail": "Roteiro de testes: FALHA",
        "status_sim_error": "Erro na simulação física. Verifique os logs.",
        "status_optimizing": "Otimizando... Iteração",
        "status_opt_finished": "Otimização concluída!",
        "status_saved": "Projeto salvo em:",
        "status_clipped": "Plano de corte aplicado em Z =",
        "status_loaded": "Projeto carregado:",
        "open_title": "Abrir Projeto IBSimion",
        "save_title": "Salvar Projeto IBSimion",
        "save_success_title": "Projeto Salvo",
        "save_success_msg": "O projeto foi salvo com sucesso em:\n{}",
        "save_error_title": "Erro ao Salvar",
        "save_error_msg": "Não foi possível salvar o projeto:\n{}",
        "load_success_title": "Projeto Carregado",
        "load_success_msg": "O projeto foi carregado com sucesso de:\n{}",
        "load_error_title": "Erro ao Abrir",
        "load_error_msg": "Não foi possível carregar o projeto:\n{}",
        "plot_tof_title": "Espectro de Tempo de Voo (TOF)",
        "plot_tof_xlabel": "Tempo de Voo (µs)",
        "plot_tof_ylabel": "Contagem de Íons",
        "plot_profile_title": "Corte Transversal do Feixe no Detector",
        "plot_profile_xlabel": "Deflexão X (mm)",
        "plot_profile_ylabel": "Deflexão Y (mm)",
        "plot_contours_title": "Equipotenciais (V) e Densidade de Carga (pcolormesh)",
        "plot_contours_xlabel": "Posição Longitudinal Z (mm)",
        "plot_contours_ylabel": "Posição Transversal X (mm)",
        "plot_convergence_title": "Convergência do Otimizador",
        "plot_convergence_xlabel": "Iteração",
        "plot_convergence_ylabel": "Loss",
        "plot_loss_label": "Perda",
        "trend_label": "Tendência (Grau 3)",
        "bins_label": "Bins",
        "cbar_traj_density": "Densidade de Corrente (A/m²)",
        "cbar_potential": "Potencial (V)",
        "cbar_magnetic": "Campo Magnético (T)"
    },
    "EN": {
        "lbl_plane_orient": "Plane Orientation:",
        "lbl_map_2d": "2D Map Type:",
        "sub_tab_phase": "Phase Space (X vs X' & Y vs Y')",
        "sub_tab_emittance": "RMS Emittance Histogram",
        "btn_apply_pic_suggestion": "Apply PIC Suggestions",
        "plane_xy": "XY Plane (Z = coord)",
        "plane_xz": "XZ Plane (Y = coord)",
        "plane_yz": "YZ Plane (X = coord)",
        "map_potential": "Electric Potential",
        "map_rho": "Charge Density (Rho) - Trajectories",
        "map_j": "Current Density (J) - Trajectories",
        "win_title": "IBSimion v2.0.1.e3l - Core Pipeline Stable",
        "btn_theme_dark": "Dark Mode",
        "btn_theme_light": "Light Mode",
        "menu_file": "File",
        "action_open": "Open Project (.JSON)",
        "action_save": "Save Project (.JSON)",
        "action_exit": "Exit",
        "menu_tests": "Tests",
        "action_run_tests": "Run Test Suite",
        "menu_help": "Help",
        "action_manual": "User Manual",
        "action_about": "About",
        "tab_settings": "Settings & Beams",
        "tab_solids": "3D Workstation & Solids",
        "tab_simulate": "Simulate & Optimize",
        "tab_diagnostics": "Advanced Diagnostics",
        "mesh_box": "Mesh Architecture & Magnetic Maps",
        "lbl_h": "Mesh Step h (m):",
        "lbl_zmax": "Longitudinal Limit Z max (m):",
        "lbl_rmax": "Radial Limit R max (m):",
        "lbl_bfield": "Map External Magnetic Field (.TXT):",
        "chk_bfield": "Enable",
        "btn_browse": "Browse...",
        "regime_box": "Regime & Simulation Configuration",
        "lbl_regime": "Regime Mode:",
        "lbl_dt": "PIC time step dt (s):",
        "lbl_tfinal": "Final simulation time T (s):",
        "beams_box": "Fine Beam Configuration",
        "btn_add_beam": "[+] Add Beam",
        "btn_remove_beam": "[-] Remove Selected",
        "btn_import_beams": "Import Beams Table",
        "beam_editor_box": "Summary View",
        "lbl_beam_name": "Beam Name:",
        "lbl_beam_particles": "Macroparticles:",
        "lbl_beam_current": "Current (mA):",
        "lbl_beam_mass": "Mass (u):",
        "lbl_beam_charge": "Charge (e):",
        "lbl_beam_energy": "Energy (eV):",
        "lbl_beam_emittance": "Emittance (m-rad):",
        "lbl_beam_dist": "Distribution:",
        "lbl_beam_orig": "Origin Z, X, Y (m):",
        "lbl_beam_dir": "Direction ux, uz:",
        "btn_close_sim": "Close Simulation",
        "status_hold": "Status: Hold (Active Pause)",
        "solids_box": "Geometries and Solids Manager",
        "btn_add_solid": "[+] Insert Solid (STL/DXF)",
        "btn_remove_solid": "[-] Delete Solid",
        "geom_editor_box": "Selected Physical Object Editor",
        "lbl_editor_name": "Object Name:",
        "lbl_editor_file": "File Path:",
        "lbl_editor_btype": "Boundary Type:",
        "lbl_editor_voltage": "Electric Potential (V):",
        "lbl_editor_translation": "Translation Offsets (m):",
        "lbl_editor_scale": "Scale (STL/DXF):",
        "lbl_editor_layer": "DXF Layer:",
        "lbl_editor_mapping": "3D Solid Mode:",
        "btn_apply_edits": "Apply Edits",
        "lbl_view_mode": "View Mode:",
        "lbl_traj_color": "Color Trajectories:",
        "btn_reload_3d": "Reload 3D",
        "pic_anim_box": "PIC Animation Control",
        "btn_play_pic": "Play",
        "btn_pause_pic": "Pause",
        "lbl_pic_time": "Time: 0.0s",
        "actions_box": "Control Actions",
        "btn_start_sim": "Run Simple Simulation",
        "btn_start_opt": "Start Nelder-Mead Optimization",
        "btn_stop_opt": "Terminate Optimization",
        "opt_params_box": "Optimizer Parameters",
        "lbl_opt_w_trans": "Transmission Weight:",
        "lbl_opt_w_emit": "Emittance Weight:",
        "lbl_opt_w_tof": "TOF FWHM Weight:",
        "lbl_opt_max_iter": "Maximum Iterations:",
        "dumps_box": "Execution Settings & Dumps",
        "lbl_threads": "Computational Threads:",
        "chk_dump_potential": "Export Electric Potential (Central Slice)",
        "chk_dump_charge": "Export Charge Density (Central Slice)",
        "chk_dump_trajdens": "Export Trajectory Density",
        "chk_dump_tof": "Export TOF Spectrometry",
        "console_box": "Linux Simulation Kernel Logs",
        "diag_ctrl_box": "Clipping Plane Settings",
        "lbl_plane_mode": "Plane Mode:",
        "lbl_plane_z": "Plane Z Coordinate (m):",
        "btn_update_diagnostics": "Update Diagnostics",
        "btn_clip_plane": "Configure Clipping Plane",
        "tof_opt_box": "TOF Style & Export",
        "lbl_tof_style": "Histogram Style:",
        "btn_export_tof": "Export TOF Data (.TXT)",
        "metrics_box": "Scientific Metrics",
        "metric_transmission": "Transmission (%)",
        "metric_emittance": "RMS Emittance X (m·rad)",
        "metric_tof": "Time of Flight FWHM (ns)",
        "sub_tab_tof": "Time of Flight Spectrum (TOF)",
        "sub_tab_profile": "Transverse Cut Profile (X vs Y)",
        "sub_tab_contours": "2D Field Map & Equipotentials",
        "status_ready": "Ready.",
        "about_title": "About IBSimion",
        "dxf_mapping_rotz": "Symmetric Rotation (Z-Axis)",
        "dxf_mapping_linear": "Linear Planar Extrusion",
        "view_persp": "3D Perspective",
        "view_zx": "ZX Plane (2D)",
        "view_zy": "ZY Plane (2D)",
        "view_xy": "XY Plane (2D)",
        "color_species": "Species",
        "color_mass": "Mass",
        "color_charge": "Charge",
        "color_energy": "Energy (Z-Grad)",
        "color_current": "Current",
        "plane_auto": "Automatic (Detector)",
        "plane_arbitrary": "Arbitrary",
        "style_bars": "Filled Bars",
        "style_line": "Smoothed Line",
        "style_scatter": "Scatter with Trend",
        "beam_headers": [
            "Name", "Particles", "Current (mA)", "Mass (u)", "Charge (e)", "Energy (eV)", "Emit. (m-rad)", "Distrib.",
            "Orig. Z (m)", "Orig. X (m)", "Orig. Y (m)", "Dir. X (ux)", "Dir. Z (uz)"
        ],
        "geom_headers": ["Name", "File", "Type", "Solid Mode", "Potential (V)", "Z-Offset (m)"],
        "metric_headers": ["Metric", "Value"],
        "tooltip_h": "Mesh step cubic cell size in meters.",
        "tooltip_zmax": "Total longitudinal limit size of the simulation domain.",
        "tooltip_rmax": "Transverse radius limit of the cylindrical mesh.",
        "tooltip_bfield": "Select to map and interpolate custom external axisymmetric magnetic field.",
        "tooltip_regime": "Continuous (CW) or Time-resolved Space Charge simulation (PIC).",
        "tooltip_dt": "PIC time step for particle pushing integration.",
        "tooltip_tfinal": "Final simulation time for the particles to cross the domain.",
        "status_canceling": "Canceling...",
        "status_test_success": "Test suite: SUCCESS",
        "status_test_fail": "Test suite: FAILED",
        "status_sim_error": "Error in physical simulation. Check logs.",
        "status_optimizing": "Optimizing... Iteration",
        "status_opt_finished": "Optimization completed!",
        "status_saved": "Project saved to:",
        "status_clipped": "Clipping plane applied at Z =",
        "status_loaded": "Project loaded:",
        "open_title": "Open IBSimion Project",
        "save_title": "Save IBSimion Project",
        "save_success_title": "Project Saved",
        "save_success_msg": "The project was saved successfully to:\n{}",
        "save_error_title": "Error Saving",
        "save_error_msg": "Could not save the project:\n{}",
        "load_success_title": "Project Loaded",
        "load_success_msg": "Project loaded successfully from:\n{}",
        "load_error_title": "Error Opening",
        "load_error_msg": "Could not load project:\n{}",
        "plot_tof_title": "Time of Flight Spectrum (TOF)",
        "plot_tof_xlabel": "Time of Flight (µs)",
        "plot_tof_ylabel": "Ion Count",
        "plot_profile_title": "Transverse Beam Cut at Detector",
        "plot_profile_xlabel": "X Deflection (mm)",
        "plot_profile_ylabel": "Y Deflection (mm)",
        "plot_contours_title": "Equipotentials (V) & Charge Density (pcolormesh)",
        "plot_contours_xlabel": "Longitudinal Position Z (mm)",
        "plot_contours_ylabel": "Transverse Position X (mm)",
        "plot_convergence_title": "Optimizer Convergence",
        "plot_convergence_xlabel": "Iteration",
        "plot_convergence_ylabel": "Loss",
        "plot_loss_label": "Loss",
        "trend_label": "Trend (Degree 3)",
        "bins_label": "Bins",
        "cbar_traj_density": "Current Density (A/m²)",
        "cbar_potential": "Potential (V)",
        "cbar_magnetic": "Magnetic Field (T)"
    }
}

class HelpDialog(QDialog):
    def __init__(self, parent=None, language="PT"):
        super().__init__(parent)
        self.language = language
        self.setWindowTitle("Manual de Uso e Fundamentos Físicos - IBSimion 2.0" if self.language == "PT" else "User Manual & Physical Foundations - IBSimion 2.0")
        self.resize(1000, 700)
        self.setStyleSheet("""
            QDialog {
                background-color: #0B0F19;
            }
            QListWidget {
                background-color: #111827;
                color: #F3F4F6;
                border: 1px solid #1F2937;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #1F2937;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: #1F2937;
                color: #3B82F6;
            }
            QListWidget::item:selected {
                background-color: #3B82F6;
                color: #ffffff;
                font-weight: bold;
            }
            QTextEdit {
                background-color: #111827;
                color: #F3F4F6;
                border: 1px solid #1F2937;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
                padding: 15px;
            }
            QPushButton {
                background-color: #1E293B;
                border: 1px solid #374151;
                border-radius: 4px;
                color: #F3F4F6;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1F2937;
                border: 1px solid #3B82F6;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        
        splitter = QSplitter(Qt.Horizontal)
        
        self.topic_list = QListWidget()
        if self.language == "PT":
            topics = [
                "Parâmetros de Malhas",
                "Configuração de Feixes",
                "Gerenciador de Geometrias",
                "Otimizador Nelder-Mead",
                "Paralelismo & Dumps"
            ]
        else:
            topics = [
                "Mesh Parameters",
                "Beam Configuration",
                "Geometry Manager",
                "Nelder-Mead Optimizer",
                "Parallelism & Dumps"
            ]
        self.topic_list.addItems(topics)
        splitter.addWidget(self.topic_list)
        
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        splitter.addWidget(self.text_area)
        
        splitter.setSizes([250, 750])
        main_layout.addWidget(splitter)
        
        btn_layout = QHBoxLayout()
        btn_close = QPushButton("Fechar" if self.language == "PT" else "Close")
        btn_close.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        main_layout.addLayout(btn_layout)
        
        if self.language == "PT":
            self.manual_chapters = {
                "Parâmetros de Malhas": """
                    <h1 style='color: #3B82F6; border-bottom: 2px solid #3B82F6; padding-bottom: 5px;'>Parâmetros de Malhas e Mapas Magnéticos</h1>
                    <p>Nesta seção, você configura o grid discreto tridimensional no qual a simulação física do IBSimu resolve a Equação de Poisson.</p>
                    <ul>
                        <li><b>Passo da Malha h (m):</b> O tamanho da célula cúbica do grid em metros. Valores menores (ex: 0.0005 m) aumentam a resolução geométrica e a precisão do campo elétrico, mas aumentam quadraticamente o consumo de memória e o tempo de simulação.</li>
                        <li><b>Limite Longitudinal Z max (m):</b> O comprimento total do domínio de simulação ao longo do eixo Z. Geralmente termina na face do detector.</li>
                        <li><b>Limite Radial R max (m):</b> O raio do domínio cilíndrico de simulação (mapeado de -R_max a +R_max nos eixos X e Y).</li>
                        <li><b>Campo Magnético Externo:</b> Se habilitado, carrega um mapa de campo magnético axissimétrico a partir de um arquivo de texto. O arquivo deve conter colunas de dados organizadas em <i>Z (m), R (m), Bz (T), Br (T)</i>. O resolvedor realiza interpolação bilinear contínua desses pontos durante o rastreamento das partículas.</li>
                    </ul>
                """,
                "Configuração de Feixes": """
                    <h1 style='color: #3B82F6; border-bottom: 2px solid #3B82F6; padding-bottom: 5px;'>Configuração de Feixes de Partículas</h1>
                    <p>O painel de feixes permite a definição de múltiplas populações de partículas carregadas a serem injetadas simultaneamente no sistema.</p>
                    <ul>
                        <li><b>Partículas:</b> Quantidade de macropartículas simuladas para representar o feixe. Valores maiores (ex: 5000 a 10000) melhoram a estatística da carga espacial e a resolução do espectro de tempo de voo.</li>
                        <li><b>Corrente (mA):</b> A corrente total do feixe em miliamperes. O resolvedor de carga espacial utiliza essa corrente para calcular a densidade de carga espacial de acordo com a velocidade das partículas.</li>
                        <li><b>Massa (u):</b> A massa das partículas em unidades de massa atômica unificada (u) (ex: próton = 1.0 u, elétron = 5.4e-4 u, íon de Xenônio = 136.2 u).</li>
                        <li><b>Carga (e):</b> O estado de carga elementar da partícula (ex: +1.0 para íons mono-carregados, -1.0 para elétrons).</li>
                        <li><b>Energia (eV):</b> Energia cinética longitudinal inicial das partículas na injeção.</li>
                        <li><b>Emitância RMS (m·rad):</b> Medida do volume ocupado pelo feixe no espaço de fase transversal. Define a dispersão angular de velocidade transversal.</li>
                        <li><b>Distribuição:</b> Tipo de amostragem no espaço transversal (Uniforme ou Gaussiana).</li>
                    </ul>
                """,
                "Gerenciador de Geometrias": """
                    <h1 style='color: #3B82F6; border-bottom: 2px solid #3B82F6; padding-bottom: 5px;'>Gerenciador de Geometrias e Sólidos</h1>
                    <p>A Workstation 3D suporta a importação flexível e dinâmica de múltiplos eletrodos definidos via arquivos CAD 3D.</p>
                    <ul>
                        <li><b>Arquivos STL (.stl):</b> Representam volumes discretos fechados. Cada STL importado é tratado como um único eletrodo sólido contínuo.</li>
                        <li><b>Arquivos DXF (.dxf):</b> Ao selecionar um arquivo DXF, o frontend lê dinamicamente as camadas (layers) existentes no arquivo. Você deve associar o objeto a uma camada específica para que o IBSimu extraia apenas os perfis contidos nela.</li>
                        <li><b>Potencial Elétrico (V):</b> A tensão em Volts aplicada ao eletrodo (relevante apenas para a condição de fronteira de Dirichlet).</li>
                        <li><b>Condições de Fronteira:</b>
                            <ul>
                                <li><b>Dirichlet:</b> O potencial é mantido constante na superfície do metal.</li>
                                <li><b>Neumann:</b> O gradiente normal do potencial elétrico é zero (superfície isolante).</li>
                            </ul>
                        </li>
                        <li><b>Offsets de Translação:</b> Permite mover o objeto nos eixos X, Y e Z sem alterar o arquivo original do modelo CAD.</li>
                        <li><b>Escala:</b> Fator multiplicativo para converter as coordenadas do arquivo CAD para metros (ex: 0.001 se o arquivo CAD foi desenhado em milímetros).</li>
                    </ul>
                """,
                "Otimizador Nelder-Mead": """
                    <h1 style='color: #3B82F6; border-bottom: 2px solid #3B82F6; padding-bottom: 5px;'>Otimizador Nelder-Mead de Tensões</h1>
                    <p>O IBSimion possui um módulo de otimização em malha fechada baseado no algoritmo Simplex de Nelder-Mead para encontrar as tensões ideais de foco e resolução temporal.</p>
                    <ul>
                        <li><b>Processo de Otimização:</b> O algoritmo ajusta iterativamente as tensões de todos os eletrodos Dirichlet. A cada passo, executa a simulação física nativamente, lê o arquivo de saída <code>tof.txt</code> e calcula a Função de Perda (Loss).</li>
                        <li><b>Função de Perda Multi-Objetivo:</b>
                            <div style='background-color: #1F2937; border-left: 4px solid #10B981; padding: 10px; margin: 10px 0; font-family: monospace;'>
                                Loss = - (w_trans &times; Transmissão) + (w_emit &times; Emitância RMS &times; 10<sup>6</sup>) + (w_tof &times; FWHM TOF &times; 10<sup>9</sup>)
                            </div>
                        </li>
                        <li><b>Métricas Configuráveis:</b>
                            <ul>
                                <li><b>Peso Transmissão:</b> Penaliza a perda de partículas por colisão.</li>
                                <li><b>Peso Emitância:</b> Incentiva a colimação transversal do feixe.</li>
                                <li><b>Peso TOF FWHM:</b> Reduz a dispersão temporal, ideal para maximizar a resolução de espectrômetros de tempo de voo.</li>
                            </ul>
                        </li>
                    </ul>
                """,
                "Paralelismo & Dumps": """
                    <h1 style='color: #3B82F6; border-bottom: 2px solid #3B82F6; padding-bottom: 5px;'>Paralelismo Computacional e Exportação</h1>
                    <p>Configurações finas do motor de execução paralela do IBSimu e dos dumps de diagnóstico para economia de disco e processamento.</p>
                    <ul>
                        <li><b>Threads Computacionais:</b> O resolvedor do IBSimu no backend utiliza paralelismo baseado em multi-threading OpenMP para acelerar a resolução da malha de Poisson e o rastreamento das partículas. Por padrão, a interface detecta o total de núcleos lógicos e pré-configura a utilização de 70% da capacidade da CPU.</li>
                        <li><b>Exportar Potencial Elétrico:</b> Salva o campo bidimensional de potencial elétrico e campo elétrico (no plano central Y &approx; 0) no arquivo <code>potential_field.dat</code>.</li>
                        <li><b>Exportar Densidade de Carga:</b> Salva a distribuição da carga espacial das partículas no plano Y &approx; 0 no arquivo <code>charge_density.dat</code>.</li>
                        <li><b>Exportar Densidade de Trajetórias:</b> Reconstrói a malha contínua tridimensional de densidade de trajeto das partículas no arquivo <code>trajectory_density.dat</code>.</li>
                        <li><b>Exportar Espectrometria TOF:</b> Salva os dados de tempo de voo brutos e o histograma processado. Desativar economiza tempo de E/S quando não for necessário.</li>
                    </ul>
                """
            }
        else:
            self.manual_chapters = {
                "Mesh Parameters": """
                    <h1 style='color: #3B82F6; border-bottom: 2px solid #3B82F6; padding-bottom: 5px;'>Mesh Parameters & Magnetic Maps</h1>
                    <p>In this section, you configure the three-dimensional discrete grid where IBSimu solves Poisson's Equation.</p>
                    <ul>
                        <li><b>Mesh Step h (m):</b> The size of each cubic grid cell in meters. Smaller values (e.g., 0.0005 m) increase geometric resolution and electric field precision but quadratically increase memory consumption and simulation time.</li>
                        <li><b>Longitudinal Limit Z max (m):</b> The total length of the simulation domain along the Z axis. It usually ends at the detector plane.</li>
                        <li><b>Radial Limit R max (m):</b> The radius of the cylindrical simulation domain (mapped from -R_max to +R_max on X and Y axes).</li>
                        <li><b>External Magnetic Field:</b> If enabled, loads an axisymmetric magnetic field map from a text file. The file must contain columns formatted as <i>Z (m), R (m), Bz (T), Br (T)</i>. The solver performs continuous bilinear interpolation during particle tracking.</li>
                    </ul>
                """,
                "Beam Configuration": """
                    <h1 style='color: #3B82F6; border-bottom: 2px solid #3B82F6; padding-bottom: 5px;'>Particle Beams Configuration</h1>
                    <p>The beams panel allows defining multiple charged particle populations to be injected simultaneously.</p>
                    <ul>
                        <li><b>Particles:</b> Quantity of macroparticles simulated to represent the beam. Higher values (e.g., 5000 to 10000) improve space charge statistics and time of flight spectrum resolution.</li>
                        <li><b>Current (mA):</b> Total beam current in milliamperes. The solver uses this to compute space charge density based on particle velocities.</li>
                        <li><b>Mass (u):</b> Particle mass in unified atomic mass units (u) (e.g., proton = 1.0 u, electron = 5.4e-4 u, Xenon ion = 136.2 u).</li>
                        <li><b>Charge (e):</b> Elementary charge state of the particle (e.g., +1.0 for singly charged ions, -1.0 for electrons).</li>
                        <li><b>Energy (eV):</b> Initial longitudinal kinetic energy of particles at injection.</li>
                        <li><b>RMS Emittance (m·rad):</b> A measure of the volume occupied by the beam in the transverse phase space. Defines transverse velocity angular spread.</li>
                        <li><b>Distribution:</b> Type of sampling in transverse space (Uniform or Gaussian).</li>
                    </ul>
                """,
                "Geometry Manager": """
                    <h1 style='color: #3B82F6; border-bottom: 2px solid #3B82F6; padding-bottom: 5px;'>Geometries and Solids Manager</h1>
                    <p>The 3D Workstation supports importing multiple electrodes defined via 3D CAD files.</p>
                    <ul>
                        <li><b>STL Files (.stl):</b> Represent closed discrete volumes. Each imported STL is treated as a single continuous solid electrode.</li>
                        <li><b>DXF Files (.dxf):</b> When selecting a DXF file, the frontend dynamically reads the existing layers. You must associate the object with a specific layer for IBSimu to extract only the profiles in that layer.</li>
                        <li><b>Electric Potential (V):</b> Voltage in Volts applied to the electrode (only relevant for Dirichlet boundary conditions).</li>
                        <li><b>Boundary Conditions:</b>
                            <ul>
                                <li><b>Dirichlet:</b> Potential is kept constant on the metal surface.</li>
                                <li><b>Neumann:</b> The normal gradient of the electric potential is zero (insulating surface).</li>
                            </ul>
                        </li>
                        <li><b>Translation Offsets:</b> Translate the object along X, Y, and Z axes without modifying the original CAD model.</li>
                        <li><b>Scale:</b> Multiplicative factor to convert CAD coordinates to meters (e.g., 0.001 if drawing was designed in millimeters).</li>
                    </ul>
                """,
                "Nelder-Mead Optimizer": """
                    <h1 style='color: #3B82F6; border-bottom: 2px solid #3B82F6; padding-bottom: 5px;'>Nelder-Mead Voltage Optimizer</h1>
                    <p>IBSimion features a closed-loop optimization module based on the Nelder-Mead Simplex algorithm to find optimal voltages for focusing and temporal resolution.</p>
                    <ul>
                        <li><b>Optimization Process:</b> The algorithm iteratively adjusts the voltages of all Dirichlet electrodes. At each step, it runs the physical simulation natively, reads the <code>tof.txt</code> output, and calculates the Loss function.</li>
                        <li><b>Multi-Objective Loss Function:</b>
                            <div style='background-color: #1F2937; border-left: 4px solid #10B981; padding: 10px; margin: 10px 0; font-family: monospace;'>
                                Loss = - (w_trans &times; Transmission) + (w_emit &times; RMS Emittance &times; 10<sup>6</sup>) + (w_tof &times; TOF FWHM &times; 10<sup>9</sup>)
                            </div>
                        </li>
                        <li><b>Configurable Weights:</b>
                            <ul>
                                <li><b>Transmission Weight:</b> Penalizes particle loss due to collisions.</li>
                                <li><b>Emittance Weight:</b> Promotes beam transverse collimation.</li>
                                <li><b>TOF FWHM Weight:</b> Minimizes temporal spread, ideal for maximizing time-of-flight spectrometer resolution.</li>
                            </ul>
                        </li>
                    </ul>
                """,
                "Parallelism & Dumps": """
                    <h1 style='color: #3B82F6; border-bottom: 2px solid #3B82F6; padding-bottom: 5px;'>Computational Parallelism & Export</h1>
                    <p>Fine-tuning settings for the IBSimu parallel execution engine and diagnostics dumps for disk space and processing efficiency.</p>
                    <ul>
                        <li><b>Computational Threads:</b> The IBSimu backend solver utilizes OpenMP multi-threading to speed up Poisson solving and particle tracking. By default, the UI detects logical cores and sets usage to 70% CPU capacity.</li>
                        <li><b>Export Electric Potential:</b> Saves the 2D electric potential and field slice (at central plane Y &approx; 0) to <code>potential_field.dat</code>.</li>
                        <li><b>Export Charge Density:</b> Saves the particle space charge distribution at central plane Y &approx; 0 to <code>charge_density.dat</code>.</li>
                        <li><b>Export Trajectory Density:</b> Reconstructs the 3D continuous trajectory density mesh in <code>trajectory_density.dat</code>.</li>
                        <li><b>Export TOF Spectrometry:</b> Saves raw time-of-flight data and processed histogram. Disabling it saves I/O time.</li>
                    </ul>
                """
            }
        
        self.topic_list.currentRowChanged.connect(self.display_topic)
        self.topic_list.setCurrentRow(0)
        
    def display_topic(self, row):
        item = self.topic_list.item(row)
        if item:
            topic = item.text()
            self.text_area.setHtml(self.manual_chapters.get(topic, ""))

# Premium Obsidian Dark QSS Style Sheet
STYLESHEET = """
QMainWindow {
    background-color: #0B0F19;
}
QDialog {
    background-color: #111827;
    color: #F3F4F6;
}
QDialog QLabel {
    color: #F3F4F6;
}
QTabWidget::pane {
    border: 1px solid #1F2937;
    background-color: #111827;
    border-radius: 6px;
}
QTabBar::tab {
    background-color: #111827;
    color: #9CA3AF;
    padding: 10px 20px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
    border: 1px solid #1F2937;
    border-bottom: none;
}
QTabBar::tab:hover {
    background-color: #1F2937;
    color: #F3F4F6;
}
QTabBar::tab:selected {
    background-color: #3B82F6;
    color: #ffffff;
    font-weight: bold;
    border: 1px solid #3B82F6;
}
QGroupBox {
    border: 1px solid #1F2937;
    border-radius: 6px;
    margin-top: 15px;
    font-weight: bold;
    color: #3B82F6;
    padding-top: 15px;
    background-color: #111827;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    left: 10px;
}
QLabel {
    color: #F3F4F6;
    font-size: 11px;
}
QLineEdit, QDoubleSpinBox, QSpinBox {
    background-color: #1F2937;
    border: 1px solid #2D3748;
    border-radius: 4px;
    color: #F3F4F6;
    padding: 4px;
}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {
    border: 1px solid #3B82F6;
}
QSlider::groove:horizontal {
    border: 1px solid #1F2937;
    height: 8px;
    background: #1F2937;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #3B82F6;
    border: 1px solid #3B82F6;
    width: 14px;
    margin: -3px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #60A5FA;
}
QPushButton {
    background-color: #1E293B;
    border: 1px solid #374151;
    border-radius: 4px;
    color: #F3F4F6;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #1F2937;
    border: 1px solid #3B82F6;
    color: #F3F4F6;
}
QPushButton:pressed {
    background-color: #3B82F6;
    color: #ffffff;
}
QPushButton:disabled {
    background-color: #111827;
    color: #4B5563;
    border: 1px solid #1F2937;
}
QPushButton#btn_run {
    background-color: #10B981;
    border: 1px solid #10B981;
    color: #ffffff;
}
QPushButton#btn_run:hover {
    background-color: #34D399;
}
QPushButton#btn_opt {
    background-color: #3B82F6;
    border: 1px solid #3B82F6;
    color: #ffffff;
}
QPushButton#btn_opt:hover {
    background-color: #60A5FA;
}
QPushButton#btn_run_tests {
    background-color: #6366F1;
    border: 1px solid #6366F1;
    color: #ffffff;
}
QPushButton#btn_run_tests:hover {
    background-color: #818CF8;
}
QTableWidget {
    background-color: #111827;
    gridline-color: #1F2937;
    color: #F3F4F6;
    border: 1px solid #1F2937;
}
QHeaderView::section {
    background-color: #1F2937;
    color: #F3F4F6;
    padding: 5px;
    border: 1px solid #111827;
}
QProgressBar {
    border: 1px solid #1F2937;
    border-radius: 4px;
    text-align: center;
    background-color: #1F2937;
    color: #ffffff;
}
QProgressBar::chunk {
    background-color: #3B82F6;
}
QComboBox {
    background-color: #1F2937;
    border: 1px solid #2D3748;
    border-radius: 4px;
    color: #F3F4F6;
    padding: 4px;
}
QComboBox:disabled {
    background-color: #1F2937;
    color: #4B5563;
    border: 1px solid #1F2937;
}
QComboBox QAbstractItemView {
    background-color: #111827;
    color: #F3F4F6;
    selection-background-color: #1F2937;
    selection-color: #3B82F6;
    border: 1px solid #1F2937;
}
QMenuBar {
    background-color: #111827;
    color: #F3F4F6;
    border-bottom: 1px solid #1F2937;
}
QMenuBar::item {
    background-color: transparent;
    padding: 6px 12px;
}
QMenuBar::item:selected {
    background-color: #1F2937;
    color: #3B82F6;
}
QMenu {
    background-color: #111827;
    color: #F3F4F6;
    border: 1px solid #1F2937;
}
QMenu::item {
    padding: 6px 24px;
}
QMenu::item:selected {
    background-color: #1F2937;
    color: #3B82F6;
}
"""

STYLESHEET_LIGHT = """
QMainWindow {
    background-color: #F3F4F6;
}
QDialog {
    background-color: #FFFFFF;
    color: #111827;
}
QDialog QLabel {
    color: #111827;
}
QTabWidget::pane {
    border: 1px solid #D1D5DB;
    background-color: #FFFFFF;
    border-radius: 6px;
}
QTabBar::tab {
    background-color: #E5E7EB;
    color: #374151;
    padding: 10px 20px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
    border: 1px solid #D1D5DB;
    border-bottom: none;
}
QTabBar::tab:hover {
    background-color: #D1D5DB;
    color: #111827;
}
QTabBar::tab:selected {
    background-color: #2563EB;
    color: #ffffff;
    font-weight: bold;
    border: 1px solid #2563EB;
}
QGroupBox {
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    margin-top: 15px;
    font-weight: bold;
    color: #2563EB;
    padding-top: 15px;
    background-color: #FFFFFF;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    left: 10px;
}
QLabel {
    color: #111827;
    font-size: 11px;
}
QLineEdit, QDoubleSpinBox, QSpinBox {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    color: #111827;
    padding: 4px;
}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {
    border: 1px solid #2563EB;
}
QSlider::groove:horizontal {
    border: 1px solid #D1D5DB;
    height: 8px;
    background: #E5E7EB;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #2563EB;
    border: 1px solid #2563EB;
    width: 14px;
    margin: -3px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #3B82F6;
}
QPushButton {
    background-color: #F3F4F6;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    color: #111827;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #E5E7EB;
    border: 1px solid #2563EB;
    color: #111827;
}
QPushButton:pressed {
    background-color: #2563EB;
    color: #ffffff;
}
QPushButton:disabled {
    background-color: #F9FAFB;
    color: #9CA3AF;
    border: 1px solid #E5E7EB;
}
QPushButton#btn_run {
    background-color: #10B981;
    border: 1px solid #10B981;
    color: #ffffff;
}
QPushButton#btn_run:hover {
    background-color: #059669;
}
QPushButton#btn_opt {
    background-color: #2563EB;
    border: 1px solid #2563EB;
    color: #ffffff;
}
QPushButton#btn_opt:hover {
    background-color: #1D4ED8;
}
QPushButton#btn_run_tests {
    background-color: #4F46E5;
    border: 1px solid #4F46E5;
    color: #ffffff;
}
QPushButton#btn_run_tests:hover {
    background-color: #4338CA;
}
QTableWidget {
    background-color: #FFFFFF;
    gridline-color: #E5E7EB;
    color: #111827;
    border: 1px solid #D1D5DB;
}
QHeaderView::section {
    background-color: #F3F4F6;
    color: #111827;
    padding: 5px;
    border: 1px solid #E5E7EB;
}
QProgressBar {
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    text-align: center;
    background-color: #E5E7EB;
    color: #111827;
}
QProgressBar::chunk {
    background-color: #2563EB;
}
QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    color: #111827;
    padding: 4px;
}
QComboBox:disabled {
    background-color: #F3F4F6;
    color: #9CA3AF;
    border: 1px solid #E5E7EB;
}
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #111827;
    selection-background-color: #E5E7EB;
    selection-color: #2563EB;
    border: 1px solid #D1D5DB;
}
QMenuBar {
    background-color: #FFFFFF;
    color: #111827;
    border-bottom: 1px solid #E5E7EB;
}
QMenuBar::item {
    background-color: transparent;
    padding: 6px 12px;
}
QMenuBar::item:selected {
    background-color: #F3F4F6;
    color: #2563EB;
}
QMenu {
    background-color: #FFFFFF;
    color: #111827;
    border: 1px solid #D1D5DB;
}
QMenu::item {
    padding: 6px 24px;
}
QMenu::item:selected {
    background-color: #F3F4F6;
    color: #2563EB;
}
"""

class TestWorker(QThread):
    status_signal = Signal(str)
    log_signal = Signal(str)
    finished_signal = Signal(bool, str)

    def __init__(self, bent_dir, language="PT"):
        super().__init__()
        self.bent_dir = bent_dir
        self.language = language

    def run(self):
        self.status_signal.emit("Executando roteiro de testes de validação..." if self.language == "PT" else "Running validation test suite...")
        path_d = "C:/Users/mosqu/OneDrive/Antigravity/IBSimion/D/.venv/Scripts/python.exe"
        path_root = "C:/Users/mosqu/OneDrive/Antigravity/IBSimion/.venv/Scripts/python.exe"
        venv_python = path_d if os.path.exists(path_d) else path_root
        cmd = [venv_python, "run_pipeline.py"]
        try:
            process = subprocess.Popen(
                cmd,
                cwd=self.bent_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )
            while True:
                try:
                    line = process.stdout.readline()
                except Exception as e:
                    line = f"[Decoding error: {e}]\n"
                if not line and process.poll() is not None:
                    break
                if line:
                    self.log_signal.emit(line)
            
            success = (process.returncode == 0)
            self.finished_signal.emit(success, "Roteiro de testes concluído." if self.language == "PT" else "Test suite completed.")
        except Exception as e:
            self.log_signal.emit(f"Exceção ao rodar os testes: {e}\n" if self.language == "PT" else f"Exception running tests: {e}\n")
            self.finished_signal.emit(False, str(e))

class SimWorker(QThread):
    status_signal = Signal(str)
    log_signal = Signal(str)
    finished_signal = Signal(bool, float) # (success, duration)
    opt_step_signal = Signal(int, int, float, list) # (iter, max_iter, loss, voltages)
    opt_finished_signal = Signal(bool, list) # (success, best_voltages)

    def __init__(self, is_opt=False, params=None, language="PT"):
        super().__init__()
        self.is_opt = is_opt
        self.params = params
        self.language = language
        self.running = True

    def run(self):
        start_time = time.time()
        backend_dir = get_backend_dir()
        
        # Ensure config_scenario_example.json and potential.txt are present in the backend folder
        res_config = resolve_resource("config_scenario_example.json")
        res_potential = resolve_resource("potential.txt")
        
        target_config = os.path.join(backend_dir, "config_scenario_example.json")
        target_potential = os.path.join(backend_dir, "potential.txt")
        
        if os.path.exists(res_config) and not os.path.exists(target_config):
            try:
                shutil.copy(res_config, target_config)
            except Exception as e:
                print(f"Error copying config file: {e}")
                
        if os.path.exists(res_potential) and not os.path.exists(target_potential):
            try:
                shutil.copy(res_potential, target_potential)
            except Exception as e:
                print(f"Error copying potential file: {e}")

        config_path = os.path.join(backend_dir, "config_scenario.json")
        
        if not self.is_opt:
            self.status_signal.emit("Executando simulação física..." if self.language == "PT" else "Running physical simulation...")
            self.write_config(config_path, self.params)
            success = self.execute_wsl(backend_dir)
            duration = time.time() - start_time
            if success:
                self.status_signal.emit("Estado: Espera (Hold / Active Pause)")
                self.finished_signal.emit(success, duration)
                self.running = True
                while self.running:
                    self.msleep(100)
            else:
                self.finished_signal.emit(success, duration)
        else:
            self.status_signal.emit("Iniciando otimização física..." if self.language == "PT" else "Starting physical optimization...")
            max_iter = self.params.get("max_iter", 20)
            
            # Identify which geometries are Dirichlet to optimize their voltage
            geometries = self.params.get("geometries", [])
            dirichlet_indices = [idx for idx, geom in enumerate(geometries) if geom.get("type", "Dirichlet") == "Dirichlet"]
            x0 = [geometries[idx]["voltage"] for idx in dirichlet_indices]
            
            if not x0:
                self.opt_finished_signal.emit(False, [])
                return
                
            import scipy.optimize as opt
            curr_iter = 0
            best_x = x0
            best_loss = float('inf')
            
            def loss_function(x):
                nonlocal curr_iter, best_loss, best_x
                if not self.running:
                    raise Exception("Otimização interrompida pelo usuário")
                
                trial_params = self.params.copy()
                trial_geoms = [geom.copy() for geom in trial_params["geometries"]]
                for idx, val in enumerate(x):
                    trial_geoms[dirichlet_indices[idx]]["voltage"] = float(val)
                trial_params["geometries"] = trial_geoms
                
                self.write_config(config_path, trial_params)
                success = self.execute_wsl(backend_dir)
                
                if success:
                    loss, trans, emitt, fwhm = self.evaluate_results(backend_dir, trial_params)
                else:
                    loss = 1e6
                
                if loss < best_loss:
                    best_loss = loss
                    best_x = x
                
                curr_iter += 1
                self.opt_step_signal.emit(min(curr_iter, max_iter), max_iter, best_loss, list(best_x))
                return loss
            
            try:
                opt.minimize(
                    loss_function, 
                    x0, 
                    method='Nelder-Mead', 
                    options={'maxiter': max_iter, 'xatol': 1.0, 'fatol': 1e-3, 'disp': False}
                )
                success = True
            except Exception as e:
                print("Optimization run stopped:", e)
                success = False
                
            self.opt_finished_signal.emit(self.running and success, list(best_x))
            
            if self.running and success:
                self.status_signal.emit("Estado: Espera (Hold / Active Pause)")
                self.running = True
                while self.running:
                    self.msleep(100)

    def write_config(self, filepath, params):
        import copy
        p_copy = copy.deepcopy(params)
        
        def clean_path(val):
            if isinstance(val, str):
                p = val.replace("\\", "/")
                if p.startswith("./data/"):
                    p = "../data/" + p[7:]
                elif p.startswith("data/"):
                    p = "../data/" + p[5:]
                elif "/" in p:
                    p = "../data/" + os.path.basename(p)
                else:
                    p = "../data/" + p
                return p
            return val

        # Sanitização recursiva contra nós nulos ocultos em subchaves do cenário
        def _sanitize_dict(d):
            if isinstance(d, dict):
                for k, v in d.items():
                    if v is None:
                        d[k] = 0.0
                    else:
                        _sanitize_dict(v)
            elif isinstance(d, list):
                for i, v in enumerate(d):
                    if v is None:
                        d[i] = 0.0
                    else:
                        _sanitize_dict(v)

        _sanitize_dict(p_copy)

        if "geometries" in p_copy and isinstance(p_copy["geometries"], list):
            for geom in p_copy["geometries"]:
                if "file_path" in geom:
                    geom["file_path"] = clean_path(geom["file_path"])
        
        if "magnetic_field_file" in p_copy:
            p_copy["magnetic_field_file"] = clean_path(p_copy["magnetic_field_file"])

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(p_copy, f, indent=4)

    def execute_wsl(self, backend_dir):
        if os.name == 'nt':
            cmd = f'wsl bash -c "cd {backend_dir} && ./ibsimu_wrapper config_scenario.json"'
            cwd_val = None
            shell_val = True
        else:
            cmd = ["./ibsimu_wrapper", "config_scenario.json"]
            cwd_val = backend_dir
            shell_val = False
            
        try:
            self.process = subprocess.Popen(
                cmd, 
                shell=shell_val, 
                cwd=cwd_val,
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )
            while True:
                if not self.running:
                    try:
                        if os.name == 'nt':
                            subprocess.run("wsl killall ibsimu_wrapper", shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                        else:
                            subprocess.run("killall ibsimu_wrapper", shell=True)
                    except Exception:
                        pass
                    self.process.terminate()
                    self.process.wait()
                    break
                try:
                    line = self.process.stdout.readline()
                except Exception as e:
                    line = f"[Decoding/Read error: {e}]\n"
                if not line and self.process.poll() is not None:
                    break
                if line:
                    self.log_signal.emit(line)
            return self.process.returncode == 0 if self.running else False
        except Exception as e:
            self.log_signal.emit(f"Exceção de Execução: {e}\n" if self.language == "PT" else f"Execution Exception: {e}\n")
            return False

    def evaluate_results(self, backend_dir, params):
        tof_path = os.path.join(backend_dir, "tof.txt")
        if not os.path.exists(tof_path):
            return 1e6, 0.0, 0.0, 0.0
            
        try:
            data = load_numpy_file_safe(tof_path)
            if data is None or data.size == 0 or len(data) == 0:
                return 1e6, 0.0, 0.0, 0.0

            # Total particles generated
            n_part_gen = sum(beam.get("particulas", 0) for beam in params.get("beams", []))
            if n_part_gen <= 0:
                n_part_gen = 50000
            n_part_rec = len(data)
            trans = n_part_rec / n_part_gen
            
            # RMS Emittance
            x = data[:, 1]
            vx = data[:, 2]
            vz = data[:, 6]
            vz[vz == 0] = 1.0 # avoid div zero
            xp = vx / vz
            
            dx = x - np.mean(x)
            dxp = xp - np.mean(xp)
            x2_mean = np.mean(dx**2)
            xp2_mean = np.mean(dxp**2)
            xxp_mean = np.mean(dx * dxp)
            emitt = np.sqrt(max(0.0, x2_mean * xp2_mean - xxp_mean**2))
            
            # FWHM of TOF (in seconds)
            times = data[:, 0]
            if len(times) > 5:
                hist, bin_edges = np.histogram(times, bins=50)
                max_val = np.max(hist)
                if max_val > 0:
                    half_max = max_val / 2.0
                    indices = np.where(hist >= half_max)[0]
                    if len(indices) >= 2:
                        fwhm = bin_edges[indices[-1]] - bin_edges[indices[0]]
                    else:
                        fwhm = np.std(times) * 2.355
                else:
                    fwhm = np.std(times) * 2.355
            else:
                fwhm = 0.0
                
            w_trans = params.get("w_trans", 1.0)
            w_emit = params.get("w_emit", 1.0)
            w_tof = params.get("w_tof", 1.0)
            
            loss = - w_trans * trans + w_emit * (emitt * 1e6) + w_tof * (fwhm * 1e9)
            return loss, trans, emitt, fwhm
        except Exception as e:
            print("Erro ao avaliar os resultados da simulação:", e)
            return 1e6, 0.0, 0.0, 0.0

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.parent_window = parent
        theme_mode = getattr(parent, 'theme_mode', 'dark')
        facecolor = '#F3F4F6' if theme_mode == 'light' else '#111827'
        bg_color = '#FFFFFF' if theme_mode == 'light' else '#0B0F19'
        fg_color = '#000000' if theme_mode == 'light' else '#F3F4F6'
        grid_color = '#D1D5DB' if theme_mode == 'light' else '#1F2937'
        title_color = '#000000' if theme_mode == 'light' else '#3B82F6'

        fig = Figure(figsize=(width, height), dpi=dpi, facecolor=facecolor)
        self.axes = fig.add_subplot(111)
        self.axes.set_facecolor(bg_color)
        self.axes.spines['bottom'].set_color(grid_color)
        self.axes.spines['top'].set_color(grid_color)
        self.axes.spines['left'].set_color(grid_color)
        self.axes.spines['right'].set_color(grid_color)
        self.axes.tick_params(colors=fg_color, which='both')
        self.axes.xaxis.label.set_color(fg_color)
        self.axes.yaxis.label.set_color(fg_color)
        self.axes.title.set_color(title_color)
        super().__init__(fig)

    def draw(self):
        if self.parent_window and hasattr(self.parent_window, 'apply_theme_to_figure'):
            self.parent_window.apply_theme_to_figure(self.figure)
        super().draw()

    def draw_idle(self):
        if self.parent_window and hasattr(self.parent_window, 'apply_theme_to_figure'):
            self.parent_window.apply_theme_to_figure(self.figure)
        super().draw_idle()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        import os
        self.backend_dir = get_backend_dir()
        self.setStyleSheet(STYLESHEET)
        self.theme_mode = "dark"
        icon_path = resolve_resource("frontend/ibsimion_icon.png")
        if os.path.exists(icon_path):
            from PySide6.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_path))
        
        self.language = "PT"
        
        # Generalist Mode: State data structures start empty
        self.geometries = []
        self.beams = []
        
        # Parallel Execution Defaults
        import os
        cpu_cores = os.cpu_count() or 4
        self.threads = max(1, int(cpu_cores * 0.7))
        
        # Output dump control states
        self.dump_potential = True
        self.dump_charge_density = True
        self.dump_trajectory_density = True
        self.dump_tof = True
        
        self.opt_losses = []
        self.opt_iterations = []
        self.worker = None
        self.simulation_cache = {}
        
        # PIC animation state variables
        self.animation_timer = QTimer(self)
        self.animation_timer.setInterval(200)
        self.animation_timer.timeout.connect(self.advance_pic_animation)
        self.pic_snapshots = []
        self.pic_times = []
        self._current_geom_row = None

        self.setup_ui()
        self.retranslate_ui()
        self.reload_geometries_table()
        self.reload_beams_table()
        
    def setup_ui(self):
        self.setWindowTitle("IBSimion v2.0.1 - Core Pipeline Stable")
        self.resize(1360, 860)
        
        # Menu Bar
        self.menu_bar = self.menuBar()
        
        # Menu Arquivo
        self.menu_arquivo = self.menu_bar.addMenu("Arquivo")
        self.action_abrir = self.menu_arquivo.addAction("Abrir Projeto (.JSON)")
        self.action_abrir.setShortcut("Ctrl+O")
        self.action_abrir.triggered.connect(self.abrir_projeto)
        self.action_salvar = self.menu_arquivo.addAction("Salvar Projeto (.JSON)")
        self.action_salvar.setShortcut("Ctrl+S")
        self.action_salvar.triggered.connect(self.salvar_projeto)
        self.menu_arquivo.addSeparator()
        self.action_sair = self.menu_arquivo.addAction("Sair")
        self.action_sair.setShortcut("Ctrl+Q")
        self.action_sair.triggered.connect(self.close)
        
        # Menu Testes
        self.menu_testes = self.menu_bar.addMenu("Testes")
        self.action_run_tests = self.menu_testes.addAction("Executar Roteiro de Testes")
        self.action_run_tests.setShortcut("Ctrl+T")
        self.action_run_tests.triggered.connect(self.run_validation_tests)
        
        # Menu Ajuda
        self.menu_ajuda = self.menu_bar.addMenu("Ajuda")
        self.action_manual = self.menu_ajuda.addAction("Manual de Uso")
        self.action_manual.setShortcut("F1")
        self.action_manual.triggered.connect(self.show_help_dialog)
        self.action_sobre = self.menu_ajuda.addAction("Sobre")
        self.action_sobre.setShortcut("Ctrl+H")
        self.action_sobre.triggered.connect(self.show_about_dialog)
        
        # Corner Widget Layout (Theme Button & Language Selector)
        self.corner_widget = QWidget()
        corner_layout = QHBoxLayout(self.corner_widget)
        corner_layout.setContentsMargins(0, 0, 10, 0)
        corner_layout.setSpacing(10)
        
        # Theme Switcher Button
        self.btn_theme = QPushButton("Modo Claro")
        self.btn_theme.clicked.connect(self.toggle_theme)
        self.btn_theme.setStyleSheet("""
            QPushButton {
                background-color: #1F2937;
                border: 1px solid #3B82F6;
                border-radius: 4px;
                color: #F3F4F6;
                padding: 4px 8px;
                font-weight: bold;
            }
        """)
        corner_layout.addWidget(self.btn_theme)
        
        # Language Selector
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["PT", "EN"])
        self.combo_lang.currentIndexChanged.connect(self.change_language)
        self.combo_lang.setStyleSheet("""
            QComboBox {
                background-color: #1F2937;
                border: 1px solid #3B82F6;
                border-radius: 4px;
                color: #F3F4F6;
                padding: 4px 8px;
                font-weight: bold;
            }
        """)
        corner_layout.addWidget(self.combo_lang)
        self.menu_bar.setCornerWidget(self.corner_widget, Qt.TopRightCorner)
        
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Tab Widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Progress Bar & Status Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.lbl_status = QLabel("Pronto.")
        self.lbl_status.setStyleSheet("color: #9CA3AF; padding: 2px;")
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.lbl_status)
        
        self.create_config_tab()
        self.create_workstation_tab()
        self.create_run_tab()
        self.create_diagnostics_tab()
        self.update_plane_z_from_mesh()

    def create_config_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # Left Panel (Mesh settings & external field)
        left_layout = QVBoxLayout()
        self.mesh_box = QGroupBox("Arquitetura de Malhas e Mapas Magnéticos")
        grid_mesh = QGridLayout(self.mesh_box)
        
        self.lbl_h = QLabel("Passo da Malha h (m):")
        grid_mesh.addWidget(self.lbl_h, 0, 0)
        self.txt_h = QLineEdit("0.001")
        grid_mesh.addWidget(self.txt_h, 0, 1)
        
        self.lbl_zmax = QLabel("Limite longitudinal Z max (m):")
        grid_mesh.addWidget(self.lbl_zmax, 1, 0)
        self.txt_zmax = QLineEdit("0.36")
        grid_mesh.addWidget(self.txt_zmax, 1, 1)
        
        self.lbl_rmax = QLabel("Limite radial R max (m):")
        grid_mesh.addWidget(self.lbl_rmax, 2, 0)
        self.txt_rmax = QLineEdit("0.035")
        grid_mesh.addWidget(self.txt_rmax, 2, 1)
        
        # External Magnetic Field
        self.lbl_bfield = QLabel("Mapear Campo Magnético Externo (.TXT):")
        grid_mesh.addWidget(self.lbl_bfield, 3, 0)
        self.chk_bfield = QCheckBox("Habilitar")
        self.chk_bfield.setStyleSheet("color: #F3F4F6;")
        grid_mesh.addWidget(self.chk_bfield, 3, 1)
        
        self.txt_bfield_path = QLineEdit("field.txt")
        grid_mesh.addWidget(self.txt_bfield_path, 4, 0)
        self.btn_browse_bfield = QPushButton("Procurar...")
        self.btn_browse_bfield.clicked.connect(self.browse_bfield_file)
        grid_mesh.addWidget(self.btn_browse_bfield, 4, 1)
        
        left_layout.addWidget(self.mesh_box)
        
        # Simulation Regime
        self.regime_box = QGroupBox("Configuração de Regime / Simulação")
        grid_regime = QGridLayout(self.regime_box)
        self.lbl_regime = QLabel("Modo de Regime:")
        grid_regime.addWidget(self.lbl_regime, 0, 0)
        self.cb_regime = QComboBox()
        self.cb_regime.addItems(["CW", "PIC"])
        self.cb_regime.currentIndexChanged.connect(self.toggle_regime_fields)
        grid_regime.addWidget(self.cb_regime, 0, 1)
        
        self.lbl_dt = QLabel("Passo de tempo PIC dt (s):")
        grid_regime.addWidget(self.lbl_dt, 1, 0)
        self.txt_dt = QLineEdit("5e-8")
        grid_regime.addWidget(self.txt_dt, 1, 1)
        
        self.lbl_tfinal = QLabel("Tempo de simulação final T (s):")
        grid_regime.addWidget(self.lbl_tfinal, 2, 0)
        self.txt_tfinal = QLineEdit("5.1e-6")
        grid_regime.addWidget(self.txt_tfinal, 2, 1)
        
        self.lbl_cfl = QLabel("CFL: OK")
        self.lbl_cfl.setStyleSheet("color: #10B981; font-weight: bold;")
        grid_regime.addWidget(self.lbl_cfl, 3, 0, 1, 2)

        self.lbl_pic_suggestion = QLabel("")
        self.lbl_pic_suggestion.setStyleSheet("color: #60A5FA; font-weight: bold;")
        self.lbl_pic_suggestion.setWordWrap(True)
        grid_regime.addWidget(self.lbl_pic_suggestion, 4, 0, 1, 2)

        self.btn_apply_pic_suggestion = QPushButton("Aplicar Sugestões PIC")
        self.btn_apply_pic_suggestion.setVisible(False)
        self.btn_apply_pic_suggestion.clicked.connect(self.apply_pic_suggestions)
        grid_regime.addWidget(self.btn_apply_pic_suggestion, 5, 0, 1, 2)
        
        # Connect inputs to update CFL and plane Z coordinates
        self.txt_h.textChanged.connect(self.check_cfl)
        self.txt_dt.textChanged.connect(self.check_cfl)
        self.txt_h.textChanged.connect(self.update_plane_z_from_mesh)
        self.txt_zmax.textChanged.connect(self.update_plane_z_from_mesh)
        self.update_plane_z_from_mesh()
        
        left_layout.addWidget(self.regime_box)
        left_layout.addStretch()
        layout.addLayout(left_layout, 1)
        
        # Right Panel (Beams manager)
        right_layout = QVBoxLayout()
        self.beams_box = QGroupBox("Configuração Fina de Feixes")
        beam_main_layout = QVBoxLayout(self.beams_box)
        
        self.table_beams = QTableWidget()
        self.table_beams.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_beams.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_beams.setColumnCount(13)
        self.table_beams.setHorizontalHeaderLabels([
            "Nome", "Partículas", "Corrente (mA)", "Massa (u)", "Carga (e)", "Energia (eV)", "Emit. (m-rad)", "Distrib.",
            "Orig. Z (m)", "Orig. X (m)", "Orig. Y (m)", "Dir. X (ux)", "Dir. Z (uz)"
        ])
        self.table_beams.itemChanged.connect(self.on_beam_table_edited)
        self.table_beams.itemSelectionChanged.connect(self.on_beam_selected)
        beam_main_layout.addWidget(self.table_beams)
        
        btn_beam_layout = QHBoxLayout()
        self.btn_add_beam = QPushButton("[+] Adicionar Feixe")
        self.btn_add_beam.clicked.connect(self.add_beam_row)
        self.btn_remove_beam = QPushButton("[-] Remover Selecionado")
        self.btn_remove_beam.clicked.connect(self.remove_beam_row)
        self.btn_import_beams = QPushButton("Importar Tabela de Feixes")
        self.btn_import_beams.clicked.connect(self.import_beams_file)
        btn_beam_layout.addWidget(self.btn_add_beam)
        btn_beam_layout.addWidget(self.btn_remove_beam)
        btn_beam_layout.addWidget(self.btn_import_beams)
        beam_main_layout.addLayout(btn_beam_layout)
        
        # Selected beam properties editor (Summary View)
        self.group_beam_editor = QGroupBox("Editor de Feixe Selecionado")
        self.group_beam_editor.setEnabled(False)
        beam_editor_layout = QVBoxLayout(self.group_beam_editor)
        
        self.beam_summary = QTextEdit()
        self.beam_summary.setReadOnly(True)
        self.beam_summary.setStyleSheet("""
            QTextEdit {
                background-color: #111827;
                color: #F3F4F6;
                border: 1px solid #1F2937;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
                padding: 10px;
            }
        """)
        beam_editor_layout.addWidget(self.beam_summary)
        beam_main_layout.addWidget(self.group_beam_editor)
        right_layout.addWidget(self.beams_box)
        layout.addLayout(right_layout, 2)
        
        self.tabs.addTab(tab, "Configurações & Feixes")
        self.toggle_regime_fields()

    def create_workstation_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # Left sidebar: Solids manager tree list & lateral properties fields
        left_panel = QVBoxLayout()
        self.solids_box = QGroupBox("Gerenciador de Geometrias e Sólidos")
        solids_layout = QVBoxLayout(self.solids_box)
        
        self.table_geoms = QTableWidget()
        self.table_geoms.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_geoms.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_geoms.setColumnCount(6)
        self.table_geoms.setHorizontalHeaderLabels(["Nome", "Arquivo", "Tipo", "Modo Sólido", "Potencial (V)", "Z-Offset (m)"])
        self.table_geoms.itemSelectionChanged.connect(self.on_geometry_selected)
        solids_layout.addWidget(self.table_geoms)
        
        btn_solid_layout = QHBoxLayout()
        self.btn_add_solid = QPushButton("[+] Inserir Sólido (STL/DXF)")
        self.btn_add_solid.clicked.connect(self.add_geometry_row)
        self.btn_remove_solid = QPushButton("[-] Excluir Sólido")
        self.btn_remove_solid.clicked.connect(self.remove_geometry_row)
        btn_solid_layout.addWidget(self.btn_add_solid)
        btn_solid_layout.addWidget(self.btn_remove_solid)
        solids_layout.addLayout(btn_solid_layout)
        
        left_panel.addWidget(self.solids_box)
        
        # Sidebar Editor panel
        self.group_editor = QGroupBox("Editor de Objeto Físico Selecionado")
        self.group_editor.setEnabled(False)
        editor_layout = QGridLayout(self.group_editor)
        
        self.lbl_editor_name = QLabel("Nome do Objeto:")
        editor_layout.addWidget(self.lbl_editor_name, 0, 0)
        self.editor_name = QLineEdit()
        editor_layout.addWidget(self.editor_name, 0, 1)
        
        self.lbl_editor_file = QLabel("Caminho do Arquivo:")
        editor_layout.addWidget(self.lbl_editor_file, 1, 0)
        self.editor_file = QLineEdit()
        self.editor_file.setReadOnly(True)
        editor_layout.addWidget(self.editor_file, 1, 1)
        self.btn_browse_geom = QPushButton("...")
        self.btn_browse_geom.clicked.connect(self.browse_geom_file)
        editor_layout.addWidget(self.btn_browse_geom, 1, 2)
        
        self.lbl_editor_btype = QLabel("Tipo de Fronteira:")
        editor_layout.addWidget(self.lbl_editor_btype, 2, 0)
        self.editor_btype = QComboBox()
        self.editor_btype.addItems(["Dirichlet", "Neumann"])
        editor_layout.addWidget(self.editor_btype, 2, 1)
        
        self.lbl_editor_voltage = QLabel("Potencial Elétrico (V):")
        editor_layout.addWidget(self.lbl_editor_voltage, 3, 0)
        self.editor_voltage = QDoubleSpinBox()
        self.editor_voltage.setRange(-100000.0, 100000.0)
        self.editor_voltage.setSingleStep(50.0)
        editor_layout.addWidget(self.editor_voltage, 3, 1)
        
        self.lbl_editor_translation = QLabel("Offsets de Translação (m):")
        editor_layout.addWidget(self.lbl_editor_translation, 4, 0)
        offset_layout = QHBoxLayout()
        self.editor_tx = QDoubleSpinBox()
        self.editor_tx.setRange(-1.0, 1.0)
        self.editor_tx.setDecimals(4)
        self.editor_tx.setSingleStep(0.01)
        self.editor_ty = QDoubleSpinBox()
        self.editor_ty.setRange(-1.0, 1.0)
        self.editor_ty.setDecimals(4)
        self.editor_ty.setSingleStep(0.01)
        self.editor_tz = QDoubleSpinBox()
        self.editor_tz.setRange(-1.0, 1.0)
        self.editor_tz.setDecimals(4)
        self.editor_tz.setSingleStep(0.01)
        offset_layout.addWidget(self.editor_tx)
        offset_layout.addWidget(self.editor_ty)
        offset_layout.addWidget(self.editor_tz)
        editor_layout.addLayout(offset_layout, 4, 1, 1, 2)
        
        # Scale
        self.lbl_editor_scale = QLabel("Escala (STL/DXF):")
        editor_layout.addWidget(self.lbl_editor_scale, 5, 0)
        self.editor_scale = QDoubleSpinBox()
        self.editor_scale.setRange(1e-6, 100.0)
        self.editor_scale.setDecimals(6)
        self.editor_scale.setValue(0.001)
        editor_layout.addWidget(self.editor_scale, 5, 1)
        
        # Layer
        self.lbl_editor_layer = QLabel("Camada DXF (Layer):")
        editor_layout.addWidget(self.lbl_editor_layer, 6, 0)
        self.editor_layer = QComboBox()
        editor_layout.addWidget(self.editor_layer, 6, 1)
        
        # Modo de Sólido 3D
        self.lbl_editor_mapping = QLabel("Modo de Sólido 3D:")
        editor_layout.addWidget(self.lbl_editor_mapping, 7, 0)
        self.editor_mapping = QComboBox()
        self.editor_mapping.addItems(["Rotação Simétrica (Eixo Z)", "Extrusão Planar Linear"])
        editor_layout.addWidget(self.editor_mapping, 7, 1)
        
        # Aplicar Edições button
        self.btn_apply_edits = QPushButton("Aplicar Edições")
        self.btn_apply_edits.setObjectName("btn_apply_edits")
        self.btn_apply_edits.setStyleSheet("background-color: #3B82F6; color: white; font-weight: bold;")
        self.btn_apply_edits.clicked.connect(self.apply_sidebar_edits)
        editor_layout.addWidget(self.btn_apply_edits, 8, 0, 1, 3)
        
        left_panel.addWidget(self.group_editor)
        layout.addLayout(left_panel, 1)
        
        # Right panel: 3D PyVista Viewport & controls
        right_panel = QVBoxLayout()
        
        viewport_ctrls = QHBoxLayout()
        self.lbl_view_mode = QLabel("Visualização:")
        viewport_ctrls.addWidget(self.lbl_view_mode)
        self.cb_view_mode = QComboBox()
        self.cb_view_mode.addItems(["3D Perspectiva", "Plano ZX (2D)", "Plano ZY (2D)", "Plano XY (2D)"])
        self.cb_view_mode.currentIndexChanged.connect(self.change_camera_view)
        viewport_ctrls.addWidget(self.cb_view_mode)
        
        self.lbl_traj_color = QLabel("Colorir Trajetórias:")
        viewport_ctrls.addWidget(self.lbl_traj_color)
        self.cb_traj_color = QComboBox()
        self.cb_traj_color.addItems(["Espécie", "Massa", "Carga", "Energia (Z-Grad)", "Corrente"])
        self.cb_traj_color.currentIndexChanged.connect(self.change_trajectory_coloring)
        viewport_ctrls.addWidget(self.cb_traj_color)
        
        self.btn_load_to_visualizer = QPushButton("Recarregar 3D")
        self.btn_load_to_visualizer.clicked.connect(self.reload_visualizer_scene)
        viewport_ctrls.addWidget(self.btn_load_to_visualizer)
        
        right_panel.addLayout(viewport_ctrls)
        
        # Interactive PyVista interactor
        self.pyvista_widget = PyVistaWidget(self)
        right_panel.addWidget(self.pyvista_widget, 4)
        
        # PIC Animation control box
        self.group_pic_anim = QGroupBox("Controle de Animação PIC")
        self.group_pic_anim.setEnabled(False)
        pic_layout = QHBoxLayout(self.group_pic_anim)
        
        self.btn_play_pic = QPushButton("Animar (Play)")
        self.btn_play_pic.clicked.connect(self.toggle_pic_animation)
        pic_layout.addWidget(self.btn_play_pic)
        
        self.slider_pic = QSlider(Qt.Horizontal)
        self.slider_pic.valueChanged.connect(self.on_pic_slider_changed)
        pic_layout.addWidget(self.slider_pic)
        
        self.lbl_pic_time = QLabel("Tempo: 0.0s")
        pic_layout.addWidget(self.lbl_pic_time)
        
        right_panel.addWidget(self.group_pic_anim)
        
        layout.addLayout(right_panel, 2)
        self.tabs.addTab(tab, "Workstation 3D & Sólidos")

    def create_run_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # Left Panel (Actions and Console output)
        left_layout = QVBoxLayout()
        
        self.actions_box = QGroupBox("Ações de Controle")
        actions_layout = QVBoxLayout(self.actions_box)
        
        self.btn_start_sim = QPushButton("Executar Simulação Simples")
        self.btn_start_sim.setObjectName("btn_run")
        self.btn_start_sim.clicked.connect(self.run_simple_simulation)
        actions_layout.addWidget(self.btn_start_sim)
        
        self.btn_start_opt = QPushButton("Iniciar Otimização Nelder-Mead")
        self.btn_start_opt.setObjectName("btn_opt")
        self.btn_start_opt.clicked.connect(self.run_optimization)
        actions_layout.addWidget(self.btn_start_opt)
        
        self.btn_stop_opt = QPushButton("Interromper Otimização")
        self.btn_stop_opt.setEnabled(False)
        self.btn_stop_opt.clicked.connect(self.stop_worker)
        actions_layout.addWidget(self.btn_stop_opt)
        
        self.btn_close_sim = QPushButton("Fechar Simulação")
        self.btn_close_sim.setObjectName("btn_close_sim")
        self.btn_close_sim.setEnabled(False)
        self.btn_close_sim.clicked.connect(self.close_simulation)
        actions_layout.addWidget(self.btn_close_sim)
        
        left_layout.addWidget(self.actions_box)
        
        # Optimizer parameters
        self.opt_params_box = QGroupBox("Parâmetros do Otimizador")
        grid_opt = QGridLayout(self.opt_params_box)
        
        self.lbl_opt_w_trans = QLabel("Peso Transmissão:")
        grid_opt.addWidget(self.lbl_opt_w_trans, 0, 0)
        self.txt_w_trans = QLineEdit("2.0")
        grid_opt.addWidget(self.txt_w_trans, 0, 1)
        
        self.lbl_opt_w_emit = QLabel("Peso Emitância:")
        grid_opt.addWidget(self.lbl_opt_w_emit, 1, 0)
        self.txt_w_emit = QLineEdit("0.5")
        grid_opt.addWidget(self.txt_w_emit, 1, 1)
        
        self.lbl_opt_w_tof = QLabel("Peso TOF FWHM:")
        grid_opt.addWidget(self.lbl_opt_w_tof, 2, 0)
        self.txt_w_tof = QLineEdit("1.0")
        grid_opt.addWidget(self.txt_w_tof, 2, 1)
        
        self.lbl_opt_max_iter = QLabel("Iterações Máximas:")
        grid_opt.addWidget(self.lbl_opt_max_iter, 3, 0)
        self.txt_max_iter = QLineEdit("20")
        grid_opt.addWidget(self.txt_max_iter, 3, 1)
        
        left_layout.addWidget(self.opt_params_box)
        
        # Configuração de Execução e Dumps
        self.dumps_box = QGroupBox("Configuração de Execução e Dumps")
        dumps_layout = QGridLayout(self.dumps_box)
        
        self.lbl_threads = QLabel("Threads Computacionais:")
        dumps_layout.addWidget(self.lbl_threads, 0, 0)
        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(1, 128)
        self.spin_threads.setValue(self.threads)
        dumps_layout.addWidget(self.spin_threads, 0, 1)
        
        self.chk_dump_potential = QCheckBox("Exportar Potencial Elétrico (Central Slice)")
        self.chk_dump_potential.setChecked(self.dump_potential)
        self.chk_dump_potential.setStyleSheet("color: #F3F4F6;")
        dumps_layout.addWidget(self.chk_dump_potential, 1, 0, 1, 2)
        
        self.chk_dump_charge = QCheckBox("Exportar Densidade de Carga (Central Slice)")
        self.chk_dump_charge.setChecked(self.dump_charge_density)
        self.chk_dump_charge.setStyleSheet("color: #F3F4F6;")
        dumps_layout.addWidget(self.chk_dump_charge, 2, 0, 1, 2)
        
        self.chk_dump_trajdens = QCheckBox("Exportar Densidade de Trajetórias")
        self.chk_dump_trajdens.setChecked(self.dump_trajectory_density)
        self.chk_dump_trajdens.setStyleSheet("color: #F3F4F6;")
        dumps_layout.addWidget(self.chk_dump_trajdens, 3, 0, 1, 2)
        
        self.chk_dump_tof = QCheckBox("Exportar Espectrometria TOF")
        self.chk_dump_tof.setChecked(self.dump_tof)
        self.chk_dump_tof.setStyleSheet("color: #F3F4F6;")
        dumps_layout.addWidget(self.chk_dump_tof, 4, 0, 1, 2)
        
        left_layout.addWidget(self.dumps_box)
        
        # Console Log Console
        self.console_box = QGroupBox(self.tr("console_box"))
        console_layout = QVBoxLayout(self.console_box)
        from PySide6.QtWidgets import QTextEdit
        self.txt_console = QTextEdit()
        self.txt_console.setReadOnly(True)
        self.txt_console.setStyleSheet("background-color: #030712; color: #10B981; font-family: Consolas; font-size: 10px;")
        console_layout.addWidget(self.txt_console)
        left_layout.addWidget(self.console_box, 1)
        
        layout.addLayout(left_layout, 1)
        
        # Right Panel: Convergence graph
        right_layout = QVBoxLayout()
        self.canvas_convergence = MplCanvas(self, width=5, height=3, dpi=100)
        right_layout.addWidget(self.canvas_convergence)
        
        # Light Navigation Toolbar
        self.toolbar_conv = NavigationToolbar(self.canvas_convergence, self)
        self.style_navigation_toolbar(self.toolbar_conv)
        right_layout.addWidget(self.toolbar_conv)
        
        layout.addLayout(right_layout, 1)
        self.tabs.addTab(tab, "Simular & Otimizar")

    def create_diagnostics_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # Left Panel (plane coordinates and metrics table)
        left_layout = QVBoxLayout()
        self.diag_ctrl_box = QGroupBox("Configurações do Plano de Corte")
        grid_diag = QGridLayout(self.diag_ctrl_box)
        
        self.lbl_plane_mode = QLabel("Modo de Plano:")
        grid_diag.addWidget(self.lbl_plane_mode, 0, 0)
        self.cb_plane_mode = QComboBox()
        self.cb_plane_mode.addItems(["Automático (Detector)", "Arbitrário"])
        self.cb_plane_mode.currentIndexChanged.connect(self.on_plane_mode_changed)
        grid_diag.addWidget(self.cb_plane_mode, 0, 1)

        self.lbl_plane_orient = QLabel("Orientação do Plano:")
        grid_diag.addWidget(self.lbl_plane_orient, 1, 0)
        self.cb_plane_orient = QComboBox()
        self.cb_plane_orient.addItems(["Plano XY (Z = coord)", "Plano XZ (Y = coord)", "Plano YZ (X = coord)"])
        self.cb_plane_orient.currentIndexChanged.connect(self.calculate_diagnostics_plots)
        grid_diag.addWidget(self.cb_plane_orient, 1, 1)
        
        self.lbl_plane_z = QLabel("Coordenada Z do Plano (m):")
        grid_diag.addWidget(self.lbl_plane_z, 2, 0)
        self.txt_plane_z = QLineEdit("0.3549")
        grid_diag.addWidget(self.txt_plane_z, 2, 1)
        
        self.btn_clip_plane = QPushButton("Configurar Plano de Corte")
        self.btn_clip_plane.clicked.connect(self.apply_clipping_plane_diagnostics)
        grid_diag.addWidget(self.btn_clip_plane, 3, 0, 1, 2)
        
        left_layout.addWidget(self.diag_ctrl_box)
        
        # Estilo & Exportação TOF
        self.tof_opt_box = QGroupBox("Estilo & Exportação TOF")
        grid_tof_opt = QGridLayout(self.tof_opt_box)
        
        self.lbl_tof_style = QLabel("Estilo Histograma:")
        grid_tof_opt.addWidget(self.lbl_tof_style, 0, 0)
        self.cb_tof_style = QComboBox()
        self.cb_tof_style.addItems(["Barras Preenchidas", "Linha Suavizada", "Dispersão com Tendência"])
        self.cb_tof_style.currentIndexChanged.connect(self.calculate_diagnostics_plots)
        grid_tof_opt.addWidget(self.cb_tof_style, 0, 1)

        self.lbl_map_2d = QLabel("Tipo de Mapa 2D:")
        grid_tof_opt.addWidget(self.lbl_map_2d, 1, 0)
        self.cb_map_2d = QComboBox()
        self.cb_map_2d.addItems(["Potencial Elétrico", "Densidade de Carga (Rho) - Trajetórias", "Densidade de Corrente (J) - Trajetórias"])
        self.cb_map_2d.currentIndexChanged.connect(self.calculate_diagnostics_plots)
        grid_tof_opt.addWidget(self.cb_map_2d, 1, 1)
        
        self.btn_export_tof = QPushButton("Exportar Dados TOF (.TXT)")
        self.btn_export_tof.clicked.connect(self.export_tof_data)
        grid_tof_opt.addWidget(self.btn_export_tof, 2, 0, 1, 2)
        
        left_layout.addWidget(self.tof_opt_box)
        
        # Metrics Table
        self.metrics_box = QGroupBox("Métricas Científicas")
        metrics_layout = QVBoxLayout(self.metrics_box)
        self.table_metrics = QTableWidget(3, 2)
        self.table_metrics.setHorizontalHeaderLabels(["Métrica", "Valor"])
        self.table_metrics.horizontalHeader().setStretchLastSection(True)
        self.table_metrics.setItem(0, 0, QTableWidgetItem("Transmissão (%)"))
        self.table_metrics.setItem(1, 0, QTableWidgetItem("Emitância RMS X (m·rad)"))
        self.table_metrics.setItem(2, 0, QTableWidgetItem("FWHM do Tempo de Voo (ns)"))
        metrics_layout.addWidget(self.table_metrics)
        left_layout.addWidget(self.metrics_box)
        left_layout.addStretch()
        
        layout.addLayout(left_layout, 1)
        
        # Right Panel (Tabbed Matplotlib graphs)
        right_layout = QVBoxLayout()
        self.diag_tabs = QTabWidget()
        right_layout.addWidget(self.diag_tabs)
        
        # Sub tab 1: TOF Histogram
        sub_tab_tof = QWidget()
        tof_layout = QVBoxLayout(sub_tab_tof)
        self.canvas_tof = MplCanvas(self)
        self.toolbar_tof = NavigationToolbar(self.canvas_tof, self)
        self.style_navigation_toolbar(self.toolbar_tof)
        tof_layout.addWidget(self.canvas_tof)
        tof_layout.addWidget(self.toolbar_tof)
        self.diag_tabs.addTab(sub_tab_tof, "Espectro de Tempo de Voo (TOF)")
        
        # Sub tab 2: Beam Profile scatter plot (X vs Y)
        sub_tab_profile = QWidget()
        profile_layout = QVBoxLayout(sub_tab_profile)
        self.canvas_profile = MplCanvas(self)
        self.toolbar_profile = NavigationToolbar(self.canvas_profile, self)
        self.style_navigation_toolbar(self.toolbar_profile)
        profile_layout.addWidget(self.canvas_profile)
        profile_layout.addWidget(self.toolbar_profile)
        self.diag_tabs.addTab(sub_tab_profile, "Perfil Transversal de Corte (X vs Y)")
        
        # Sub tab 3: 2D Field Contour map
        sub_tab_contours = QWidget()
        contours_layout = QVBoxLayout(sub_tab_contours)
        self.canvas_contours = MplCanvas(self)
        self.toolbar_contours = NavigationToolbar(self.canvas_contours, self)
        self.style_navigation_toolbar(self.toolbar_contours)
        contours_layout.addWidget(self.canvas_contours)
        contours_layout.addWidget(self.toolbar_contours)
        self.diag_tabs.addTab(sub_tab_contours, "Mapa de Campo 2D & Equipotenciais")

        # Sub tab 4: Phase Space (X vs X' & Y vs Y')
        sub_tab_phase = QWidget()
        phase_layout = QVBoxLayout(sub_tab_phase)
        self.canvas_phase = MplCanvas(self)
        self.toolbar_phase = NavigationToolbar(self.canvas_phase, self)
        self.style_navigation_toolbar(self.toolbar_phase)
        phase_layout.addWidget(self.canvas_phase)
        phase_layout.addWidget(self.toolbar_phase)
        self.diag_tabs.addTab(sub_tab_phase, "Espaço Fásico (X vs X' & Y vs Y')")

        # Sub tab 5: Emittance RMS histogram
        sub_tab_emittance = QWidget()
        emittance_layout = QVBoxLayout(sub_tab_emittance)
        self.canvas_emittance = MplCanvas(self)
        self.toolbar_emittance = NavigationToolbar(self.canvas_emittance, self)
        self.style_navigation_toolbar(self.toolbar_emittance)
        emittance_layout.addWidget(self.canvas_emittance)
        emittance_layout.addWidget(self.toolbar_emittance)
        self.diag_tabs.addTab(sub_tab_emittance, "Histograma de Emitância RMS")
        
        layout.addWidget(self.diag_tabs, 3)
        self.tabs.addTab(tab, "Diagnósticos Avançados")

    def style_navigation_toolbar(self, toolbar):
        """Ajusta a navegação do Matplotlib garantindo que o fundo seja claro e contrastante para evitar ícones ocultos."""
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #F3F4F6;
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                padding: 2px;
            }
            QToolButton {
                background-color: #E5E7EB;
                color: #111827;
                border: 1px solid #C4C9D3;
                border-radius: 3px;
                margin: 2px;
                padding: 3px;
            }
            QToolButton:hover {
                background-color: #D1D5DB;
                border: 1px solid #9CA3AF;
            }
            QToolButton:pressed {
                background-color: #9CA3AF;
            }
        """)

    def browse_bfield_file(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Selecionar Tabela de Campo Magnético (.TXT)", "", "TXT Files (*.txt)")
        if fn:
            self.txt_bfield_path.setText(fn)

    def browse_geom_file(self):
        selected_rows = self.table_geoms.selectedItems()
        if not selected_rows:
            return
        fn, _ = QFileDialog.getOpenFileName(self, "Selecionar Arquivo CAD/Sólido", "", "CAD Files (*.stl *.dxf)")
        if fn:
            self.editor_file.setText(fn)
            # Dynamically update the layer ComboBox based on the newly selected file
            is_dxf = fn.lower().endswith(".dxf")
            self.editor_layer.clear()
            if is_dxf:
                self.editor_layer.setEnabled(True)
                layers = get_dxf_layers(fn)
                if layers:
                    self.editor_layer.addItems(layers)
                else:
                    self.editor_layer.addItem("0")
            else:
                self.editor_layer.addItem("N/A (STL)")
                self.editor_layer.setEnabled(False)

    def toggle_regime_fields(self):
        is_pic = (self.cb_regime.currentText() == "PIC")
        self.txt_dt.setEnabled(is_pic)
        self.txt_tfinal.setEnabled(is_pic)
        self.check_cfl()

    def check_cfl(self):
        try:
            h = float(self.txt_h.text())
            dt = float(self.txt_dt.text())
            
            # v_max estimated from xe ion at ~1000 eV (vq ~ 3.8e4 m/s)
            v_max = 3.8e4
            t_cfl = h / v_max if v_max > 0 else 1e-6
            
            if dt >= t_cfl:
                self.lbl_cfl.setText(f"⚠️ Aviso CFL: dt >= h/v_max! Risco de divergência (Max dt: {t_cfl:.2e} s)")
                self.lbl_cfl.setStyleSheet("color: #F43F5E; font-weight: bold;")
            else:
                self.lbl_cfl.setText("CFL: OK (dt < h/v_max)")
                self.lbl_cfl.setStyleSheet("color: #10B981; font-weight: bold;")
        except Exception:
            pass

    @Slot()
    def update_plane_z_from_mesh(self):
        if not hasattr(self, 'txt_plane_z'):
            return
        try:
            zmax_val = self.txt_zmax.text().strip()
            h_val = self.txt_h.text().strip()
            if zmax_val and h_val:
                zmax = float(zmax_val)
                h = float(h_val)
                plane_z = zmax - h
                self.txt_plane_z.setText(f"{plane_z:.4f}")
        except ValueError:
            pass

    def on_plane_mode_changed(self):
        is_auto = (self.cb_plane_mode.currentIndex() == 0)
        self.txt_plane_z.setEnabled(not is_auto)
        if is_auto:
            self.update_auto_plane_z()

    def update_auto_plane_z(self):
        # Scan geometries for "detector", "detions", "det_ion"
        detector_z = 0.3549
        found = False
        for geom in self.geometries:
            name_lower = geom["name"].lower()
            if "detector" in name_lower or "detions" in name_lower or "det_ion" in name_lower:
                detector_z = geom["translation"][2]
                found = True
                break
        if not found and self.geometries:
            # Fallback to the last geometry's Z translation coordinate
            detector_z = self.geometries[-1]["translation"][2]
            
        self.txt_plane_z.setText(f"{detector_z:.4f}")

    # -------------------------------------------------------------------------
    # Geometries Table / Sidebar bindings
    # -------------------------------------------------------------------------
    def reload_geometries_table(self):
        self.table_geoms.blockSignals(True)
        self.table_geoms.setRowCount(len(self.geometries))
        for idx, geom in enumerate(self.geometries):
            self.table_geoms.setItem(idx, 0, QTableWidgetItem(geom["name"]))
            self.table_geoms.setItem(idx, 1, QTableWidgetItem(os.path.basename(geom["file_path"])))
            self.table_geoms.setItem(idx, 2, QTableWidgetItem(geom["type"]))
            
            mapping_str = "Rot. Z" if geom.get("mapping", "rotz") == "rotz" else "Extrusão"
            self.table_geoms.setItem(idx, 3, QTableWidgetItem(mapping_str))
            
            self.table_geoms.setItem(idx, 4, QTableWidgetItem(f"{geom['voltage']:.1f}"))
            self.table_geoms.setItem(idx, 5, QTableWidgetItem(f"{geom['translation'][2]:.4f}"))
        self.table_geoms.blockSignals(False)

    def add_geometry_row(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Selecionar Sólido STL/DXF", "", "CAD Files (*.stl *.dxf)")
        if not fn:
            return
        
        ext = fn.split(".")[-1].lower()
        if ext == "dxf":
            layers = get_dxf_layers(fn)
            if not layers:
                layers = ["0"]
            
            first_idx = len(self.geometries)
            for layer in layers:
                new_geom = {
                    "name": layer,
                    "file_path": fn,
                    "layer": layer,
                    "voltage": 0.0,
                    "type": "Dirichlet",
                    "translation": [0.0, 0.0, 0.0],
                    "scale": 0.001,
                    "mapping": "rotz"
                }
                self.geometries.append(new_geom)
            
            self.reload_geometries_table()
            self.table_geoms.selectRow(first_idx)
            self.reload_visualizer_scene()
        else:
            name = "Sólido " + str(len(self.geometries) + 1)
            new_geom = {
                "name": name,
                "file_path": fn,
                "voltage": 0.0,
                "type": "Dirichlet",
                "translation": [0.0, 0.0, 0.0],
                "scale": 0.001,
                "mapping": "rotz"
            }
            self.geometries.append(new_geom)
            self.reload_geometries_table()
            self.table_geoms.selectRow(len(self.geometries) - 1)
            self.reload_visualizer_scene()

    def remove_geometry_row(self):
        row = self.table_geoms.currentRow()
        if row < 0 or row >= len(self.geometries):
            return
        self.geometries.pop(row)
        self._current_geom_row = None
        self.reload_geometries_table()
        self.group_editor.setEnabled(False)
        self.reload_visualizer_scene()

    def on_geometry_selected(self):
        row = self.table_geoms.currentRow()
        if row < 0 or row >= len(self.geometries):
            self.group_editor.setEnabled(False)
            self._current_geom_row = None
            return
            
        self._current_geom_row = row
        geom = self.geometries[row]
        
        # Block child signals temporarily to avoid triggering changes
        self.editor_name.blockSignals(True)
        self.editor_file.blockSignals(True)
        self.editor_btype.blockSignals(True)
        self.editor_voltage.blockSignals(True)
        self.editor_tx.blockSignals(True)
        self.editor_ty.blockSignals(True)
        self.editor_tz.blockSignals(True)
        self.editor_scale.blockSignals(True)
        self.editor_layer.blockSignals(True)
        self.editor_mapping.blockSignals(True)
        
        self.editor_name.setText(geom["name"])
        self.editor_file.setText(geom["file_path"])
        self.editor_btype.setCurrentText(geom["type"])
        self.editor_voltage.setValue(geom["voltage"])
        self.editor_tx.setValue(geom["translation"][0])
        self.editor_ty.setValue(geom["translation"][1])
        self.editor_tz.setValue(geom["translation"][2])
        self.editor_scale.setValue(geom.get("scale", 1.0))
        
        mapping_val = geom.get("mapping", "rotz")
        if mapping_val == "unity":
            self.editor_mapping.setCurrentIndex(1)
        else:
            self.editor_mapping.setCurrentIndex(0)
        
        # Dynamically populate layers ComboBox if it is a DXF file
        file_path = geom["file_path"]
        is_dxf = file_path.lower().endswith(".dxf")
        
        self.editor_layer.clear()
        if is_dxf:
            self.editor_layer.setEnabled(True)
            abs_path = resolve_path(file_path)
            
            layers = get_dxf_layers(abs_path)
            if not layers:
                # Fallback if parsing failed or file path is not resolved yet
                self.editor_layer.addItems(["0", geom.get("layer", "")])
            else:
                self.editor_layer.addItems(layers)
            
            saved_layer = geom.get("layer", "")
            idx = self.editor_layer.findText(saved_layer)
            if idx >= 0:
                self.editor_layer.setCurrentIndex(idx)
            elif saved_layer:
                self.editor_layer.addItem(saved_layer)
                self.editor_layer.setCurrentText(saved_layer)
        else:
            self.editor_layer.addItem("N/A (STL)")
            self.editor_layer.setEnabled(False)
            
        self.group_editor.setEnabled(True)
        
        # Unblock signals
        self.editor_layer.blockSignals(False)
        self.editor_scale.blockSignals(False)
        self.editor_tz.blockSignals(False)
        self.editor_ty.blockSignals(False)
        self.editor_tx.blockSignals(False)
        self.editor_voltage.blockSignals(False)
        self.editor_btype.blockSignals(False)
        self.editor_file.blockSignals(False)
        self.editor_name.blockSignals(False)
        self.editor_mapping.blockSignals(False)

    def apply_sidebar_edits(self):
        row = getattr(self, "_current_geom_row", None)
        if row is None or row < 0 or row >= len(self.geometries):
            selected_rows = self.table_geoms.selectedItems()
            if not selected_rows:
                return
            row = selected_rows[0].row()
            
        if row < 0 or row >= len(self.geometries):
            return
            
        geom = self.geometries[row]
        
        geom["name"] = self.editor_name.text()
        geom["file_path"] = self.editor_file.text()
        geom["type"] = self.editor_btype.currentText()
        geom["voltage"] = self.editor_voltage.value()
        geom["translation"] = [self.editor_tx.value(), self.editor_ty.value(), self.editor_tz.value()]
        geom["scale"] = self.editor_scale.value()
        geom["mapping"] = "unity" if self.editor_mapping.currentIndex() == 1 else "rotz"
        
        is_dxf = geom["file_path"].lower().endswith(".dxf")
        if is_dxf:
            geom["layer"] = self.editor_layer.currentText()
            geom["name"] = geom["layer"]
        else:
            geom.pop("layer", None) # STL has no layers
            
        self.reload_geometries_table()
        
        # Keep row selection
        self.table_geoms.blockSignals(True)
        self.table_geoms.selectRow(row)
        self.table_geoms.blockSignals(False)
        self._current_geom_row = row
        
        # Reload 3D scene
        self.reload_visualizer_scene()

    # -------------------------------------------------------------------------
    # Beams Table bindings
    # -------------------------------------------------------------------------
    def reload_beams_table(self):
        self.table_beams.blockSignals(True)
        self.table_beams.setRowCount(len(self.beams))
        for idx, beam in enumerate(self.beams):
            self.table_beams.setItem(idx, 0, QTableWidgetItem(beam["nome"]))
            self.table_beams.setItem(idx, 1, QTableWidgetItem(str(beam["particulas"])))
            curr_val = beam['corrente']
            curr_str = f"{curr_val:.2e}" if curr_val < 1e-2 else f"{curr_val:.3f}"
            self.table_beams.setItem(idx, 2, QTableWidgetItem(curr_str))
            self.table_beams.setItem(idx, 3, QTableWidgetItem(f"{beam['massa']:.4f}"))
            self.table_beams.setItem(idx, 4, QTableWidgetItem(f"{beam['carga']:.1f}"))
            self.table_beams.setItem(idx, 5, QTableWidgetItem(f"{beam['energy']:.1f}"))
            self.table_beams.setItem(idx, 6, QTableWidgetItem(f"{beam['emittance']:.2e}"))
            self.table_beams.setItem(idx, 7, QTableWidgetItem(beam["distribution"]))
            
            # Additional columns
            self.table_beams.setItem(idx, 8, QTableWidgetItem(f"{beam.get('orig_z', beam.get('z_start', 0.081)):.4f}"))
            self.table_beams.setItem(idx, 9, QTableWidgetItem(f"{beam.get('orig_x', 0.0):.4f}"))
            self.table_beams.setItem(idx, 10, QTableWidgetItem(f"{beam.get('orig_y', 0.0):.4f}"))
            self.table_beams.setItem(idx, 11, QTableWidgetItem(f"{beam.get('dir_x', 0.0):.4f}"))
            self.table_beams.setItem(idx, 12, QTableWidgetItem(f"{beam.get('dir_z', 1.0):.4f}"))
        self.table_beams.blockSignals(False)

    def add_beam_row(self):
        new_beam = {
            "nome": f"Feixe {len(self.beams) + 1}",
            "particulas": 3000,
            "corrente": 1.0,
            "massa": 136.2,
            "carga": 1.0,
            "energy": 1000.0,
            "emittance": 1e-6,
            "distribution": "Uniform",
            "radius": 0.0005,
            "z_start": 0.081,
            "orig_z": 0.081,
            "orig_x": 0.0,
            "orig_y": 0.0,
            "dir_x": 0.0,
            "dir_z": 1.0
        }
        self.beams.append(new_beam)
        self.reload_beams_table()

    def remove_beam_row(self):
        row = self.table_beams.currentRow()
        if row < 0 or row >= len(self.beams):
            return
        self.beams.pop(row)
        self.reload_beams_table()
        self.group_beam_editor.setEnabled(False)
        self.beam_summary.clear()

    def on_beam_table_edited(self, item):
        row = item.row()
        col = item.column()
        val = item.text()
        beam = self.beams[row]
        
        try:
            if col == 0:
                beam["nome"] = val
            elif col == 1:
                beam["particulas"] = int(val)
            elif col == 2:
                beam["corrente"] = float(val)
            elif col == 3:
                beam["massa"] = float(val)
            elif col == 4:
                beam["carga"] = float(val)
            elif col == 5:
                beam["energy"] = float(val)
            elif col == 6:
                beam["emittance"] = float(val)
            elif col == 7:
                beam["distribution"] = val
            elif col == 8:
                beam["orig_z"] = float(val)
                beam["z_start"] = float(val)
            elif col == 9:
                beam["orig_x"] = float(val)
            elif col == 10:
                beam["orig_y"] = float(val)
            elif col == 11:
                beam["dir_x"] = float(val)
            elif col == 12:
                beam["dir_z"] = float(val)
            
            # Format row and update summary view
            self.reload_beams_table()
            self.table_beams.blockSignals(True)
            self.table_beams.setCurrentCell(row, col)
            self.table_beams.blockSignals(False)
            self.update_beam_summary()
        except Exception as e:
            QMessageBox.warning(self, "Valor Inválido" if self.language == "PT" else "Invalid Value",
                                f"Erro ao atualizar feixe: {e}" if self.language == "PT" else f"Error updating beam: {e}")
            self.reload_beams_table()

    def on_beam_selected(self):
        row = self.table_beams.currentRow()
        if row < 0 or row >= len(self.beams):
            self.group_beam_editor.setEnabled(False)
            self.beam_summary.clear()
            return
            
        self.group_beam_editor.setEnabled(True)
        self.update_beam_summary()

    def update_beam_summary(self):
        row = self.table_beams.currentRow()
        if row < 0 or row >= len(self.beams):
            self.beam_summary.setHtml(
                "<p style='color: #9CA3AF; font-style: italic;'>"
                "Nenhum feixe selecionado." if self.language == "PT" else "No beam selected."
                "</p>"
            )
            return
        beam = self.beams[row]
        
        if self.language == "PT":
            html = f"""
            <h3 style="color: #3B82F6; margin-top: 0px; margin-bottom: 8px;">{beam['nome']}</h3>
            <table style="width: 100%; border-collapse: collapse; color: #F3F4F6;">
                <tr><td style="padding: 3px 0; color: #9CA3AF;">Macropartículas:</td><td style="text-align: right; font-weight: bold;">{beam['particulas']}</td></tr>
                <tr><td style="padding: 3px 0; color: #9CA3AF;">Corrente:</td><td style="text-align: right; font-weight: bold;">{beam['corrente']:.3e} mA</td></tr>
                <tr><td style="padding: 3px 0; color: #9CA3AF;">Massa:</td><td style="text-align: right; font-weight: bold;">{beam['massa']:.4f} u</td></tr>
                <tr><td style="padding: 3px 0; color: #9CA3AF;">Carga:</td><td style="text-align: right; font-weight: bold;">{beam['carga']:.1f} e</td></tr>
                <tr><td style="padding: 3px 0; color: #9CA3AF;">Energia:</td><td style="text-align: right; font-weight: bold;">{beam['energy']:.1f} eV</td></tr>
                <tr><td style="padding: 3px 0; color: #9CA3AF;">Emitância:</td><td style="text-align: right; font-weight: bold;">{beam['emittance']:.3e} m-rad</td></tr>
                <tr><td style="padding: 3px 0; color: #9CA3AF;">Distribuição:</td><td style="text-align: right; font-weight: bold;">{beam['distribution']}</td></tr>
                <tr><td style="padding: 3px 0; color: #9CA3AF;">Origem (Z, X, Y):</td><td style="text-align: right; font-weight: bold;">({beam.get('orig_z', beam.get('z_start', 0.081)):.4f}, {beam.get('orig_x', 0.0):.4f}, {beam.get('orig_y', 0.0):.4f}) m</td></tr>
                <tr><td style="padding: 3px 0; color: #9CA3AF;">Direção (ux, uz):</td><td style="text-align: right; font-weight: bold;">({beam.get('dir_x', 0.0):.4f}, {beam.get('dir_z', 1.0):.4f})</td></tr>
            </table>
            """
        else:
            html = f"""
            <h3 style="color: #3B82F6; margin-top: 0px; margin-bottom: 8px;">{beam['nome']}</h3>
            <table style="width: 100%; border-collapse: collapse; color: #F3F4F6;">
                <tr><td style="padding: 3px 0; color: #9CA3AF;">Macroparticles:</td><td style="text-align: right; font-weight: bold;">{beam['particulas']}</td></tr>
                <tr><td style="padding: 3px 0; color: #9CA3AF;">Current:</td><td style="text-align: right; font-weight: bold;">{beam['corrente']:.3e} mA</td></tr>
                <tr><td style="padding: 3px 0; color: #9CA3AF;">Mass:</td><td style="text-align: right; font-weight: bold;">{beam['massa']:.4f} u</td></tr>
                <tr><td style="padding: 3px 0; color: #9CA3AF;">Charge:</td><td style="text-align: right; font-weight: bold;">{beam['carga']:.1f} e</td></tr>
                <tr><td style="padding: 3px 0; color: #9CA3AF;">Energy:</td><td style="text-align: right; font-weight: bold;">{beam['energy']:.1f} eV</td></tr>
                <tr><td style="padding: 3px 0; color: #9CA3AF;">Emittance:</td><td style="text-align: right; font-weight: bold;">{beam['emittance']:.3e} m-rad</td></tr>
                <tr><td style="padding: 3px 0; color: #9CA3AF;">Distribution:</td><td style="text-align: right; font-weight: bold;">{beam['distribution']}</td></tr>
                <tr><td style="padding: 3px 0; color: #9CA3AF;">Origin (Z, X, Y):</td><td style="text-align: right; font-weight: bold;">({beam.get('orig_z', beam.get('z_start', 0.081)):.4f}, {beam.get('orig_x', 0.0):.4f}, {beam.get('orig_y', 0.0):.4f}) m</td></tr>
                <tr><td style="padding: 3px 0; color: #9CA3AF;">Direction (ux, uz):</td><td style="text-align: right; font-weight: bold;">({beam.get('dir_x', 0.0):.4f}, {beam.get('dir_z', 1.0):.4f})</td></tr>
            </table>
            """
        self.beam_summary.setHtml(html)

    def import_beams_file(self):
        fn, _ = QFileDialog.getOpenFileName(
            self, "Importar Tabela de Feixes", "", "Spreadsheet/Text Files (*.xlsx *.txt *.csv)"
        )
        if not fn:
            return
            
        try:
            import pandas as pd
            if fn.lower().endswith(".xlsx"):
                df = pd.read_excel(fn)
            else:
                with open(fn, 'r', encoding='utf-8', errors='ignore') as f:
                    first_line = f.readline()
                delim = '\t' if '\t' in first_line else ','
                df = pd.read_csv(fn, sep=delim)
                
            df.columns = [str(c).strip() for c in df.columns]
            
            col_map = {}
            for col in df.columns:
                c_low = col.lower()
                if "nome" in c_low or "name" in c_low:
                    col_map["nome"] = col
                elif "particula" in c_low or "particle" in c_low or "n_part" in c_low:
                    col_map["particulas"] = col
                elif "corrente" in c_low or "current" in c_low:
                    col_map["corrente"] = col
                elif "massa" in c_low or "mass" in c_low:
                    col_map["massa"] = col
                elif "carga" in c_low or "charge" in c_low:
                    col_map["carga"] = col
                elif "energia" in c_low or "energy" in c_low:
                    col_map["energy"] = col
                elif "emitancia" in c_low or "emitância" in c_low or "emittance" in c_low:
                    col_map["emittance"] = col
                elif "distrib" in c_low or "distribution" in c_low:
                    col_map["distribution"] = col
                elif "orig_z" in c_low or "origem z" in c_low or "start z" in c_low:
                    col_map["orig_z"] = col
                elif "orig_x" in c_low or "origem x" in c_low or "start x" in c_low:
                    col_map["orig_x"] = col
                elif "orig_y" in c_low or "origem y" in c_low or "start y" in c_low:
                    col_map["orig_y"] = col
                elif "dir_x" in c_low or "direção x" in c_low or "steer x" in c_low:
                    col_map["dir_x"] = col
                elif "dir_z" in c_low or "direção z" in c_low or "steer z" in c_low:
                    col_map["dir_z"] = col
                    
            imported_count = 0
            for _, row in df.iterrows():
                nome = str(row[col_map["nome"]]) if "nome" in col_map else f"Feixe Importado {len(self.beams) + 1}"
                particulas = int(row[col_map["particulas"]]) if "particulas" in col_map else 3000
                
                corrente_raw = float(row[col_map["corrente"]]) if "corrente" in col_map else 1.0
                if "corrente" in col_map:
                    c_header = col_map["corrente"].lower()
                    if "(a)" in c_header or c_header.endswith("_a"):
                        corrente_raw *= 1000.0  # Amperes to mA
                corrente = corrente_raw
                
                massa = float(row[col_map["massa"]]) if "massa" in col_map else 136.2
                carga = float(row[col_map["carga"]]) if "carga" in col_map else 1.0
                energy = float(row[col_map["energy"]]) if "energy" in col_map else 1000.0
                emittance = float(row[col_map["emittance"]]) if "emittance" in col_map else 1e-6
                distribution = str(row[col_map["distribution"]]) if "distribution" in col_map else "Uniform"
                
                orig_z = float(row[col_map["orig_z"]]) if "orig_z" in col_map else 0.081
                orig_x = float(row[col_map["orig_x"]]) if "orig_x" in col_map else 0.0
                orig_y = float(row[col_map["orig_y"]]) if "orig_y" in col_map else 0.0
                dir_x = float(row[col_map["dir_x"]]) if "dir_x" in col_map else 0.0
                dir_z = float(row[col_map["dir_z"]]) if "dir_z" in col_map else 1.0
                
                new_beam = {
                    "nome": nome,
                    "particulas": particulas,
                    "corrente": corrente,
                    "massa": massa,
                    "carga": carga,
                    "energy": energy,
                    "emittance": emittance,
                    "distribution": distribution,
                    "radius": 0.0005,
                    "z_start": orig_z,
                    "orig_z": orig_z,
                    "orig_x": orig_x,
                    "orig_y": orig_y,
                    "dir_x": dir_x,
                    "dir_z": dir_z
                }
                self.beams.append(new_beam)
                imported_count += 1
                
            self.reload_beams_table()
            QMessageBox.information(
                self, "Importação Concluída", f"Foram importados {imported_count} feixes com sucesso!"
            )
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Importar", f"Não foi possível ler a tabela de feixes:\n{e}")

    # -------------------------------------------------------------------------
    # Execution & Otimização Control
    # -------------------------------------------------------------------------
    def to_wsl_path(self, path):
        if not path:
            return ""
        if ":" not in path and "\\" not in path:
            return path.replace("\\", "/")
        p = path.replace("\\", "/")
        if len(p) >= 2 and p[1] == ":":
            drive = p[0].lower()
            p = f"/mnt/{drive}{p[2:]}"
        return p

    def read_all_scenario_parameters(self):
        """Coleta todas as definições estruturadas da interface e gera os parâmetros para o cenário JSON."""
        h = float(self.txt_h.text())
        zmax = float(self.txt_zmax.text())
        rmax = float(self.txt_rmax.text())
        
        # Clean and dynamic geometries file paths in ./data/
        wsl_geoms = []
        for geom in self.geometries:
            geom_copy = geom.copy()
            filename = os.path.basename(geom["file_path"])
            geom_copy["file_path"] = f"./data/{filename}"
            # Ensure name and layer are aligned for DXF files
            is_dxf = geom["file_path"].lower().endswith(".dxf")
            if is_dxf and "layer" in geom:
                geom_copy["name"] = geom["layer"]
                geom_copy["layer"] = geom["layer"]
            wsl_geoms.append(geom_copy)
            
        bfield_wsl = f"./data/{os.path.basename(self.txt_bfield_path.text())}" if self.chk_bfield.isChecked() and self.txt_bfield_path.text() else ""
        
        # Construct scenario dict
        params = {
            "mode": self.cb_regime.currentText(),
            "h": h,
            "xmin": -rmax,
            "xmax": rmax,
            "ymin": -rmax,
            "ymax": rmax,
            "zmin": 0.0,
            "zmax": zmax,
            "geometries": wsl_geoms,
            "beams": self.beams,
            "bfield_enabled": self.chk_bfield.isChecked(),
            "magnetic_field_file": bfield_wsl,
            "diag_plane_z": float(self.txt_plane_z.text()) if self.txt_plane_z.text() else 0.3549,
            "dt": float(self.txt_dt.text()),
            "T_final": float(self.txt_tfinal.text()),
            "w_trans": float(self.txt_w_trans.text()),
            "w_emit": float(self.txt_w_emit.text()),
            "w_tof": float(self.txt_w_tof.text()),
            "max_iter": int(self.txt_max_iter.text()),
            "threads": self.spin_threads.value(),
            "dump_potential": self.chk_dump_potential.isChecked(),
            "dump_charge_density": self.chk_dump_charge.isChecked(),
            "dump_trajectory_density": self.chk_dump_trajdens.isChecked(),
            "dump_tof": self.chk_dump_tof.isChecked(),
            "generate_jpg": 0,
            "interactive_plot": 0
        }
        return params

    def run_simple_simulation(self):
        if self.worker and self.worker.isRunning():
            self.worker.running = False
            self.worker.wait()
            
        # CICLO DE LIMPEZA CONTRA ACÚMULO DE LIXO
        self.simulation_cache = {}
        import gc; gc.collect()
            
        self.btn_start_sim.setEnabled(False)
        self.btn_start_opt.setEnabled(False)
        self.btn_close_sim.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0) # Infinite scrolling
        self.txt_console.clear()
        
        params = self.read_all_scenario_parameters()
        self.worker = SimWorker(is_opt=False, params=params, language=self.language)
        self.worker.status_signal.connect(self.update_status_msg)
        self.worker.log_signal.connect(self.append_log)
        self.worker.finished_signal.connect(self.on_sim_finished)
        self.worker.start()

    def run_optimization(self):
        if self.worker and self.worker.isRunning():
            self.worker.running = False
            self.worker.wait()
            
        # CICLO DE LIMPEZA CONTRA ACÚMULO DE LIXO
        self.simulation_cache = {}
        import gc; gc.collect()
            
        self.btn_start_sim.setEnabled(False)
        self.btn_start_opt.setEnabled(False)
        self.btn_stop_opt.setEnabled(True)
        self.btn_close_sim.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.txt_console.clear()
        
        params = self.read_all_scenario_parameters()
        max_iter = params["max_iter"]
        self.progress_bar.setRange(0, max_iter)
        self.progress_bar.setValue(0)
        
        self.opt_losses = []
        self.opt_iterations = []
        self.canvas_convergence.axes.cla()
        self.canvas_convergence.draw()
        
        self.worker = SimWorker(is_opt=True, params=params, language=self.language)
        self.worker.status_signal.connect(self.update_status_msg)
        self.worker.log_signal.connect(self.append_log)
        self.worker.opt_step_signal.connect(self.on_opt_step)
        self.worker.opt_finished_signal.connect(self.on_opt_finished)
        self.worker.start()

    def stop_worker(self):
        if self.worker and self.worker.isRunning():
            self.worker.running = False
            try:
                kill_cmd = "wsl killall ibsimu_wrapper" if os.name == 'nt' else "killall ibsimu_wrapper"
                subprocess.run(kill_cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            except Exception:
                pass
            self.worker.wait()
            self.btn_stop_opt.setEnabled(False)
            self.lbl_status.setText("Pronto.")

    def close_simulation(self):
        if self.worker and self.worker.isRunning():
            self.worker.running = False
            try:
                kill_cmd = "wsl killall ibsimu_wrapper" if os.name == 'nt' else "killall ibsimu_wrapper"
                subprocess.run(kill_cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            except Exception:
                pass
            self.worker.wait()
        self.lbl_status.setText("Pronto.")
        self.btn_close_sim.setEnabled(False)

    def run_validation_tests(self):
        self.btn_start_sim.setEnabled(False)
        self.btn_start_opt.setEnabled(False)
        if hasattr(self, 'btn_run_tests'):
            self.btn_run_tests.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.txt_console.clear()
        
        frontend_dir = os.path.dirname(os.path.abspath(__file__))
        d_dir = os.path.dirname(frontend_dir)
        bent_dir = os.path.join(d_dir, "bent")
        
        self.test_worker = TestWorker(bent_dir, self.language)
        self.test_worker.status_signal.connect(self.update_status_msg)
        self.test_worker.log_signal.connect(self.append_log)
        self.test_worker.finished_signal.connect(self.on_tests_finished)
        self.test_worker.start()

    def on_tests_finished(self, success, msg):
        self.btn_start_sim.setEnabled(True)
        self.btn_start_opt.setEnabled(True)
        if hasattr(self, 'btn_run_tests'):
            self.btn_run_tests.setEnabled(True)
        self.progress_bar.setVisible(False)
        if success:
            self.lbl_status.setText(self.tr("status_test_success"))
            QMessageBox.information(
                self, 
                self.tr("win_title"), 
                "All tests passed!" if self.language == "EN" else "Todos os testes passaram!"
            )
        else:
            self.lbl_status.setText(self.tr("status_test_fail"))
            QMessageBox.warning(
                self, 
                self.tr("win_title"), 
                "Some tests failed. Check console logs." if self.language == "EN" else "Algum teste falhou. Verifique os logs no console."
            )

    @Slot(str)
    def update_status_msg(self, msg):
        self.lbl_status.setText(msg)

    @Slot(str)
    def append_log(self, text):
        self.txt_console.insertPlainText(text)
        self.txt_console.ensureCursorVisible()

    @Slot(bool, float)
    def on_sim_finished(self, success, duration):
        self.btn_start_sim.setEnabled(True)
        self.btn_start_opt.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            self.write_simulation_cache()
            self.lbl_status.setText("Estado: Espera (Hold / Active Pause)")
            self.btn_close_sim.setEnabled(True)
            self.reload_visualizer_scene()
            self.calculate_diagnostics_plots()
            if self.cb_regime.currentText() == "CW":
                self.calculate_pic_suggestions()
            else:
                self.lbl_pic_suggestion.setText("")
                self.btn_apply_pic_suggestion.setVisible(False)
        else:
            self.lbl_status.setText(self.tr("status_sim_error"))

    @Slot(int, int, float, list)
    def on_opt_step(self, iter_idx, max_iter, loss, voltages):
        self.progress_bar.setValue(iter_idx)
        self.lbl_status.setText(f"{self.tr('status_optimizing')} {iter_idx}/{max_iter} | Loss: {loss:.4f}")
        
        self.opt_iterations.append(iter_idx)
        self.opt_losses.append(loss)
        
        cols = self.get_theme_colors()
        self.canvas_convergence.axes.cla()
        self.canvas_convergence.axes.set_facecolor(cols["bg"])
        self.canvas_convergence.axes.plot(self.opt_iterations, self.opt_losses, 'c-o', label=self.tr("plot_loss_label"))
        self.canvas_convergence.axes.set_xlabel(self.tr("plot_convergence_xlabel"), color=cols["fg"])
        self.canvas_convergence.axes.set_ylabel(self.tr("plot_convergence_ylabel"), color=cols["fg"])
        self.canvas_convergence.axes.set_title(self.tr("plot_convergence_title"), color=cols["title"])
        self.canvas_convergence.axes.legend(facecolor=cols["legend_bg"], edgecolor=cols["legend_edge"], labelcolor=cols["legend_text"])
        self.canvas_convergence.axes.grid(True, color=cols["grid"])
        self.canvas_convergence.draw()
        
        # Update voltages of Dirichlet geometries in table/editor
        dirichlet_indices = [idx for idx, geom in enumerate(self.geometries) if geom.get("type", "Dirichlet") == "Dirichlet"]
        for idx, val in enumerate(voltages):
            if idx < len(dirichlet_indices):
                g_idx = dirichlet_indices[idx]
                self.geometries[g_idx]["voltage"] = val
        self.reload_geometries_table()
        
    @Slot(bool, list)
    def on_opt_finished(self, success, best_voltages):
        self.btn_start_sim.setEnabled(True)
        self.btn_start_opt.setEnabled(True)
        self.btn_stop_opt.setEnabled(False)
        self.progress_bar.setVisible(False)
        if success:
            self.write_simulation_cache()
            self.lbl_status.setText("Estado: Espera (Hold / Active Pause)")
            self.btn_close_sim.setEnabled(True)
            if self.cb_regime.currentText() == "CW":
                self.calculate_pic_suggestions()
            else:
                self.lbl_pic_suggestion.setText("")
                self.btn_apply_pic_suggestion.setVisible(False)
        else:
            self.lbl_status.setText(self.tr("status_opt_finished"))
        self.reload_visualizer_scene()
        self.calculate_diagnostics_plots()

    # -------------------------------------------------------------------------
    # 3D Viewport Controls
    # -------------------------------------------------------------------------
    def reload_visualizer_scene(self):
        """Atualiza a Workstation 3D com as trajetórias e as malhas transparentes."""
        self.pyvista_widget.clear_scene()
        
        # Loads geometry obj
        obj_path = os.path.join(self.backend_dir, "geometry.obj")
        self.pyvista_widget.load_geometry(obj_path)
        
        regime = self.cb_regime.currentText()
        if regime == "CW":
            self.group_pic_anim.setEnabled(False)
            if self.animation_timer.isActive():
                self.animation_timer.stop()
            traj_path = os.path.join(self.backend_dir, "trajectories.txt")
            
            color_modes = ['species', 'mass', 'charge', 'energy', 'current']
            color_by = color_modes[self.cb_traj_color.currentIndex()]
            self.pyvista_widget.load_trajectories(traj_path, color_by)
        else:
            self.group_pic_anim.setEnabled(True)
            self.pic_snapshots = []
            self.pic_times = []
            try:
                files = [f for f in os.listdir(self.backend_dir) if f.startswith("pout_") and f.endswith(".txt")]
                if files:
                    def get_time_from_fn(fn):
                        return float(fn[5:-4])
                    files.sort(key=get_time_from_fn)
                    self.pic_snapshots = [os.path.join(self.backend_dir, f) for f in files]
                    self.pic_times = [get_time_from_fn(f) for f in files]
                    
                    self.slider_pic.setRange(0, len(self.pic_snapshots) - 1)
                    self.slider_pic.setValue(0)
                    
                    if self.pic_snapshots:
                        self.pyvista_widget.load_pic_snapshot(self.pic_snapshots[0])
                        self.lbl_pic_time.setText(f"Tempo: {self.pic_times[0]:.2e} s")
            except Exception as e:
                print("Erro ao carregar snapshots PIC:", e)

    def change_camera_view(self):
        idx = self.cb_view_mode.currentIndex()
        if idx == 0:
            self.pyvista_widget.plotter.view_isometric()
        elif idx == 1:
            self.pyvista_widget.plotter.view_xz()
        elif idx == 2:
            self.pyvista_widget.plotter.view_zy()
        elif idx == 3:
            self.pyvista_widget.plotter.view_yx()
        self.pyvista_widget.plotter.reset_camera()

    def change_trajectory_coloring(self):
        self.reload_visualizer_scene()

    # PIC animation
    def toggle_pic_animation(self):
        if self.animation_timer.isActive():
            self.animation_timer.stop()
            self.btn_play_pic.setText("Animar (Play)")
        else:
            if self.pic_snapshots:
                self.animation_timer.start()
                self.btn_play_pic.setText("Pausar")
            else:
                QMessageBox.warning(self, "Simulação PIC Requerida", "Nenhum frame PIC encontrado. Execute primeiro.")

    def advance_pic_animation(self):
        if not self.pic_snapshots:
            self.animation_timer.stop()
            return
        curr = self.slider_pic.value()
        next_val = (curr + 1) % len(self.pic_snapshots)
        self.slider_pic.setValue(next_val)

    def on_pic_slider_changed(self, val):
        if 0 <= val < len(self.pic_snapshots):
            fn_val = os.path.basename(self.pic_snapshots[val])
            cached_data = self.simulation_cache.get("pout", {}).get(fn_val)
            self.pyvista_widget.load_pic_snapshot(cached_data if cached_data is not None else self.pic_snapshots[val])
            self.lbl_pic_time.setText(f"Tempo: {self.pic_times[val]:.2e} s")

    # -------------------------------------------------------------------------
    # Diagnostics & Cuts logic
    # -------------------------------------------------------------------------
    def write_simulation_cache(self):
        """Lê os novos arquivos gerados pelo motor backend utilizando NumPy e salva-os no cache local."""
        self.simulation_cache = {}
        
        pdb_path = os.path.join(self.backend_dir, "pdb.dat")
        if os.path.exists(pdb_path):
            try:
                # Carrega o pdb.dat como array NumPy de bytes (rápido e seguro)
                self.simulation_cache["pdb"] = load_numpy_file_safe(pdb_path, is_binary=True)
            except Exception as e:
                print(f"Erro ao carregar pdb.dat para o cache: {e}")
                
        tof_path = os.path.join(self.backend_dir, "tof.txt")
        if os.path.exists(tof_path):
            try:
                self.simulation_cache["tof"] = load_numpy_file_safe(tof_path)
            except Exception as e:
                print(f"Erro ao carregar tof.txt para o cache: {e}")
                
        pot_field_path = os.path.join(self.backend_dir, "potential_field.dat")
        if os.path.exists(pot_field_path):
            try:
                self.simulation_cache["potential_field"] = load_numpy_file_safe(pot_field_path)
            except Exception as e:
                print(f"Erro ao carregar potential_field.dat para o cache: {e}")
                
        charge_density_path = os.path.join(self.backend_dir, "charge_density.dat")
        if os.path.exists(charge_density_path):
            try:
                self.simulation_cache["charge_density"] = load_numpy_file_safe(charge_density_path)
            except Exception as e:
                print(f"Erro ao carregar charge_density.dat para o cache: {e}")
                
        trajectory_density_path = os.path.join(self.backend_dir, "trajectory_density.dat")
        if os.path.exists(trajectory_density_path):
            try:
                self.simulation_cache["trajectory_density"] = load_numpy_file_safe(trajectory_density_path)
            except Exception as e:
                print(f"Erro ao carregar trajectory_density.dat para o cache: {e}")

        traj_path = os.path.join(self.backend_dir, "trajectories.txt")
        if os.path.exists(traj_path):
            try:
                self.simulation_cache["trajectories"] = parse_trajectories(traj_path)
            except Exception as e:
                print(f"Erro ao carregar trajetórias para o cache: {e}")
                
        pout_cache = {}
        if os.path.exists(self.backend_dir):
            for fn in os.listdir(self.backend_dir):
                if fn.startswith("pout_") and fn.endswith(".txt"):
                    path = os.path.join(self.backend_dir, fn)
                    try:
                        pout_cache[fn] = load_numpy_file_safe(path)
                    except Exception as e:
                        print(f"Erro ao carregar {fn} para o cache: {e}")
        self.simulation_cache["pout"] = pout_cache

    def calculate_diagnostics_plots(self):
        """Analisa os arquivos dat/txt e gera os histogramas de TOF, perfil radial, e contornos equipotenciais 2D."""
        if not self.simulation_cache:
            self.write_simulation_cache()

        tof_path = os.path.join(self.backend_dir, "tof.txt")
        pot_field_path = os.path.join(self.backend_dir, "potential_field.dat")
        rho_field_path = os.path.join(self.backend_dir, "charge_density.dat")
        traj_path = os.path.join(self.backend_dir, "trajectories.txt")
        
        # 1. Load TOF and metrics
        data = self.simulation_cache.get("tof")
        cols = self.get_theme_colors()
        
        if data is None or data.size == 0:
            self.canvas_tof.axes.cla()
            self.canvas_tof.axes.set_facecolor(cols["bg"])
            self.canvas_tof.axes.text(0.5, 0.5, "Aguardando dados da simulação..." if self.language == "PT" else "Waiting for simulation data...",
                                      ha='center', va='center', color=cols["text_muted"], transform=self.canvas_tof.axes.transAxes, fontsize=12)
            self.canvas_tof.draw()
            
            self.canvas_profile.axes.cla()
            self.canvas_profile.axes.set_facecolor(cols["bg"])
            self.canvas_profile.axes.text(0.5, 0.5, "Aguardando dados da simulação..." if self.language == "PT" else "Waiting for simulation data...",
                                          ha='center', va='center', color=cols["text_muted"], transform=self.canvas_profile.axes.transAxes, fontsize=12)
            self.canvas_profile.draw()
            
            self.canvas_phase.figure.clear()
            ax_ph = self.canvas_phase.figure.add_subplot(111)
            ax_ph.set_facecolor(cols["bg"])
            ax_ph.text(0.5, 0.5, "Aguardando dados da simulação..." if self.language == "PT" else "Waiting for simulation data...",
                       ha='center', va='center', color=cols["text_muted"], transform=ax_ph.transAxes, fontsize=12)
            self.canvas_phase.draw()
            
            self.canvas_emittance.axes.cla()
            self.canvas_emittance.axes.set_facecolor(cols["bg"])
            self.canvas_emittance.axes.text(0.5, 0.5, "Aguardando dados da simulação..." if self.language == "PT" else "Waiting for simulation data...",
                                            ha='center', va='center', color=cols["text_muted"], transform=self.canvas_emittance.axes.transAxes, fontsize=12)
            self.canvas_emittance.draw()
            
            self.canvas_contours.axes.cla()
            self.canvas_contours.axes.set_facecolor(cols["bg"])
            self.canvas_contours.axes.text(0.5, 0.5, "Aguardando dados da simulação..." if self.language == "PT" else "Waiting for simulation data...",
                                           ha='center', va='center', color=cols["text_muted"], transform=self.canvas_contours.axes.transAxes, fontsize=12)
            self.canvas_contours.draw()
            return
            
        try:
            if data.ndim == 1:
                data = np.expand_dims(data, axis=0)
            if data.size > 0:
                times = data[:, 0]
                x_pos = data[:, 1]
                y_pos = data[:, 3]
                
                # TOF Histogram / Plot
                self.canvas_tof.axes.cla()
                self.canvas_tof.axes.set_facecolor(cols["bg"])
                
                style_idx = self.cb_tof_style.currentIndex()
                if style_idx == 0:  # Barras Preenchidas
                    self.canvas_tof.axes.hist(times * 1e6, bins=60, color='#8B5CF6', edgecolor='#D8B4FE', alpha=0.8)
                elif style_idx == 1:  # Linhas Suavizadas
                    counts, bin_edges = np.histogram(times * 1e6, bins=60)
                    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
                    if len(bin_centers) > 3:
                        try:
                            from scipy.interpolate import make_interp_spline
                            x_new = np.linspace(bin_centers.min(), bin_centers.max(), 300)
                            spl = make_interp_spline(bin_centers, counts, k=3)
                            y_new = spl(x_new)
                            y_new = np.clip(y_new, 0, None)
                            self.canvas_tof.axes.plot(x_new, y_new, color='#A78BFA', linewidth=2)
                            self.canvas_tof.axes.fill_between(x_new, y_new, color='#A78BFA', alpha=0.3)
                        except Exception:
                            self.canvas_tof.axes.plot(bin_centers, counts, color='#A78BFA', linewidth=2)
                            self.canvas_tof.axes.fill_between(bin_centers, counts, color='#A78BFA', alpha=0.3)
                    else:
                        self.canvas_tof.axes.plot(bin_centers, counts, color='#A78BFA', linewidth=2)
                        self.canvas_tof.axes.fill_between(bin_centers, counts, color='#A78BFA', alpha=0.3)
                elif style_idx == 2:  # Dispersão com Linha de Tendência (Multi-Gaussian Fit)
                    counts, bin_edges = np.histogram(times * 1e6, bins=60)
                    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
                    self.canvas_tof.axes.scatter(bin_centers, counts, color='#EC4899', alpha=0.7, edgecolors='none', s=25, label=self.tr("bins_label"))
                    if len(bin_centers) > 3:
                        popt, model_func = fit_multi_gaussian(bin_centers, counts)
                        if popt is not None and model_func is not None:
                            x_trend = np.linspace(bin_centers.min(), bin_centers.max(), 300)
                            y_trend = model_func(x_trend, *popt)
                            self.canvas_tof.axes.plot(x_trend, y_trend, color='#3B82F6', linewidth=2, label="Gaussian Fit" if self.language == "EN" else "Ajuste Gaussiano")
                        else:
                            try:
                                coefs = np.polyfit(bin_centers, counts, 3)
                                poly = np.poly1d(coefs)
                                x_trend = np.linspace(bin_centers.min(), bin_centers.max(), 200)
                                y_trend = poly(x_trend)
                                y_trend = np.clip(y_trend, 0, None)
                                self.canvas_tof.axes.plot(x_trend, y_trend, color='#F472B6', linewidth=2, linestyle='--', label=self.tr("trend_label"))
                            except Exception:
                                pass
                    self.canvas_tof.axes.legend(facecolor=cols["legend_bg"], edgecolor=cols["legend_edge"], labelcolor=cols["legend_text"])

                self.canvas_tof.axes.set_xlabel(self.tr("plot_tof_xlabel"), color=cols["fg"])
                self.canvas_tof.axes.set_ylabel(self.tr("plot_tof_ylabel"), color=cols["fg"])
                self.canvas_tof.axes.set_title(self.tr("plot_tof_title"), color=cols["title"])
                self.canvas_tof.axes.grid(True, color=cols["grid"])
                self.canvas_tof.draw()
                
                # Beam Profile cut (X vs Y scatter plot at the detector Z plane)
                self.canvas_profile.axes.cla()
                self.canvas_profile.axes.set_facecolor(cols["bg"])
                self.canvas_profile.axes.scatter(x_pos * 1000, y_pos * 1000, color='#10B981', alpha=0.6, edgecolors='none', s=8)
                self.canvas_profile.axes.set_xlabel(self.tr("plot_profile_xlabel"), color=cols["fg"])
                self.canvas_profile.axes.set_ylabel(self.tr("plot_profile_ylabel"), color=cols["fg"])
                self.canvas_profile.axes.set_title(self.tr("plot_profile_title"), color=cols["title"])
                self.canvas_profile.axes.grid(True, color=cols["grid"])
                self.canvas_profile.draw()
                
                # --- Phase Space Plot (X vs X' and Y vs Y' side-by-side) ---
                self.canvas_phase.figure.clear()
                ax_x = self.canvas_phase.figure.add_subplot(121)
                ax_y = self.canvas_phase.figure.add_subplot(122)
                
                for ax in [ax_x, ax_y]:
                    ax.yaxis.label.set_color('#F3F4F6')
                    ax.title.set_color('#3B82F6')
                    ax.grid(True, color='#1F2937')
                
                vx = data[:, 2]
                vy = data[:, 4]
                vz = data[:, 6]
                vz[vz == 0] = 1.0
                xp = vx / vz
                yp = vy / vz
                
                ax_x.scatter(x_pos * 1000, xp * 1000, color='#60A5FA', alpha=0.6, edgecolors='none', s=6)
                ax_x.set_xlabel("X (mm)", color='#F3F4F6')
                ax_x.set_ylabel("X' (mrad)", color='#F3F4F6')
                ax_x.set_title("Space X - X'" if self.language == "EN" else "Espaço X - X'", color='#3B82F6')
                
                ax_y.scatter(y_pos * 1000, yp * 1000, color='#34D399', alpha=0.6, edgecolors='none', s=6)
                ax_y.set_xlabel("Y (mm)", color='#F3F4F6')
                ax_y.set_ylabel("Y' (mrad)", color='#F3F4F6')
                ax_y.set_title("Space Y - Y'" if self.language == "EN" else "Espaço Y - Y'", color='#3B82F6')
                
                self.canvas_phase.figure.tight_layout()
                self.canvas_phase.draw()
                
                # --- Emittance Distribution Histogram ---
                x_mean = np.mean(x_pos)
                xp_mean = np.mean(xp)
                dx_part = x_pos - x_mean
                dxp_part = xp - xp_mean
                
                x2_mean = np.mean(dx_part**2)
                xp2_mean = np.mean(dxp_part**2)
                xxp_mean = np.mean(dx_part * dxp_part)
                eps_rms = np.sqrt(max(1e-20, x2_mean * xp2_mean - xxp_mean**2))
                
                beta = x2_mean / eps_rms
                alpha = -xxp_mean / eps_rms
                gamma = xp2_mean / eps_rms
                
                single_emitt = gamma * dx_part**2 + 2.0 * alpha * dx_part * dxp_part + beta * dxp_part**2
                
                self.canvas_emittance.axes.cla()
                self.canvas_emittance.axes.set_facecolor(cols["bg"])
                self.canvas_emittance.axes.hist(single_emitt * 1e6, bins=50, color='#F59E0B', edgecolor='#FCD34D', alpha=0.8)
                self.canvas_emittance.axes.set_xlabel("Single-particle Emittance (mm·mrad)" if self.language == "EN" else "Emitância Individual (mm·mrad)", color=cols["fg"])
                self.canvas_emittance.axes.set_ylabel("Count" if self.language == "EN" else "Contagem", color=cols["fg"])
                self.canvas_emittance.axes.set_title("Emittance Distribution" if self.language == "EN" else "Distribuição de Emitância", color=cols["title"])
                self.canvas_emittance.axes.grid(True, color=cols["grid"])
                self.canvas_emittance.draw()
                
                # Update text metrics
                params = self.read_all_scenario_parameters()
                n_part_gen = sum(beam.get("particulas", 0) for beam in params.get("beams", []))
                if n_part_gen <= 0: n_part_gen = 50000
                trans = (len(data) / n_part_gen) * 100.0
                
                # FWHM calculation
                if len(times) > 5:
                    hist, bin_edges = np.histogram(times, bins=50)
                    max_val = np.max(hist)
                    if max_val > 0:
                        half_max = max_val / 2.0
                        indices = np.where(hist >= half_max)[0]
                        if len(indices) >= 2:
                            fwhm_s = bin_edges[indices[-1]] - bin_edges[indices[0]]
                        else:
                            fwhm_s = np.std(times) * 2.355
                    else:
                        fwhm_s = np.std(times) * 2.355
                else:
                    fwhm_s = 0.0
                
                self.table_metrics.setItem(0, 1, QTableWidgetItem(f"{trans:.2f} %"))
                self.table_metrics.setItem(1, 1, QTableWidgetItem(f"{eps_rms:.4e}"))
                self.table_metrics.setItem(2, 1, QTableWidgetItem(f"{fwhm_s*1e9:.2f} ns"))
                
        except Exception as e:
            print("Erro ao atualizar os gráficos de diagnósticos:", e)
                
        # 2. Slice potential and charge densities 2D contours
        orient = self.cb_plane_orient.currentIndex()
        map_type = self.cb_map_2d.currentIndex()
        coord_val = 0.0
        try:
            coord_val = float(self.txt_plane_z.text())
        except ValueError:
            pass
            
        V_matrix = None
        rho_matrix = None
        zs = None
        xs = None
        
        # If user wants potential or default charge density file slice
        if map_type == 0:
            if os.path.exists(pot_field_path) and os.path.exists(rho_field_path):
                try:
                    zs, xs, V_matrix = self.load_grid_slice(pot_field_path, 3, plane_orient=orient, coord_val=coord_val)
                    _, _, rho_matrix = self.load_grid_slice(rho_field_path, 3, plane_orient=orient, coord_val=coord_val)
                except Exception as e:
                    print("Error slicing field files:", e)
        else:
            # Slicing from trajectories (Rho or J)
            trajectories = self.simulation_cache.get("trajectories")
            if trajectories is None and os.path.exists(traj_path):
                trajectories = parse_trajectories(traj_path)
                self.simulation_cache["trajectories"] = trajectories
                
            if trajectories:
                try:
                    # Check potential field mapping for V contours overlay if exists
                    if os.path.exists(pot_field_path):
                        try:
                            zs, xs, V_matrix = self.load_grid_slice(pot_field_path, 3, plane_orient=orient, coord_val=coord_val)
                        except Exception:
                            pass
                            
                    params = self.read_all_scenario_parameters()
                    h = params.get("h", 0.001)
                    xmin = params.get("xmin", -0.05)
                    xmax = params.get("xmax", 0.05)
                    ymin = params.get("ymin", -0.05)
                    ymax = params.get("ymax", 0.05)
                    zmin = params.get("zmin", 0.0)
                    zmax = params.get("zmax", 0.35)
                    
                    tol = 2.0 * h
                    
                    coord_h = []
                    coord_v = []
                    weights = []
                    
                    if orient == 0:  # XY (Z = coord)
                        h_range = [xmin, xmax]
                        v_range = [ymin, ymax]
                        nbins_h = max(10, int((xmax - xmin) / h))
                        nbins_v = max(10, int((ymax - ymin) / h))
                    elif orient == 1:  # XZ (Y = coord)
                        h_range = [zmin, zmax]
                        v_range = [xmin, xmax]
                        nbins_h = max(10, int((zmax - zmin) / h))
                        nbins_v = max(10, int((xmax - xmin) / h))
                    else:  # YZ (X = coord)
                        h_range = [zmin, zmax]
                        v_range = [ymin, ymax]
                        nbins_h = max(10, int((zmax - zmin) / h))
                        nbins_v = max(10, int((ymax - ymin) / h))
                        
                    for traj in trajectories:
                        pts = traj["points"]
                        curr = traj["curr"]
                        for k in range(len(pts) - 1):
                            t1, x1, y1, z1 = pts[k]
                            t2, x2, y2, z2 = pts[k+1]
                            dt = t2 - t1
                            if dt <= 0:
                                continue
                            
                            x_mid = (x1 + x2) / 2.0
                            y_mid = (y1 + y2) / 2.0
                            z_mid = (z1 + z2) / 2.0
                            
                            in_slice = False
                            if orient == 0:  # XY
                                if abs(z_mid - coord_val) < tol:
                                    in_slice = True
                                    ch, cv = x_mid, y_mid
                            elif orient == 1:  # XZ
                                if abs(y_mid - coord_val) < tol:
                                    in_slice = True
                                    ch, cv = z_mid, x_mid
                            else:  # YZ
                                if abs(x_mid - coord_val) < tol:
                                    in_slice = True
                                    ch, cv = z_mid, y_mid
                                    
                            if in_slice:
                                coord_h.append(ch)
                                coord_v.append(cv)
                                if map_type == 1: # Rho
                                    weights.append(curr * dt)
                                else: # J
                                    ds = np.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
                                    weights.append(curr * ds)
                                    
                    if len(coord_h) > 0:
                        counts, h_edges, v_edges = np.histogram2d(
                            coord_h, coord_v,
                            bins=[nbins_h, nbins_v],
                            range=[h_range, v_range],
                            weights=weights
                        )
                        dh = (h_range[1] - h_range[0]) / nbins_h
                        dv = (v_range[1] - v_range[0]) / nbins_v
                        vol = dh * dv * (2.0 * tol)
                        rho_matrix = (counts / vol).T
                        
                        zs = (h_edges[:-1] + h_edges[1:]) / 2.0
                        xs = (v_edges[:-1] + v_edges[1:]) / 2.0
                except Exception as e:
                    print(f"Error calculating trajectory density map: {e}")
                    
        # 3. Draw 2D contours
        if zs is not None and xs is not None:
            try:
                cols = self.get_theme_colors()
                self.canvas_contours.axes.cla()
                self.canvas_contours.figure.clear()
                self.canvas_contours.axes = self.canvas_contours.figure.add_subplot(111)
                
                self.canvas_contours.axes.set_facecolor(cols["bg"])
                self.canvas_contours.axes.set_aspect("equal", adjustable="box")
                
                self.canvas_contours.axes.spines['bottom'].set_color(cols["grid"])
                self.canvas_contours.axes.spines['top'].set_color(cols["grid"])
                self.canvas_contours.axes.spines['left'].set_color(cols["grid"])
                self.canvas_contours.axes.spines['right'].set_color(cols["grid"])
                self.canvas_contours.axes.tick_params(colors=cols["fg"], which='both')
                self.canvas_contours.axes.xaxis.label.set_color(cols["fg"])
                self.canvas_contours.axes.yaxis.label.set_color(cols["fg"])
                self.canvas_contours.axes.title.set_color(cols["title"])
                
                h_val = 0.001
                try:
                    h_val = float(self.txt_h.text())
                except Exception:
                    pass
                
                orig_zs = np.array(zs, copy=True)
                orig_xs = np.array(xs, copy=True)
                
                if V_matrix is not None:
                    zs, xs, V_matrix = ensure_2d_grid_at_least_2x2(orig_zs, orig_xs, V_matrix, h_val)
                if rho_matrix is not None:
                    _, _, rho_matrix = ensure_2d_grid_at_least_2x2(orig_zs, orig_xs, rho_matrix, h_val)
                    if V_matrix is None:
                        zs, xs, _ = ensure_2d_grid_at_least_2x2(orig_zs, orig_xs, rho_matrix, h_val)
                
                Z_grid, X_grid = np.meshgrid(zs * 1000, xs * 1000) # scale to mm
                
                im = None
                if rho_matrix is not None:
                    im = self.canvas_contours.axes.pcolormesh(
                        Z_grid, X_grid, rho_matrix, cmap='plasma', shading='auto', alpha=0.6
                    )
                
                if V_matrix is not None:
                    contours = self.canvas_contours.axes.contour(
                        Z_grid, X_grid, V_matrix, levels=15, colors=cols["contour_color"], linewidths=0.7, alpha=0.8
                    )
                    self.canvas_contours.axes.clabel(contours, inline=True, fontsize=8, fmt="%d V", colors=cols["fg"])
                
                if orient == 0:
                    xlabel = "X (mm)"
                    ylabel = "Y (mm)"
                    t_title = "XY - Equipotentials (V)" if self.language == "EN" else "XY - Equipotenciais (V)"
                elif orient == 1:
                    xlabel = "Z (mm)"
                    ylabel = "X (mm)"
                    t_title = "XZ - Equipotentials (V)" if self.language == "EN" else "XZ - Equipotenciais (V)"
                else:
                    xlabel = "Z (mm)"
                    ylabel = "Y (mm)"
                    t_title = "YZ - Equipotentials (V)" if self.language == "EN" else "YZ - Equipotenciais (V)"
                    
                self.canvas_contours.axes.set_xlabel(xlabel, color=cols["fg"])
                self.canvas_contours.axes.set_ylabel(ylabel, color=cols["fg"])
                self.canvas_contours.axes.set_title(t_title, color=cols["title"])
                self.canvas_contours.axes.grid(True, color=cols["grid"])
                
                if im is not None:
                    if map_type == 0:
                        label_text = "Charge Density (C/m³)" if self.language == "EN" else "Densidade de Carga (C/m³)"
                    elif map_type == 1:
                        label_text = "Rho (C/m³)"
                    else:
                        label_text = "J (A/m²)"
                        
                    cbar = self.canvas_contours.figure.colorbar(im, ax=self.canvas_contours.axes, orientation='vertical')
                    cbar.set_label(label_text, color=cols["fg"])
                    cbar.ax.yaxis.set_tick_params(color=cols["fg"], labelcolor=cols["fg"])
                    cbar.ax.tick_params(colors=cols["fg"])
                    cbar.outline.set_edgecolor(cols["cbar_edge"])
                    
                self.canvas_contours.figure.tight_layout()
                self.canvas_contours.draw()
            except Exception as e:
                print("Error drawing 2D contour map:", e)

    def load_grid_slice(self, filepath, val_col_idx, plane_orient=1, coord_val=0.0):
        # plane_orient: 0 = XY (Z = coord), 1 = XZ (Y = coord), 2 = YZ (X = coord)
        filename = os.path.basename(filepath)
        cache_key = None
        if "potential_field" in filename:
            cache_key = "potential_field"
        elif "charge_density" in filename:
            cache_key = "charge_density"
        elif "trajectory_density" in filename:
            cache_key = "trajectory_density"
            
        raw = None
        if cache_key and cache_key in self.simulation_cache:
            raw = self.simulation_cache[cache_key]
        else:
            if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
                return None, None, None
            try:
                raw = load_numpy_file_safe(filepath)
                if raw is not None and cache_key:
                    self.simulation_cache[cache_key] = raw
            except Exception as e:
                print(f"Error loading grid slice from {filepath}: {e}")
                return None, None, None
                
        try:
            if raw is None or raw.size == 0:
                return None, None, None
            if raw.ndim == 1:
                raw = np.expand_dims(raw, axis=0)
            
            # The columns are: 0 = X, 1 = Y, 2 = Z
            if plane_orient == 0:  # XY (Z = coord)
                zs = raw[:, 2]
                unique_zs = np.unique(zs)
                if len(unique_zs) == 0:
                    return None, None, None
                z_slice = unique_zs[np.argmin(np.abs(unique_zs - coord_val))]
                mask = raw[:, 2] == z_slice
                filtered = raw[mask]
                
                xs = np.unique(filtered[:, 0])
                ys = np.unique(filtered[:, 1])
                
                grid_val = np.zeros((len(ys), len(xs)))
                x_map = {x: i for i, x in enumerate(xs)}
                y_map = {y: i for i, y in enumerate(ys)}
                
                for row in filtered:
                    x_idx = x_map[row[0]]
                    y_idx = y_map[row[1]]
                    grid_val[y_idx, x_idx] = row[val_col_idx]
                return xs, ys, grid_val
                
            elif plane_orient == 1:  # XZ (Y = coord)
                ys = raw[:, 1]
                unique_ys = np.unique(ys)
                if len(unique_ys) == 0:
                    return None, None, None
                y_slice = unique_ys[np.argmin(np.abs(unique_ys - coord_val))]
                mask = raw[:, 1] == y_slice
                filtered = raw[mask]
                
                xs = np.unique(filtered[:, 0])
                zs = np.unique(filtered[:, 2])
                
                grid_val = np.zeros((len(xs), len(zs)))
                x_map = {x: i for i, x in enumerate(xs)}
                z_map = {z: i for i, z in enumerate(zs)}
                
                for row in filtered:
                    x_idx = x_map[row[0]]
                    z_idx = z_map[row[2]]
                    grid_val[x_idx, z_idx] = row[val_col_idx]
                return zs, xs, grid_val
                
            else:  # YZ (X = coord)
                xs = raw[:, 0]
                unique_xs = np.unique(xs)
                if len(unique_xs) == 0:
                    return None, None, None
                x_slice = unique_xs[np.argmin(np.abs(unique_xs - coord_val))]
                mask = raw[:, 0] == x_slice
                filtered = raw[mask]
                
                ys = np.unique(filtered[:, 1])
                zs = np.unique(filtered[:, 2])
                
                grid_val = np.zeros((len(ys), len(zs)))
                y_map = {y: i for i, y in enumerate(ys)}
                z_map = {z: i for i, z in enumerate(zs)}
                
                for row in filtered:
                    y_idx = y_map[row[1]]
                    z_idx = z_map[row[2]]
                    grid_val[y_idx, z_idx] = row[val_col_idx]
                return zs, ys, grid_val
        except Exception as e:
            print(f"Error slicing grid data: {e}")
            return None, None, None

    def salvar_projeto(self):
        file_path, _ = QFileDialog.getSaveFileName(self, self.tr("save_title"), "", "JSON Files (*.json)")
        if not file_path:
            return
            
        try:
            # Clean geometries and bfield path to use relative ./data/ format
            clean_geoms = []
            for geom in self.geometries:
                g_copy = geom.copy()
                g_copy["file_path"] = f"./data/{os.path.basename(geom['file_path'])}"
                clean_geoms.append(g_copy)
                
            bfield_clean = f"./data/{os.path.basename(self.txt_bfield_path.text())}" if self.txt_bfield_path.text() else ""
            
            project_data = {
                "h": self.txt_h.text(),
                "zmax": self.txt_zmax.text(),
                "rmax": self.txt_rmax.text(),
                "bfield_enabled": self.chk_bfield.isChecked(),
                "bfield_path": bfield_clean,
                "regime": self.cb_regime.currentText(),
                "dt": self.txt_dt.text(),
                "tfinal": self.txt_tfinal.text(),
                "w_trans": self.txt_w_trans.text(),
                "w_emit": self.txt_w_emit.text(),
                "w_tof": self.txt_w_tof.text(),
                "max_iter": self.txt_max_iter.text(),
                "threads": self.spin_threads.value(),
                "dump_potential": self.chk_dump_potential.isChecked(),
                "dump_charge_density": self.chk_dump_charge.isChecked(),
                "dump_trajectory_density": self.chk_dump_trajdens.isChecked(),
                "dump_tof": self.chk_dump_tof.isChecked(),
                "geometries": clean_geoms,
                "beams": self.beams,
                "tof_style": self.cb_tof_style.currentIndex(),
                "plane_z": self.txt_plane_z.text(),
                "plane_mode": self.cb_plane_mode.currentIndex(),
                "plane_orient": self.cb_plane_orient.currentIndex(),
                "map_2d": self.cb_map_2d.currentIndex()
            }
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(project_data, f, indent=4)
                
            self.geometries = clean_geoms
            self.txt_bfield_path.setText(bfield_clean)
            self.reload_geometries_table()
                
            self.lbl_status.setText(f"{self.tr('status_saved')} {os.path.basename(file_path)}")
            QMessageBox.information(self, self.tr("save_success_title"), self.tr("save_success_msg").format(file_path))
        except Exception as e:
            QMessageBox.critical(self, self.tr("save_error_title"), self.tr("save_error_msg").format(e))

    def get_theme_colors(self):
        if self.theme_mode == "dark":
            return {
                "bg": '#0B0F19',
                "fg": '#F3F4F6',
                "title": '#3B82F6',
                "grid": '#1F2937',
                "legend_bg": '#111827',
                "legend_edge": '#1F2937',
                "legend_text": '#F3F4F6',
                "text_muted": '#9CA3AF',
                "contour_color": '#E5E7EB',
                "cbar_text": 'white',
                "cbar_edge": '#1F2937'
            }
        else:
            return {
                "bg": '#FFFFFF',
                "fg": '#000000',
                "title": '#000000',
                "grid": '#D1D5DB',
                "legend_bg": '#FFFFFF',
                "legend_edge": '#D1D5DB',
                "legend_text": '#000000',
                "text_muted": '#1F2937',
                "contour_color": '#000000',
                "cbar_text": '#000000',
                "cbar_edge": '#D1D5DB'
            }

    def toggle_theme(self):
        if self.theme_mode == "dark":
            self.theme_mode = "light"
        else:
            self.theme_mode = "dark"
        
        if self.theme_mode == "dark":
            self.setStyleSheet(STYLESHEET)
            self.lbl_status.setStyleSheet("color: #9CA3AF; padding: 2px;")
            self.chk_bfield.setStyleSheet("color: #F3F4F6;")
            self.chk_dump_potential.setStyleSheet("color: #F3F4F6;")
            self.chk_dump_charge.setStyleSheet("color: #F3F4F6;")
            self.chk_dump_trajdens.setStyleSheet("color: #F3F4F6;")
            self.chk_dump_tof.setStyleSheet("color: #F3F4F6;")
            self.beam_summary.setStyleSheet("QTextEdit { background-color: #111827; color: #F3F4F6; border: 1px solid #1F2937; font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px; padding: 10px; }")
            self.combo_lang.setStyleSheet("QComboBox { background-color: #1F2937; border: 1px solid #3B82F6; border-radius: 4px; color: #F3F4F6; padding: 4px 8px; font-weight: bold; }")
            self.btn_theme.setStyleSheet("QPushButton { background-color: #1F2937; border: 1px solid #3B82F6; border-radius: 4px; color: #F3F4F6; padding: 4px 8px; font-weight: bold; }")
        else:
            self.setStyleSheet(STYLESHEET_LIGHT)
            self.lbl_status.setStyleSheet("color: #374151; padding: 2px;")
            self.chk_bfield.setStyleSheet("color: #111827;")
            self.chk_dump_potential.setStyleSheet("color: #111827;")
            self.chk_dump_charge.setStyleSheet("color: #111827;")
            self.chk_dump_trajdens.setStyleSheet("color: #111827;")
            self.chk_dump_tof.setStyleSheet("color: #111827;")
            self.beam_summary.setStyleSheet("QTextEdit { background-color: #FFFFFF; color: #111827; border: 1px solid #D1D5DB; font-family: 'Segoe UI', Arial, sans-serif; font-size: 12px; padding: 10px; }")
            self.combo_lang.setStyleSheet("QComboBox { background-color: #FFFFFF; border: 1px solid #2563EB; border-radius: 4px; color: #111827; padding: 4px 8px; font-weight: bold; }")
            self.btn_theme.setStyleSheet("QPushButton { background-color: #FFFFFF; border: 1px solid #2563EB; border-radius: 4px; color: #111827; padding: 4px 8px; font-weight: bold; }")
            
        # Retranslate theme button text
        theme_text = self.tr("btn_theme_dark") if self.theme_mode == "light" else self.tr("btn_theme_light")
        self.btn_theme.setText(theme_text)
        
        # Update 3D widget
        if hasattr(self, "pyvista_widget") and self.pyvista_widget:
            self.pyvista_widget.set_theme_mode(self.theme_mode)
            
        # Update Matplotlib plots
        self.update_plots_theme()

    def apply_theme_to_figure(self, fig):
        cols = self.get_theme_colors()
        fig.set_facecolor('#F3F4F6' if self.theme_mode == 'light' else '#111827')
        for ax in fig.get_axes():
            ax.set_facecolor(cols["bg"])
            for spine in ax.spines.values():
                spine.set_color(cols["grid"])
            ax.tick_params(colors=cols["fg"], which='both')
            ax.xaxis.label.set_color(cols["fg"])
            ax.yaxis.label.set_color(cols["fg"])
            if ax.title:
                ax.title.set_color(cols["title"])
            
            # Style legend
            legend = ax.get_legend()
            if legend:
                legend.get_frame().set_facecolor(cols["legend_bg"])
                legend.get_frame().set_edgecolor(cols["legend_edge"])
                for text in legend.get_texts():
                    text.set_color(cols["legend_text"])
                try:
                    title = legend.get_title()
                    if title:
                        title.set_color(cols["legend_text"])
                except Exception:
                    pass
            
            # Style offset texts (scientific notation multiplier like 1e-6)
            try:
                ax.xaxis.get_offset_text().set_color(cols["fg"])
            except Exception:
                pass
            try:
                ax.yaxis.get_offset_text().set_color(cols["fg"])
            except Exception:
                pass
            
            # Style colorbars
            cbar = getattr(ax, '_colorbar', None)
            if cbar is None:
                cbar = getattr(ax, 'colorbar', None)
            if cbar is not None:
                try:
                    label = cbar.ax.get_ylabel()
                    if label:
                        cbar.set_label(label, color=cols["fg"])
                except Exception:
                    pass
                try:
                    label = cbar.ax.get_xlabel()
                    if label:
                        cbar.set_label(label, color=cols["fg"])
                except Exception:
                    pass
                try:
                    cbar.ax.xaxis.set_tick_params(color=cols["fg"], labelcolor=cols["fg"])
                except Exception:
                    pass
                try:
                    cbar.ax.yaxis.set_tick_params(color=cols["fg"], labelcolor=cols["fg"])
                except Exception:
                    pass
                try:
                    cbar.outline.set_edgecolor(cols["cbar_edge"])
                except Exception:
                    pass
            
            # Style inner texts
            for txt in ax.texts:
                txt.set_color(cols["text_muted"])

    def update_plots_theme(self):
        canvases = [
            self.canvas_convergence,
            self.canvas_tof,
            self.canvas_profile,
            self.canvas_contours,
            self.canvas_phase,
            self.canvas_emittance
        ]
        for canvas in canvases:
            if canvas:
                self.apply_theme_to_figure(canvas.figure)
                canvas.draw_idle()

    def tr(self, key):
        return TRANSLATIONS[self.language].get(key, key)

    def change_language(self, index):
        self.language = "PT" if index == 0 else "EN"
        self.retranslate_ui()

    def retranslate_ui(self):
        # Window Title
        self.setWindowTitle(self.tr("win_title"))
        
        # Menus
        self.menu_arquivo.setTitle(self.tr("menu_file"))
        self.action_abrir.setText(self.tr("action_open"))
        self.action_salvar.setText(self.tr("action_save"))
        self.action_sair.setText(self.tr("action_exit"))
        
        self.menu_testes.setTitle(self.tr("menu_tests"))
        self.action_run_tests.setText(self.tr("action_run_tests"))
        
        self.menu_ajuda.setTitle(self.tr("menu_help"))
        self.action_manual.setText(self.tr("action_manual"))
        self.action_sobre.setText(self.tr("action_about"))
        
        # Tabs
        self.tabs.setTabText(0, self.tr("tab_settings"))
        self.tabs.setTabText(1, self.tr("tab_solids"))
        self.tabs.setTabText(2, self.tr("tab_simulate"))
        self.tabs.setTabText(3, self.tr("tab_diagnostics"))
        
        # Tab 1: Settings & Beams
        self.mesh_box.setTitle(self.tr("mesh_box"))
        self.lbl_h.setText(self.tr("lbl_h"))
        self.lbl_zmax.setText(self.tr("lbl_zmax"))
        self.lbl_rmax.setText(self.tr("lbl_rmax"))
        self.lbl_bfield.setText(self.tr("lbl_bfield"))
        self.chk_bfield.setText(self.tr("chk_bfield"))
        self.btn_browse_bfield.setText(self.tr("btn_browse"))
        
        self.regime_box.setTitle(self.tr("regime_box"))
        self.lbl_regime.setText(self.tr("lbl_regime"))
        self.lbl_dt.setText(self.tr("lbl_dt"))
        self.lbl_tfinal.setText(self.tr("lbl_tfinal"))
        
        self.beams_box.setTitle(self.tr("beams_box"))
        self.btn_add_beam.setText(self.tr("btn_add_beam"))
        self.btn_remove_beam.setText(self.tr("btn_remove_beam"))
        self.btn_import_beams.setText(self.tr("btn_import_beams"))
        
        self.group_beam_editor.setTitle(self.tr("beam_editor_box"))
        self.update_beam_summary()
        
        # Tab 2: Workstation 3D & Solids
        self.solids_box.setTitle(self.tr("solids_box"))
        self.btn_add_solid.setText(self.tr("btn_add_solid"))
        self.btn_remove_solid.setText(self.tr("btn_remove_solid"))
        
        self.group_editor.setTitle(self.tr("geom_editor_box"))
        self.lbl_editor_name.setText(self.tr("lbl_editor_name"))
        self.lbl_editor_file.setText(self.tr("lbl_editor_file"))
        self.lbl_editor_btype.setText(self.tr("lbl_editor_btype"))
        self.lbl_editor_voltage.setText(self.tr("lbl_editor_voltage"))
        self.lbl_editor_translation.setText(self.tr("lbl_editor_translation"))
        self.lbl_editor_scale.setText(self.tr("lbl_editor_scale"))
        self.lbl_editor_layer.setText(self.tr("lbl_editor_layer"))
        self.lbl_editor_mapping.setText(self.tr("lbl_editor_mapping"))
        self.btn_apply_edits.setText(self.tr("btn_apply_edits"))
        
        self.lbl_view_mode.setText(self.tr("lbl_view_mode"))
        self.lbl_traj_color.setText(self.tr("lbl_traj_color"))
        self.btn_load_to_visualizer.setText(self.tr("btn_reload_3d"))
        
        self.group_pic_anim.setTitle(self.tr("pic_anim_box"))
        self.btn_play_pic.setText(self.tr("btn_pause_pic") if self.animation_timer.isActive() else self.tr("btn_play_pic"))
        
        # Tab 3: Simulate & Optimize
        self.actions_box.setTitle(self.tr("actions_box"))
        self.btn_start_sim.setText(self.tr("btn_start_sim"))
        self.btn_start_opt.setText(self.tr("btn_start_opt"))
        self.btn_stop_opt.setText(self.tr("btn_stop_opt"))
        self.btn_close_sim.setText(self.tr("btn_close_sim"))
        
        self.opt_params_box.setTitle(self.tr("opt_params_box"))
        self.lbl_opt_w_trans.setText(self.tr("lbl_opt_w_trans"))
        self.lbl_opt_w_emit.setText(self.tr("lbl_opt_w_emit"))
        self.lbl_opt_w_tof.setText(self.tr("lbl_opt_w_tof"))
        self.lbl_opt_max_iter.setText(self.tr("lbl_opt_max_iter"))
        
        self.dumps_box.setTitle(self.tr("dumps_box"))
        self.lbl_threads.setText(self.tr("lbl_threads"))
        self.chk_dump_potential.setText(self.tr("chk_dump_potential"))
        self.chk_dump_charge.setText(self.tr("chk_dump_charge"))
        self.chk_dump_trajdens.setText(self.tr("chk_dump_trajdens"))
        self.chk_dump_tof.setText(self.tr("chk_dump_tof"))
        
        self.console_box.setTitle(self.tr("console_box"))
        
        # Tab 4: Advanced Diagnostics
        self.diag_ctrl_box.setTitle(self.tr("diag_ctrl_box"))
        self.lbl_plane_mode.setText(self.tr("lbl_plane_mode"))
        self.lbl_plane_z.setText(self.tr("lbl_plane_z"))
        self.btn_clip_plane.setText(self.tr("btn_clip_plane"))
        
        self.tof_opt_box.setTitle(self.tr("tof_opt_box"))
        self.lbl_tof_style.setText(self.tr("lbl_tof_style"))
        self.btn_export_tof.setText(self.tr("btn_export_tof"))
        
        self.metrics_box.setTitle(self.tr("metrics_box"))
        self.btn_apply_pic_suggestion.setText(self.tr("btn_apply_pic_suggestion"))
        
        # Update PIC suggestion text dynamically if active
        if hasattr(self, "_suggested_T") and hasattr(self, "_suggested_dt") and self.lbl_pic_suggestion.text():
            msg_pt = f"Sugestão PIC: T_sug = {self._suggested_T:.2e} s | dt_sug = {self._suggested_dt:.2e} s"
            msg_en = f"PIC Suggestion: T_sug = {self._suggested_T:.2e} s | dt_sug = {self._suggested_dt:.2e} s"
            self.lbl_pic_suggestion.setText(msg_pt if self.language == "PT" else msg_en)
        
        # Table Headers
        self.table_beams.setHorizontalHeaderLabels(self.tr("beam_headers"))
        self.table_geoms.setHorizontalHeaderLabels(self.tr("geom_headers"))
        self.table_metrics.setHorizontalHeaderLabels(self.tr("metric_headers"))
        
        # ComboBox items translating (preserving selection indexes)
        self.cb_plane_mode.blockSignals(True)
        idx_plane = self.cb_plane_mode.currentIndex()
        self.cb_plane_mode.clear()
        self.cb_plane_mode.addItems([self.tr("plane_auto"), self.tr("plane_arbitrary")])
        self.cb_plane_mode.setCurrentIndex(idx_plane if idx_plane >= 0 else 0)
        self.cb_plane_mode.blockSignals(False)
        
        self.lbl_plane_orient.setText(self.tr("lbl_plane_orient"))
        self.cb_plane_orient.blockSignals(True)
        idx_orient = self.cb_plane_orient.currentIndex()
        self.cb_plane_orient.clear()
        self.cb_plane_orient.addItems([self.tr("plane_xy"), self.tr("plane_xz"), self.tr("plane_yz")])
        self.cb_plane_orient.setCurrentIndex(idx_orient if idx_orient >= 0 else 0)
        self.cb_plane_orient.blockSignals(False)

        self.lbl_map_2d.setText(self.tr("lbl_map_2d"))
        self.cb_map_2d.blockSignals(True)
        idx_map = self.cb_map_2d.currentIndex()
        self.cb_map_2d.clear()
        self.cb_map_2d.addItems([self.tr("map_potential"), self.tr("map_rho"), self.tr("map_j")])
        self.cb_map_2d.setCurrentIndex(idx_map if idx_map >= 0 else 0)
        self.cb_map_2d.blockSignals(False)
        
        self.cb_view_mode.blockSignals(True)
        idx_view = self.cb_view_mode.currentIndex()
        self.cb_view_mode.clear()
        self.cb_view_mode.addItems([self.tr("view_persp"), self.tr("view_zx"), self.tr("view_zy"), self.tr("view_xy")])
        self.cb_view_mode.setCurrentIndex(idx_view if idx_view >= 0 else 0)
        self.cb_view_mode.blockSignals(False)
        
        self.cb_traj_color.blockSignals(True)
        idx_traj = self.cb_traj_color.currentIndex()
        self.cb_traj_color.clear()
        self.cb_traj_color.addItems([self.tr("color_species"), self.tr("color_mass"), self.tr("color_charge"), self.tr("color_energy"), self.tr("color_current")])
        self.cb_traj_color.setCurrentIndex(idx_traj if idx_traj >= 0 else 0)
        self.cb_traj_color.blockSignals(False)
        
        self.editor_mapping.blockSignals(True)
        idx_mapping = self.editor_mapping.currentIndex()
        self.editor_mapping.clear()
        self.editor_mapping.addItems([self.tr("dxf_mapping_rotz"), self.tr("dxf_mapping_linear")])
        self.editor_mapping.setCurrentIndex(idx_mapping if idx_mapping >= 0 else 0)
        self.editor_mapping.blockSignals(False)
        
        self.cb_tof_style.blockSignals(True)
        idx_tof = self.cb_tof_style.currentIndex()
        self.cb_tof_style.clear()
        self.cb_tof_style.addItems([self.tr("style_bars"), self.tr("style_line"), self.tr("style_scatter")])
        self.cb_tof_style.setCurrentIndex(idx_tof if idx_tof >= 0 else 0)
        self.cb_tof_style.blockSignals(False)
        
        # Tooltips
        self.txt_h.setToolTip(self.tr("tooltip_h"))
        self.txt_zmax.setToolTip(self.tr("tooltip_zmax"))
        self.txt_rmax.setToolTip(self.tr("tooltip_rmax"))
        self.chk_bfield.setToolTip(self.tr("tooltip_bfield"))
        self.cb_regime.setToolTip(self.tr("tooltip_regime"))
        self.txt_dt.setToolTip(self.tr("tooltip_dt"))
        self.txt_tfinal.setToolTip(self.tr("tooltip_tfinal"))
        
        # Status
        if self.lbl_status.text() in ["Pronto.", "Ready."]:
            self.lbl_status.setText(self.tr("status_ready"))
            
        # Re-populate metrics names in self.table_metrics
        self.table_metrics.setItem(0, 0, QTableWidgetItem(self.tr("metric_transmission")))
        self.table_metrics.setItem(1, 0, QTableWidgetItem(self.tr("metric_emittance")))
        self.table_metrics.setItem(2, 0, QTableWidgetItem(self.tr("metric_tof")))
        
        # Diagnostics tabs
        self.diag_tabs.setTabText(0, self.tr("sub_tab_tof"))
        self.diag_tabs.setTabText(1, self.tr("sub_tab_profile"))
        self.diag_tabs.setTabText(2, self.tr("sub_tab_contours"))
        self.diag_tabs.setTabText(3, self.tr("sub_tab_phase"))
        self.diag_tabs.setTabText(4, self.tr("sub_tab_emittance"))
        
        # Retranslate theme button text
        theme_text = self.tr("btn_theme_dark") if self.theme_mode == "light" else self.tr("btn_theme_light")
        self.btn_theme.setText(theme_text)

    def show_help_dialog(self):
        dialog = HelpDialog(self, self.language)
        dialog.exec()

    def show_about_dialog(self):
        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle("About IBSimion" if self.language == "EN" else "Sobre o IBSimion")
        
        # Style the QMessageBox explicitly to force light background and dark text
        msg.setStyleSheet("""
            QDialog {
                background-color: #F3F4F6;
            }
            QMessageBox {
                background-color: #F3F4F6;
            }
            QLabel {
                color: #111827;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }
            QPushButton {
                background-color: #E5E7EB;
                color: #111827;
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D1D5DB;
            }
        """)
        
        if self.language == "EN":
            texto_sobre = (
                "<div style='color: #111827; background-color: #F3F4F6;'>"
                "<h2 style='color: #1F2937;'>About IBSimion</h2>"
                "<p><b>App:</b> IBSimion (v2.0.1.e3l)</p>"
                "<p><b>Status:</b> Stable Beta Version</p>"
                "<p><b>Dev:</b> IBSimion Team</p>"
                "<p><b>Description:</b> Advanced scientific platform for modeling, potential visualization, and particle trajectory simulation.</p>"
                "<p><b>Year:</b> 2026</p>"
                "</div>"
            )
        else:
            texto_sobre = (
                "<div style='color: #111827; background-color: #F3F4F6;'>"
                "<h2 style='color: #1F2937;'>Sobre o IBSimion</h2>"
                "<p><b>App:</b> IBSimion (v2.0.1.e3l)</p>"
                "<p><b>Status:</b> Versão Beta Estável</p>"
                "<p><b>Dev:</b> IBSimion Team</p>"
                "<p><b>Descrição:</b> Plataforma científica avançada para modelagem, visualização de potenciais e simulação de trajetórias de partículas.</p>"
                "<p><b>Ano:</b> 2026</p>"
                "</div>"
            )
        msg.setText(texto_sobre)
        msg.exec()

    def apply_clipping_plane_diagnostics(self):
        self.calculate_diagnostics_plots()
        try:
            coord_val = float(self.txt_plane_z.text())
            orient = self.cb_plane_orient.currentIndex()
            if orient == 0:  # XY (Z = coord)
                normal = (0, 0, -1)
                origin = (0, 0, coord_val)
            elif orient == 1:  # XZ (Y = coord)
                normal = (0, -1, 0)
                origin = (0, coord_val, 0)
            else:  # YZ (X = coord)
                normal = (-1, 0, 0)
                origin = (coord_val, 0, 0)
            self.pyvista_widget.apply_clipping_plane(coord_val, normal=normal, origin=origin)
            self.lbl_status.setText(f"Plano de corte aplicado em {self.cb_plane_orient.currentText()} = {coord_val} m" if self.language == "PT" else f"Clipping plane applied at {self.cb_plane_orient.currentText()} = {coord_val} m")
        except ValueError:
            QMessageBox.warning(self, "Valor Inválido" if self.language == "PT" else "Invalid Value",
                                "Coordenada do plano inválida" if self.language == "PT" else "Invalid plane coordinate")

    def calculate_pic_suggestions(self):
        tof_data = self.simulation_cache.get("tof")
        if tof_data is None:
            return
            
        try:
            if tof_data.ndim == 1:
                tof_data = np.expand_dims(tof_data, axis=0)
            if tof_data.size == 0 or len(tof_data) == 0:
                return
                
            times = tof_data[:, 0]
            avg_tof = np.mean(times)
            
            vx = tof_data[:, 2]
            vy = tof_data[:, 4]
            vz = tof_data[:, 6]
            speeds = np.sqrt(vx**2 + vy**2 + vz**2)
            v_max = np.max(speeds) if len(speeds) > 0 else 3.8e4
            if v_max <= 0:
                v_max = 3.8e4
                
            h = float(self.txt_h.text())
            dt_cfl = h / v_max
            
            suggested_T = 1.2 * avg_tof
            suggested_dt = 0.8 * dt_cfl
            
            self._suggested_T = suggested_T
            self._suggested_dt = suggested_dt
            
            msg_pt = f"Sugestão PIC: T_sug = {suggested_T:.2e} s | dt_sug = {suggested_dt:.2e} s"
            msg_en = f"PIC Suggestion: T_sug = {suggested_T:.2e} s | dt_sug = {suggested_dt:.2e} s"
            
            self.lbl_pic_suggestion.setText(msg_pt if self.language == "PT" else msg_en)
            self.btn_apply_pic_suggestion.setVisible(True)
        except Exception as e:
            print(f"Error calculating PIC suggestions: {e}")
            
    def apply_pic_suggestions(self):
        if hasattr(self, "_suggested_T") and hasattr(self, "_suggested_dt"):
            self.txt_tfinal.setText(f"{self._suggested_T:.2e}")
            self.txt_dt.setText(f"{self._suggested_dt:.2e}")
            self.btn_apply_pic_suggestion.setVisible(False)
            self.lbl_pic_suggestion.setText("Sugestões aplicadas!" if self.language == "PT" else "Suggestions applied!")
            self.check_cfl()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.running = False
            self.worker.wait()
        event.accept()

    def abrir_projeto(self):
        title = self.tr("open_title")
        file_path, _ = QFileDialog.getOpenFileName(self, title, "", "JSON Files (*.json)")
        if not file_path:
            return
        self.carregar_projeto_do_caminho(file_path, silencioso=False)

    def carregar_projeto_do_caminho(self, file_path, silencioso=False):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                project_data = json.load(f)
                
            if "h" in project_data: self.txt_h.setText(str(project_data["h"]))
            if "zmax" in project_data: self.txt_zmax.setText(str(project_data["zmax"]))
            if "rmax" in project_data: self.txt_rmax.setText(str(project_data["rmax"]))
            if "bfield_enabled" in project_data: self.chk_bfield.setChecked(bool(project_data["bfield_enabled"]))
            if "bfield_path" in project_data: self.txt_bfield_path.setText(str(project_data["bfield_path"]))
            if "regime" in project_data: self.cb_regime.setCurrentText(str(project_data["regime"]))
            if "dt" in project_data: self.txt_dt.setText(str(project_data["dt"]))
            if "tfinal" in project_data: self.txt_tfinal.setText(str(project_data["tfinal"]))
            if "w_trans" in project_data: self.txt_w_trans.setText(str(project_data["w_trans"]))
            if "w_emit" in project_data: self.txt_w_emit.setText(str(project_data["w_emit"]))
            if "w_tof" in project_data: self.txt_w_tof.setText(str(project_data["w_tof"]))
            if "max_iter" in project_data: self.txt_max_iter.setText(str(project_data["max_iter"]))
            if "threads" in project_data: self.spin_threads.setValue(int(project_data["threads"]))
            if "dump_potential" in project_data: self.chk_dump_potential.setChecked(bool(project_data["dump_potential"]))
            if "dump_charge_density" in project_data: self.chk_dump_charge.setChecked(bool(project_data["dump_charge_density"]))
            if "dump_trajectory_density" in project_data: self.chk_dump_trajdens.setChecked(bool(project_data["dump_trajectory_density"]))
            if "dump_tof" in project_data: self.chk_dump_tof.setChecked(bool(project_data["dump_tof"]))
            if "tof_style" in project_data: self.cb_tof_style.setCurrentIndex(int(project_data["tof_style"]))
            if "plane_z" in project_data: self.txt_plane_z.setText(str(project_data["plane_z"]))
            if "plane_mode" in project_data: self.cb_plane_mode.setCurrentIndex(int(project_data["plane_mode"]))
            if "plane_orient" in project_data:
                self.cb_plane_orient.setCurrentIndex(int(project_data["plane_orient"]))
            else:
                self.cb_plane_orient.setCurrentIndex(1) # Default to XZ Plane
            if "map_2d" in project_data:
                self.cb_map_2d.setCurrentIndex(int(project_data["map_2d"]))
            else:
                self.cb_map_2d.setCurrentIndex(0) # Default to Potential Map
            
            self.geometries = project_data.get("geometries", [])
            for geom in self.geometries:
                if "mapping" not in geom:
                    geom["mapping"] = "rotz"
            self.beams = project_data.get("beams", [])
            for idx, beam in enumerate(self.beams):
                if "nome" not in beam:
                    beam["nome"] = f"Feixe {idx + 1}"
                if "particulas" not in beam:
                    beam["particulas"] = int(beam.get("n_part", 3000))
                if "corrente" not in beam:
                    beam["corrente"] = 1.0
                if "massa" not in beam:
                    beam["massa"] = 136.2
                if "carga" not in beam:
                    beam["carga"] = 1.0
                if "energy" not in beam:
                    beam["energy"] = 1000.0
                if "emittance" not in beam:
                    beam["emittance"] = 1e-6
                if "distribution" not in beam:
                    beam["distribution"] = "Uniform"
                if "radius" not in beam:
                    beam["radius"] = 0.0005
                if "orig_z" not in beam:
                    beam["orig_z"] = beam.get("z_start", 0.081)
                if "orig_x" not in beam:
                    beam["orig_x"] = 0.0
                if "orig_y" not in beam:
                    beam["orig_y"] = 0.0
                if "dir_x" not in beam:
                    beam["dir_x"] = 0.0
                if "dir_z" not in beam:
                    beam["dir_z"] = 1.0
                if "z_start" not in beam:
                    beam["z_start"] = beam["orig_z"]
            
            self.reload_geometries_table()
            self.reload_beams_table()
            self._current_geom_row = None
            self.group_editor.setEnabled(False)
            
            self.threads = self.spin_threads.value()
            self.dump_potential = self.chk_dump_potential.isChecked()
            self.dump_charge_density = self.chk_dump_charge.isChecked()
            self.dump_trajectory_density = self.chk_dump_trajdens.isChecked()
            self.dump_tof = self.chk_dump_tof.isChecked()
            
            self.toggle_regime_fields()
            self.on_plane_mode_changed()
            self.reload_visualizer_scene()
            
            self.lbl_status.setText(f"{self.tr('status_loaded')} {os.path.basename(file_path)}")
            if not silencioso:
                QMessageBox.information(self, self.tr("load_success_title"), self.tr("load_success_msg").format(file_path))
        except Exception as e:
            if not silencioso:
                QMessageBox.critical(self, self.tr("load_error_title"), self.tr("load_error_msg").format(e))
            else:
                raise e

    def export_tof_data(self):
        tof_histo_path = os.path.join(self.backend_dir, "tof_histo.txt")
        tof_raw_path = os.path.join(self.backend_dir, "tof.txt")
        
        if not os.path.exists(tof_histo_path) and not os.path.exists(tof_raw_path):
            QMessageBox.warning(self, "Sem Dados", "Nenhum arquivo de dados TOF encontrado. Execute a simulação primeiro.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(self, "Exportar Dados TOF", "", "Text Files (*.txt)")
        if not file_path:
            return
            
        try:
            if os.path.exists(tof_histo_path):
                data = load_numpy_file_safe(tof_histo_path)
                if data is None or data.size == 0:
                    raise Exception("O arquivo tof_histo.txt está vazio ou corrompido.")
                times_us = data[:, 0] * 1e6
                counts = data[:, 1]
            else:
                raw_data = load_numpy_file_safe(tof_raw_path)
                if raw_data is None or raw_data.size == 0 or len(raw_data) == 0:
                    raise Exception("O arquivo raw tof.txt está vazio ou corrompido.")
                times = raw_data[:, 0]
                counts, bin_edges = np.histogram(times, bins=150)
                bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0
                times_us = bin_centers * 1e6
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("Tempo_Voo_us\tContagem_Ions\n")
                for t_us, count in zip(times_us, counts):
                    f.write(f"{t_us:.6f}\t{int(count)}\n")
                    
            QMessageBox.information(self, "Exportação Concluída", f"Dados exportados com sucesso para:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erro na Exportação", f"Ocorreu um erro ao exportar dados TOF:\n{e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    from PySide6.QtWidgets import QSplashScreen
    from PySide6.QtGui import QPixmap
    from PySide6.QtCore import QCoreApplication, Qt
    
    icon_path = resolve_resource("frontend/ibsimion_icon.png")
    splash = None
    if os.path.exists(icon_path):
        pixmap = QPixmap(icon_path)
        scaled_pixmap = pixmap.scaled(512, 512, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        splash = QSplashScreen(scaled_pixmap)
        splash.show()
        splash.showMessage(
            "IBSimion v2.0.1.e3l - Inicializando componentes...",
            Qt.AlignBottom | Qt.AlignHCenter,
            Qt.white
        )
        QCoreApplication.processEvents()
        
    # Close early background splash screen if running
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pid_file = os.path.join(script_dir, "..", "early_splash.pid")
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
            import signal
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
        finally:
            if os.path.exists(pid_file):
                try:
                    os.remove(pid_file)
                except Exception:
                    pass

    def delay_and_process(seconds, msg):
        steps = int(seconds / 0.05)
        for _ in range(steps):
            if splash is not None and msg:
                splash.showMessage(
                    f"IBSimion v2.0.1.e3l - {msg}",
                    Qt.AlignBottom | Qt.AlignHCenter,
                    Qt.white
                )
            time.sleep(0.05)
            QCoreApplication.processEvents()

    print("[STATUS] Carregando Malhas...")
    delay_and_process(0.8, "Carregando Malhas...")

    print("[STATUS] Vinculando resolvedor C++...")
    delay_and_process(0.8, "Vinculando resolvedor C++...")

    print("[STATUS] Inicializando PyVista 3D...")
    delay_and_process(0.8, "Inicializando PyVista 3D...")

    window = MainWindow()
    
    print("[STATUS] Pronto!")
    delay_and_process(0.4, "Pronto!")
    
    if splash is not None:
        splash.finish(window)
        
    window.show()
    window.raise_()
    window.activateWindow()
    sys.exit(app.exec())
