# -*- coding: utf-8 -*-
# main.py
# Main PySide6 Application for IBSimion

import os
import sys
import subprocess
import time
import numpy as np
import matplotlib
matplotlib.use('qtagg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, 
    QHBoxLayout, QGridLayout, QLabel, QLineEdit, QSlider, QPushButton, 
    QComboBox, QFileDialog, QGroupBox, QTableWidget, QTableWidgetItem,
    QProgressBar, QMessageBox
)

from translation import TRANSLATIONS
from pyvista_widget import PyVistaWidget

def get_backend_dir():
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle (dist/IBSimion/IBSimion.exe)
        exe_dir = os.path.dirname(sys.executable)
        dist_dir = os.path.dirname(exe_dir)
        d_dir = os.path.dirname(dist_dir)
        backend_dir = os.path.join(d_dir, "backend")
    else:
        # Running in normal python interpreter (D/frontend/main.py)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        d_dir = os.path.dirname(script_dir)
        backend_dir = os.path.join(d_dir, "backend")
    return os.path.abspath(backend_dir)

# Premium Dark QSS Style Sheet
STYLESHEET = """
QMainWindow {
    background-color: #121212;
}
QTabWidget::pane {
    border: 1px solid #2d2d2d;
    background-color: #1e1e1e;
    border-radius: 6px;
}
QTabBar::tab {
    background-color: #252525;
    color: #b3b3b3;
    padding: 10px 20px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}
QTabBar::tab:hover {
    background-color: #333333;
    color: #ffffff;
}
QTabBar::tab:selected {
    background-color: #7d56f4;
    color: #ffffff;
    font-weight: bold;
}
QGroupBox {
    border: 1px solid #3d3d3d;
    border-radius: 6px;
    margin-top: 15px;
    font-weight: bold;
    color: #7d56f4;
    padding-top: 15px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    left: 10px;
}
QLabel {
    color: #e0e0e0;
    font-size: 12px;
}
QLineEdit {
    background-color: #2b2b2b;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    color: #ffffff;
    padding: 4px;
}
QLineEdit:focus {
    border: 1px solid #7d56f4;
}
QSlider::groove:horizontal {
    border: 1px solid #3d3d3d;
    height: 8px;
    background: #2b2b2b;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #7d56f4;
    border: 1px solid #7d56f4;
    width: 14px;
    margin: -3px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #9d7cf7;
}
QPushButton {
    background-color: #2c2c2c;
    border: 1px solid #4d4d4d;
    border-radius: 4px;
    color: #ffffff;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #3c3c3c;
    border: 1px solid #7d56f4;
}
QPushButton:pressed {
    background-color: #7d56f4;
}
QPushButton#btn_run {
    background-color: #7d56f4;
    border: 1px solid #7d56f4;
}
QPushButton#btn_run:hover {
    background-color: #9d7cf7;
}
QPushButton#btn_opt {
    background-color: #1b5e20;
    border: 1px solid #1b5e20;
}
QPushButton#btn_opt:hover {
    background-color: #2e7d32;
}
QTableWidget {
    background-color: #1e1e1e;
    gridline-color: #2d2d2d;
    color: #ffffff;
    border: 1px solid #3d3d3d;
}
QHeaderView::section {
    background-color: #252525;
    color: #ffffff;
    padding: 5px;
    border: 1px solid #2d2d2d;
}
QProgressBar {
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    text-align: center;
    background-color: #2b2b2b;
    color: #ffffff;
}
QProgressBar::chunk {
    background-color: #7d56f4;
}
QComboBox {
    background-color: #2b2b2b;
    border: 1px solid #3d3d3d;
    border-radius: 4px;
    color: #ffffff;
    padding: 4px;
}
"""

class SimWorker(QThread):
    # Signals to communicate simulation status/outputs
    status_signal = Signal(str)
    finished_signal = Signal(bool, float) # (success, duration)
    opt_step_signal = Signal(int, int, float, list) # (iter, max_iter, loss, voltages)
    opt_finished_signal = Signal(bool, list) # (success, best_voltages)

    def __init__(self, is_opt=False, params=None):
        super().__init__()
        self.is_opt = is_opt
        self.params = params
        self.running = True

    def run(self):
        start_time = time.time()
        
        # Paths
        backend_dir = get_backend_dir()
        wsl_dir = backend_dir.replace("\\", "/").replace("C:", "/mnt/c").replace("c:", "/mnt/c")
        config_path = os.path.join(backend_dir, "sim_config.txt")
        
        if not self.is_opt:
            # Simple Run
            self.status_signal.emit("status_running_sim")
            self.write_config(config_path, self.params)
            
            success = self.execute_wsl(wsl_dir)
            duration = time.time() - start_time
            self.finished_signal.emit(success, duration)
        else:
            # Nelder-Mead Optimization Run in Python using SciPy
            self.status_signal.emit("status_running_sim")
            max_iter = self.params.get("max_iter", 50)
            
            # Initial guess (Voltages)
            v_keys = ["Vdeteletrons", "Vgradepositiva", "Vgradenegativa", "Vlente", "Vdrift", "Vdetions"]
            x0 = [self.params[k] for k in v_keys]
            
            import scipy.optimize as opt
            
            curr_iter = 0
            best_x = x0
            best_loss = float('inf')
            
            def loss_function(x):
                nonlocal curr_iter, best_loss, best_x
                if not self.running:
                    raise Exception("Optimization stopped by user")
                
                # Apply voltages
                trial_params = self.params.copy()
                for idx, k in enumerate(v_keys):
                    trial_params[k] = float(x[idx])
                    
                self.write_config(config_path, trial_params)
                success = self.execute_wsl(wsl_dir)
                
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
            except Exception as e:
                print("Optimization run completed or stopped:", e)
                
            self.opt_finished_signal.emit(self.running, list(best_x))

    def write_config(self, filepath, params):
        with open(filepath, "w") as f:
            for k, v in params.items():
                f.write(f"{k}={v}\n")

    def execute_wsl(self, wsl_dir):
        cmd = f'wsl bash -c "cd {wsl_dir} && ./ibsimu_wrapper"'
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                return True
            else:
                print("WSL Execution Error Stderr:", res.stderr)
                return False
        except Exception as e:
            print("WSL Execution Exception:", e)
            return False

    def evaluate_results(self, backend_dir, params):
        tof_path = os.path.join(backend_dir, "tof.txt")
        if not os.path.exists(tof_path):
            return 1e6, 0.0, 0.0, 0.0
            
        try:
            data = np.loadtxt(tof_path)
            if data.ndim == 1:
                data = np.expand_dims(data, axis=0)
            if data.size == 0 or len(data) == 0:
                return 1e6, 0.0, 0.0, 0.0

            # 1. Transmission
            # Npart1 is the primary species particle count
            n_part_gen = params.get("Npart1", 50000)
            n_part_rec = len(data)
            trans = n_part_rec / n_part_gen if n_part_gen > 0 else 0.0
            
            # 2. RMS Emittance
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
            
            # 3. FWHM of TOF (in seconds)
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
                
            # 4. Weighted Loss calculation
            w_trans = params.get("w_trans", 1.0)
            w_emit = params.get("w_emit", 1.0)
            w_tof = params.get("w_tof", 1.0)
            
            # Normalization factors
            # Emittance is typical 1e-6 m-rad, FWHM is typical 1e-9 s (1 ns)
            loss = - w_trans * trans + w_emit * (emitt * 1e6) + w_tof * (fwhm * 1e9)
            return loss, trans, emitt, fwhm
        except Exception as e:
            print("Evaluation exception:", e)
            return 1e6, 0.0, 0.0, 0.0


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#1e1e1e')
        self.axes = fig.add_subplot(111)
        self.axes.set_facecolor('#121212')
        self.axes.spines['bottom'].set_color('#3d3d3d')
        self.axes.spines['top'].set_color('#3d3d3d')
        self.axes.spines['left'].set_color('#3d3d3d')
        self.axes.spines['right'].set_color('#3d3d3d')
        self.axes.tick_params(colors='#e0e0e0', which='both')
        self.axes.xaxis.label.set_color('#e0e0e0')
        self.axes.yaxis.label.set_color('#e0e0e0')
        self.axes.title.set_color('#7d56f4')
        super().__init__(fig)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.lang = 'pt'
        self.backend_dir = get_backend_dir()
        
        # Load visual theme
        self.setStyleSheet(STYLESHEET)
        
        # Setup UI layout
        self.setup_ui()
        self.retranslate_ui()
        
        # State variables
        self.opt_losses = []
        self.opt_iterations = []
        self.worker = None
        
        # PIC animation state variables
        self.animation_timer = QTimer(self)
        self.animation_timer.setInterval(200)  # 200 ms per frame
        self.animation_timer.timeout.connect(self.advance_pic_animation)
        self.pic_snapshots = []
        self.pic_times = []

    def setup_ui(self):
        self.resize(1200, 800)
        
        # Central widget
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # Top panel (Language selector)
        top_layout = QHBoxLayout()
        self.lbl_lang = QLabel()
        self.cb_lang = QComboBox()
        self.cb_lang.addItems(["Português", "English"])
        self.cb_lang.currentIndexChanged.connect(self.change_language)
        top_layout.addWidget(self.lbl_lang)
        top_layout.addWidget(self.cb_lang)
        top_layout.addStretch()
        main_layout.addLayout(top_layout)
        
        # Tab Widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # Status Bar / Progress Bar at bottom
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.lbl_status = QLabel()
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.lbl_status)
        
        # Create Tabs
        self.create_config_tab()
        self.create_cad_tab()
        self.create_run_tab()
        self.create_visualizer_tab()

    def create_config_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # Left Panel (Electrode Voltages)
        left_box = QGroupBox()
        self.group_voltages = left_box
        grid_vol = QGridLayout(left_box)
        
        self.lbl_vdet_el = QLabel()
        self.txt_vdet_el = QLineEdit("3700")
        self.sld_vdet_el = QSlider(Qt.Horizontal)
        self.sld_vdet_el.setRange(0, 5000)
        self.sld_vdet_el.setValue(3700)
        self.connect_slider_txt(self.sld_vdet_el, self.txt_vdet_el)
        
        self.lbl_vgrid_pos = QLabel()
        self.txt_vgrid_pos = QLineEdit("500")
        self.sld_vgrid_pos = QSlider(Qt.Horizontal)
        self.sld_vgrid_pos.setRange(-2000, 2000)
        self.sld_vgrid_pos.setValue(500)
        self.connect_slider_txt(self.sld_vgrid_pos, self.txt_vgrid_pos)

        self.lbl_vgrid_neg = QLabel()
        self.txt_vgrid_neg = QLineEdit("-500")
        self.sld_vgrid_neg = QSlider(Qt.Horizontal)
        self.sld_vgrid_neg.setRange(-2000, 2000)
        self.sld_vgrid_neg.setValue(-500)
        self.connect_slider_txt(self.sld_vgrid_neg, self.txt_vgrid_neg)

        self.lbl_vlens = QLabel()
        self.txt_vlens = QLineEdit("-950")
        self.sld_vlens = QSlider(Qt.Horizontal)
        self.sld_vlens.setRange(-5000, 5000)
        self.sld_vlens.setValue(-950)
        self.connect_slider_txt(self.sld_vlens, self.txt_vlens)

        self.lbl_vdrift = QLabel()
        self.txt_vdrift = QLineEdit("-2924")
        self.sld_vdrift = QSlider(Qt.Horizontal)
        self.sld_vdrift.setRange(-5000, 0)
        self.sld_vdrift.setValue(-2924)
        self.connect_slider_txt(self.sld_vdrift, self.txt_vdrift)

        self.lbl_vdet_ion = QLabel()
        self.txt_vdet_ion = QLineEdit("-4800")
        self.sld_vdet_ion = QSlider(Qt.Horizontal)
        self.sld_vdet_ion.setRange(-8000, 0)
        self.sld_vdet_ion.setValue(-4800)
        self.connect_slider_txt(self.sld_vdet_ion, self.txt_vdet_ion)

        grid_vol.addWidget(self.lbl_vdet_el, 0, 0)
        grid_vol.addWidget(self.txt_vdet_el, 0, 1)
        grid_vol.addWidget(self.sld_vdet_el, 0, 2)
        
        grid_vol.addWidget(self.lbl_vgrid_pos, 1, 0)
        grid_vol.addWidget(self.txt_vgrid_pos, 1, 1)
        grid_vol.addWidget(self.sld_vgrid_pos, 1, 2)
        
        grid_vol.addWidget(self.lbl_vgrid_neg, 2, 0)
        grid_vol.addWidget(self.txt_vgrid_neg, 2, 1)
        grid_vol.addWidget(self.sld_vgrid_neg, 2, 2)
        
        grid_vol.addWidget(self.lbl_vlens, 3, 0)
        grid_vol.addWidget(self.txt_vlens, 3, 1)
        grid_vol.addWidget(self.sld_vlens, 3, 2)
        
        grid_vol.addWidget(self.lbl_vdrift, 4, 0)
        grid_vol.addWidget(self.txt_vdrift, 4, 1)
        grid_vol.addWidget(self.sld_vdrift, 4, 2)
        
        grid_vol.addWidget(self.lbl_vdet_ion, 5, 0)
        grid_vol.addWidget(self.txt_vdet_ion, 5, 1)
        grid_vol.addWidget(self.sld_vdet_ion, 5, 2)
        
        layout.addWidget(left_box, 1)
        
        # Right Panel (Beams & Mesh parameters)
        right_panel = QVBoxLayout()
        
        beam_box = QGroupBox()
        self.group_beams = beam_box
        grid_beam = QGridLayout(beam_box)
        
        self.lbl_npart = QLabel()
        self.txt_npart = QLineEdit("5000")
        self.lbl_q = QLabel()
        self.txt_q = QLineEdit("1.0")
        self.lbl_m1 = QLabel()
        self.txt_m1 = QLineEdit("136.2")
        self.lbl_m2 = QLabel()
        self.txt_m2 = QLineEdit("137.2")
        self.lbl_m3 = QLabel()
        self.txt_m3 = QLineEdit("138.2")
        
        self.lbl_r0 = QLabel()
        self.txt_r0 = QLineEdit("0.0005")
        self.lbl_tp = QLabel()
        self.txt_tp = QLineEdit("0.001")
        self.lbl_tt = QLabel()
        self.txt_tt = QLineEdit("0.0001")
        
        grid_beam.addWidget(self.lbl_npart, 0, 0)
        grid_beam.addWidget(self.txt_npart, 0, 1)
        grid_beam.addWidget(self.lbl_q, 0, 2)
        grid_beam.addWidget(self.txt_q, 0, 3)
        
        grid_beam.addWidget(self.lbl_m1, 1, 0)
        grid_beam.addWidget(self.txt_m1, 1, 1)
        grid_beam.addWidget(self.lbl_r0, 1, 2)
        grid_beam.addWidget(self.txt_r0, 1, 3)
        
        grid_beam.addWidget(self.lbl_m2, 2, 0)
        grid_beam.addWidget(self.txt_m2, 2, 1)
        grid_beam.addWidget(self.lbl_tp, 2, 2)
        grid_beam.addWidget(self.txt_tp, 2, 3)

        grid_beam.addWidget(self.lbl_m3, 3, 0)
        grid_beam.addWidget(self.txt_m3, 3, 1)
        grid_beam.addWidget(self.lbl_tt, 3, 2)
        grid_beam.addWidget(self.txt_tt, 3, 3)
        
        right_panel.addWidget(beam_box)
        
        # Mesh box
        mesh_box = QGroupBox()
        self.group_mesh = mesh_box
        grid_mesh = QGridLayout(mesh_box)
        
        self.lbl_h = QLabel()
        self.txt_h = QLineEdit("0.001") # default 1mm fast
        self.lbl_zmax = QLabel()
        self.txt_zmax = QLineEdit("0.36")
        self.lbl_xymax = QLabel()
        self.txt_xymax = QLineEdit("0.035")
        
        grid_mesh.addWidget(self.lbl_h, 0, 0)
        grid_mesh.addWidget(self.txt_h, 0, 1)
        grid_mesh.addWidget(self.lbl_zmax, 1, 0)
        grid_mesh.addWidget(self.txt_zmax, 1, 1)
        grid_mesh.addWidget(self.lbl_xymax, 2, 0)
        grid_mesh.addWidget(self.txt_xymax, 2, 1)
        
        right_panel.addWidget(mesh_box)
        layout.addLayout(right_panel, 1)
        
        self.tabs.addTab(tab, "")

    def create_cad_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        import_box = QGroupBox()
        self.group_import = import_box
        grid_imp = QGridLayout(import_box)
        
        self.lbl_import_mode = QLabel()
        self.cb_import_mode = QComboBox()
        self.cb_import_mode.addItems(["DXF", "STL"])
        self.cb_import_mode.currentIndexChanged.connect(self.toggle_import_fields)
        
        self.lbl_dxf_file = QLabel()
        self.txt_dxf_file = QLineEdit("tofl203d.dxf")
        self.btn_dxf_browse = QPushButton()
        self.btn_dxf_browse.clicked.connect(self.browse_dxf)
        
        grid_imp.addWidget(self.lbl_import_mode, 0, 0)
        grid_imp.addWidget(self.cb_import_mode, 0, 1)
        grid_imp.addWidget(self.lbl_dxf_file, 1, 0)
        grid_imp.addWidget(self.txt_dxf_file, 1, 1)
        grid_imp.addWidget(self.btn_dxf_browse, 1, 2)
        
        layout.addWidget(import_box)
        
        # STL Files group
        self.stl_box = QGroupBox()
        self.group_stl_files = self.stl_box
        grid_stl = QGridLayout(self.stl_box)
        
        # Detector Electrons STL
        self.lbl_stl_det_el = QLabel()
        self.txt_stl_det_el = QLineEdit("")
        self.btn_stl_det_el = QPushButton("...")
        self.btn_stl_det_el.clicked.connect(lambda: self.browse_stl(self.txt_stl_det_el))
        
        # Positive Grid STL
        self.lbl_stl_grid_pos = QLabel()
        self.txt_stl_grid_pos = QLineEdit("")
        self.btn_stl_grid_pos = QPushButton("...")
        self.btn_stl_grid_pos.clicked.connect(lambda: self.browse_stl(self.txt_stl_grid_pos))

        # Negative Grid STL
        self.lbl_stl_grid_neg = QLabel()
        self.txt_stl_grid_neg = QLineEdit("")
        self.btn_stl_grid_neg = QPushButton("...")
        self.btn_stl_grid_neg.clicked.connect(lambda: self.browse_stl(self.txt_stl_grid_neg))

        # Lens STL
        self.lbl_stl_lens = QLabel()
        self.txt_stl_lens = QLineEdit("")
        self.btn_stl_lens = QPushButton("...")
        self.btn_stl_lens.clicked.connect(lambda: self.browse_stl(self.txt_stl_lens))

        # Drift Tube STL
        self.lbl_stl_drift = QLabel()
        self.txt_stl_drift = QLineEdit("")
        self.btn_stl_drift = QPushButton("...")
        self.btn_stl_drift.clicked.connect(lambda: self.browse_stl(self.txt_stl_drift))

        # Detector Ions STL
        self.lbl_stl_det_ion = QLabel()
        self.txt_stl_det_ion = QLineEdit("")
        self.btn_stl_det_ion = QPushButton("...")
        self.btn_stl_det_ion.clicked.connect(lambda: self.browse_stl(self.txt_stl_det_ion))

        grid_stl.addWidget(self.lbl_stl_det_el, 0, 0)
        grid_stl.addWidget(self.txt_stl_det_el, 0, 1)
        grid_stl.addWidget(self.btn_stl_det_el, 0, 2)
        
        grid_stl.addWidget(self.lbl_stl_grid_pos, 1, 0)
        grid_stl.addWidget(self.txt_stl_grid_pos, 1, 1)
        grid_stl.addWidget(self.btn_stl_grid_pos, 1, 2)

        grid_stl.addWidget(self.lbl_stl_grid_neg, 2, 0)
        grid_stl.addWidget(self.txt_stl_grid_neg, 2, 1)
        grid_stl.addWidget(self.btn_stl_grid_neg, 2, 2)

        grid_stl.addWidget(self.lbl_stl_lens, 3, 0)
        grid_stl.addWidget(self.txt_stl_lens, 3, 1)
        grid_stl.addWidget(self.btn_stl_lens, 3, 2)

        grid_stl.addWidget(self.lbl_stl_drift, 4, 0)
        grid_stl.addWidget(self.txt_stl_drift, 4, 1)
        grid_stl.addWidget(self.btn_stl_drift, 4, 2)

        grid_stl.addWidget(self.lbl_stl_det_ion, 5, 0)
        grid_stl.addWidget(self.txt_stl_det_ion, 5, 1)
        grid_stl.addWidget(self.btn_stl_det_ion, 5, 2)

        layout.addWidget(self.stl_box)
        
        # Translation offsets group
        offset_box = QGroupBox()
        self.group_offset = offset_box
        grid_off = QHBoxLayout(offset_box)
        self.lbl_dx = QLabel()
        self.txt_dx = QLineEdit("0.0")
        self.lbl_dy = QLabel()
        self.txt_dy = QLineEdit("0.0")
        self.lbl_dz = QLabel()
        self.txt_dz = QLineEdit("0.0")
        grid_off.addWidget(self.lbl_dx)
        grid_off.addWidget(self.txt_dx)
        grid_off.addWidget(self.lbl_dy)
        grid_off.addWidget(self.txt_dy)
        grid_off.addWidget(self.lbl_dz)
        grid_off.addWidget(self.txt_dz)
        
        layout.addWidget(offset_box)
        layout.addStretch()
        self.tabs.addTab(tab, "")
        
        # Set default view state for CAD tab
        self.toggle_import_fields()

    def create_run_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        left_layout = QVBoxLayout()
        
        # Sim Mode group
        mode_box = QGroupBox()
        self.group_sim_mode = mode_box
        grid_mode = QGridLayout(mode_box)
        
        self.lbl_mode = QLabel()
        self.cb_mode = QComboBox()
        self.cb_mode.addItems(["CW", "PIC"])
        self.cb_mode.currentIndexChanged.connect(self.toggle_pic_fields)
        
        self.lbl_dt = QLabel()
        self.txt_dt = QLineEdit("5e-8")
        self.lbl_tfinal = QLabel()
        self.txt_tfinal = QLineEdit("5.1e-6")
        
        self.lbl_cfl_warning = QLabel()
        self.lbl_cfl_warning.setWordWrap(True)
        
        grid_mode.addWidget(self.lbl_mode, 0, 0)
        grid_mode.addWidget(self.cb_mode, 0, 1)
        grid_mode.addWidget(self.lbl_dt, 1, 0)
        grid_mode.addWidget(self.txt_dt, 1, 1)
        grid_mode.addWidget(self.lbl_tfinal, 2, 0)
        grid_mode.addWidget(self.txt_tfinal, 2, 1)
        grid_mode.addWidget(self.lbl_cfl_warning, 3, 0, 1, 2)
        
        # Connect text changes to check CFL condition in real time
        self.txt_dt.textChanged.connect(self.check_cfl_condition)
        self.txt_h.textChanged.connect(self.check_cfl_condition)
        self.txt_m1.textChanged.connect(self.check_cfl_condition)
        self.txt_q.textChanged.connect(self.check_cfl_condition)
        self.txt_vdrift.textChanged.connect(self.check_cfl_condition)
        
        left_layout.addWidget(mode_box)
        
        # Optimizer Setup group
        opt_box = QGroupBox()
        self.group_opt = opt_box
        grid_opt = QGridLayout(opt_box)
        
        self.lbl_opt_w_trans = QLabel()
        self.txt_opt_w_trans = QLineEdit("2.0")
        self.lbl_opt_w_emit = QLabel()
        self.txt_opt_w_emit = QLineEdit("0.5")
        self.lbl_opt_w_tof = QLabel()
        self.txt_opt_w_tof = QLineEdit("1.0")
        self.lbl_opt_max_iter = QLabel()
        self.txt_opt_max_iter = QLineEdit("20")
        
        grid_opt.addWidget(self.lbl_opt_w_trans, 0, 0)
        grid_opt.addWidget(self.txt_opt_w_trans, 0, 1)
        grid_opt.addWidget(self.lbl_opt_w_emit, 1, 0)
        grid_opt.addWidget(self.txt_opt_w_emit, 1, 1)
        grid_opt.addWidget(self.lbl_opt_w_tof, 2, 0)
        grid_opt.addWidget(self.txt_opt_w_tof, 2, 1)
        grid_opt.addWidget(self.lbl_opt_max_iter, 3, 0)
        grid_opt.addWidget(self.txt_opt_max_iter, 3, 1)
        
        left_layout.addWidget(opt_box)
        
        # Control buttons
        self.btn_start_sim = QPushButton()
        self.btn_start_sim.setObjectName("btn_run")
        self.btn_start_sim.clicked.connect(self.run_simple_simulation)
        
        self.btn_start_opt = QPushButton()
        self.btn_start_opt.setObjectName("btn_opt")
        self.btn_start_opt.clicked.connect(self.run_optimization)
        
        self.btn_stop_opt = QPushButton()
        self.btn_stop_opt.setEnabled(False)
        self.btn_stop_opt.clicked.connect(self.stop_worker)
        
        left_layout.addWidget(self.btn_start_sim)
        left_layout.addWidget(self.btn_start_opt)
        left_layout.addWidget(self.btn_stop_opt)
        left_layout.addStretch()
        
        layout.addLayout(left_layout, 1)
        
        # Right layout (Plots and Results)
        right_layout = QVBoxLayout()
        
        # Real-time Matplotlib Plot
        self.canvas = MplCanvas(self, width=5, height=3, dpi=100)
        right_layout.addWidget(self.canvas)
        
        # Results Table
        res_box = QGroupBox()
        self.group_results = res_box
        res_layout = QVBoxLayout(res_box)
        
        self.table_results = QTableWidget(3, 2)
        self.table_results.setHorizontalHeaderLabels(["Métrica", "Valor"])
        self.table_results.horizontalHeader().setStretchLastSection(True)
        res_layout.addWidget(self.table_results)
        
        right_layout.addWidget(res_box)
        layout.addLayout(right_layout, 2)
        
        self.tabs.addTab(tab, "")
        
        # Set default view states
        self.toggle_pic_fields()

    def create_visualizer_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # Left Panel (Viewer Controls)
        ctrl_layout = QVBoxLayout()
        self.btn_load_geom = QPushButton()
        self.btn_load_geom.clicked.connect(self.reload_visualizer_scene)
        ctrl_layout.addWidget(self.btn_load_geom)
        
        self.lbl_view_type = QLabel()
        self.cb_view_type = QComboBox()
        self.cb_view_type.addItems(["3D Perspectiva", "Plano ZX (2D)", "Plano ZY (2D)", "Plano XY (2D)"])
        self.cb_view_type.currentIndexChanged.connect(self.change_visualizer_camera)
        ctrl_layout.addWidget(self.lbl_view_type)
        ctrl_layout.addWidget(self.cb_view_type)
        
        self.cb_color_by = QLabel()
        self.combo_color_by = QComboBox()
        self.combo_color_by.currentIndexChanged.connect(self.change_trajectory_colors)
        ctrl_layout.addWidget(self.cb_color_by)
        ctrl_layout.addWidget(self.combo_color_by)
        
        # PIC Animation group box
        self.group_pic_anim = QGroupBox()
        pic_layout = QVBoxLayout(self.group_pic_anim)
        
        self.btn_play_pic = QPushButton()
        self.btn_play_pic.clicked.connect(self.toggle_pic_animation)
        pic_layout.addWidget(self.btn_play_pic)
        
        self.slider_pic = QSlider(Qt.Horizontal)
        self.slider_pic.setEnabled(False)
        self.slider_pic.valueChanged.connect(self.on_pic_slider_changed)
        pic_layout.addWidget(self.slider_pic)
        
        self.lbl_pic_time = QLabel()
        pic_layout.addWidget(self.lbl_pic_time)
        
        ctrl_layout.addWidget(self.group_pic_anim)
        
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout, 1)
        
        # Right Panel (Interactive PyVista Widget)
        self.pyvista_widget = PyVistaWidget(self)
        layout.addWidget(self.pyvista_widget, 4)
        
        self.tabs.addTab(tab, "")

    def connect_slider_txt(self, slider, txt_box):
        # Bi-directional updates
        def sld_changed(val):
            txt_box.setText(str(val))
        def txt_changed():
            try:
                val = int(float(txt_box.text()))
                slider.setValue(val)
            except ValueError:
                pass
        slider.valueChanged.connect(sld_changed)
        txt_box.editingFinished.connect(txt_changed)

    def toggle_import_fields(self):
        mode = self.cb_import_mode.currentText()
        is_stl = (mode == "STL")
        self.stl_box.setVisible(is_stl)
        self.txt_dxf_file.setEnabled(not is_stl)
        self.btn_dxf_browse.setEnabled(not is_stl)

    def toggle_pic_fields(self):
        mode = self.cb_mode.currentText()
        is_pic = (mode == "PIC")
        self.txt_dt.setEnabled(is_pic)
        self.txt_tfinal.setEnabled(is_pic)

    def browse_dxf(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Selecionar DXF", "", "DXF Files (*.dxf)")
        if fn:
            self.txt_dxf_file.setText(fn)

    def browse_stl(self, line_edit):
        fn, _ = QFileDialog.getOpenFileName(self, "Selecionar STL", "", "STL Files (*.stl)")
        if fn:
            line_edit.setText(fn)

    def change_language(self):
        idx = self.cb_lang.currentIndex()
        self.lang = 'en' if idx == 1 else 'pt'
        self.retranslate_ui()

    def retranslate_ui(self):
        t = TRANSLATIONS[self.lang]
        self.setWindowTitle(t['window_title'])
        self.tabs.setTabText(0, t['tab_config'])
        self.tabs.setTabText(1, t['tab_geom'])
        self.tabs.setTabText(2, t['tab_run'])
        self.tabs.setTabText(3, t['tab_visualizer'])
        self.lbl_lang.setText(t['lang_label'])
        
        # Config Tab
        self.group_voltages.setTitle(t['group_voltages'])
        self.lbl_vdet_el.setText(t['lbl_vdet_el'])
        self.lbl_vgrid_pos.setText(t['lbl_vgrid_pos'])
        self.lbl_vgrid_neg.setText(t['lbl_vgrid_neg'])
        self.lbl_vlens.setText(t['lbl_vlens'])
        self.lbl_vdrift.setText(t['lbl_vdrift'])
        self.lbl_vdet_ion.setText(t['lbl_vdet_ion'])
        
        self.group_beams.setTitle(t['group_beams'])
        self.lbl_npart.setText(t['lbl_npart'])
        self.lbl_q.setText(t['lbl_q'])
        self.lbl_m1.setText(t['lbl_m1'])
        self.lbl_m2.setText(t['lbl_m2'])
        self.lbl_m3.setText(t['lbl_m3'])
        self.lbl_r0.setText(t['lbl_r0'])
        self.lbl_tp.setText(t['lbl_tp'])
        self.lbl_tt.setText(t['lbl_tt'])
        
        self.group_mesh.setTitle(t['group_mesh'])
        self.lbl_h.setText(t['lbl_h'])
        self.lbl_zmax.setText(t['lbl_zmax'])
        self.lbl_xymax.setText(t['lbl_xymax'])
        
        # CAD Tab
        self.group_import.setTitle(t['group_import'])
        self.lbl_import_mode.setText(t['lbl_import_mode'])
        self.lbl_dxf_file.setText(t['lbl_dxf_file'])
        self.btn_dxf_browse.setText(t['btn_browse'])
        
        self.group_stl_files.setTitle(t['group_stl_files'])
        self.lbl_stl_det_el.setText(t['lbl_stl_det_el'])
        self.lbl_stl_grid_pos.setText(t['lbl_stl_grid_pos'])
        self.lbl_stl_grid_neg.setText(t['lbl_stl_grid_neg'])
        self.lbl_stl_lens.setText(t['lbl_stl_lens'])
        self.lbl_stl_drift.setText(t['lbl_stl_drift'])
        self.lbl_stl_det_ion.setText(t['lbl_stl_det_ion'])
        
        self.group_offset.setTitle(t['group_offset'])
        self.lbl_dx.setText(t['lbl_dx'])
        self.lbl_dy.setText(t['lbl_dy'])
        self.lbl_dz.setText(t['lbl_dz'])
        
        # Run Tab
        self.group_sim_mode.setTitle(t['group_sim_mode'])
        self.lbl_mode.setText(t['lbl_mode'])
        self.lbl_dt.setText(t['lbl_dt'])
        self.lbl_tfinal.setText(t['lbl_tfinal'])
        
        self.group_opt.setTitle(t['group_opt'])
        self.lbl_opt_w_trans.setText(t['lbl_opt_w_trans'])
        self.lbl_opt_w_emit.setText(t['lbl_opt_w_emit'])
        self.lbl_opt_w_tof.setText(t['lbl_opt_w_tof'])
        self.lbl_opt_max_iter.setText(t['lbl_opt_max_iter'])
        
        self.btn_start_sim.setText(t['btn_start_sim'])
        self.btn_start_opt.setText(t['btn_start_opt'])
        self.btn_stop_opt.setText(t['btn_stop_opt'])
        
        self.group_results.setTitle(t['group_results'])
        self.table_results.setHorizontalHeaderLabels([
            'Métrica' if self.lang == 'pt' else 'Metric',
            'Valor' if self.lang == 'pt' else 'Value'
        ])
        self.table_results.setItem(0, 0, QTableWidgetItem(t['lbl_res_transmission']))
        self.table_results.setItem(1, 0, QTableWidgetItem(t['lbl_res_emittance']))
        self.table_results.setItem(2, 0, QTableWidgetItem(t['lbl_res_fwhm']))
        
        # Visualizer Tab
        self.btn_load_geom.setText(t['btn_load_geom'])
        self.lbl_view_type.setText(t['lbl_view_type'])
        self.cb_color_by.setText(t['cb_color_by'])
        
        self.combo_color_by.clear()
        self.combo_color_by.addItems([t['color_mass'], t['color_charge'], t['color_energy']])
        
        self.group_pic_anim.setTitle(t['group_pic_anim'])
        self.btn_play_pic.setText(t['btn_play'] if not (hasattr(self, 'animation_timer') and self.animation_timer.isActive()) else t['btn_pause'])
        if not hasattr(self, 'pic_times') or not self.pic_times:
            self.lbl_pic_time.setText(t['lbl_pic_time'].format(0.0))
            
        self.check_cfl_condition()
        
        self.lbl_status.setText(t['status_ready'])

    def read_gui_parameters(self):
        """Helper to collect all GUI inputs into a single dictionary."""
        # Update/Check CFL condition
        self.check_cfl_condition()
        
        h = float(self.txt_h.text())
        mode = self.cb_mode.currentText()

        params = {
            "mode": mode,
            "import_mode": self.cb_import_mode.currentText(),
            "Vdeteletrons": float(self.txt_vdet_el.text()),
            "Vgradepositiva": float(self.txt_vgrid_pos.text()),
            "Vgradenegativa": float(self.txt_vgrid_neg.text()),
            "Vlente": float(self.txt_vlens.text()),
            "Vdrift": float(self.txt_vdrift.text()),
            "Vdetions": float(self.txt_vdet_ion.text()),
            
            "E01": float(self.txt_m1.text()), # start energy matching mass default ratio in wrapper
            "E02": float(self.txt_m2.text()),
            "E03": float(self.txt_m3.text()),
            
            "Npart1": int(self.txt_npart.text()),
            "Npart2": int(self.txt_npart.text()),
            "Npart3": int(self.txt_npart.text()),
            
            "q": float(self.txt_q.text()),
            "m1": float(self.txt_m1.text()),
            "m2": float(self.txt_m2.text()),
            "m3": float(self.txt_m3.text()),
            
            "Tp": float(self.txt_tp.text()),
            "Tt": float(self.txt_tt.text()),
            "r0": float(self.txt_r0.text()),
            "h": h,
            
            "xmin": -float(self.txt_xymax.text()),
            "xmax": float(self.txt_xymax.text()),
            "ymin": -float(self.txt_xymax.text()),
            "ymax": float(self.txt_xymax.text()),
            "zmin": 0.0,
            "zmax": float(self.txt_zmax.text()),
            
            "dx": float(self.txt_dx.text()),
            "dy": float(self.txt_dy.text()),
            "dz": float(self.txt_dz.text()),
            
            "dxf_filename": self.txt_dxf_file.text(),
            
            "stl_deteletrons": self.txt_stl_det_el.text(),
            "stl_gradepositiva": self.txt_stl_grid_pos.text(),
            "stl_gradenegativa": self.txt_stl_grid_neg.text(),
            "stl_lente": self.txt_stl_lens.text(),
            "stl_drift": self.txt_stl_drift.text(),
            "stl_detions": self.txt_stl_det_ion.text(),
            
            "dt": float(self.txt_dt.text()),
            "T_final": float(self.txt_tfinal.text()),
            
            "w_trans": float(self.txt_opt_w_trans.text()),
            "w_emit": float(self.txt_opt_w_emit.text()),
            "w_tof": float(self.txt_opt_w_tof.text()),
            "max_iter": int(self.txt_opt_max_iter.text()),
            
            "threads": 4,
            "interactive_plot": 0,
            "generate_jpg": 0
        }
        return params

    def run_simple_simulation(self):
        self.btn_start_sim.setEnabled(False)
        self.btn_start_opt.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0) # Infinite scrolling
        
        params = self.read_gui_parameters()
        self.worker = SimWorker(is_opt=False, params=params)
        self.worker.status_signal.connect(self.update_status_msg)
        self.worker.finished_signal.connect(self.on_sim_finished)
        self.worker.start()

    def run_optimization(self):
        self.btn_start_sim.setEnabled(False)
        self.btn_start_opt.setEnabled(False)
        self.btn_stop_opt.setEnabled(True)
        self.progress_bar.setVisible(True)
        
        params = self.read_gui_parameters()
        max_iter = params["max_iter"]
        self.progress_bar.setRange(0, max_iter)
        self.progress_bar.setValue(0)
        
        self.opt_losses = []
        self.opt_iterations = []
        self.canvas.axes.cla()
        self.canvas.draw()
        
        self.worker = SimWorker(is_opt=True, params=params)
        self.worker.status_signal.connect(self.update_status_msg)
        self.worker.opt_step_signal.connect(self.on_opt_step)
        self.worker.opt_finished_signal.connect(self.on_opt_finished)
        self.worker.start()

    def stop_worker(self):
        if self.worker and self.worker.isRunning():
            self.worker.running = False
            self.btn_stop_opt.setEnabled(False)
            self.lbl_status.setText("Cancelando...")

    @Slot(str)
    def update_status_msg(self, key):
        t = TRANSLATIONS[self.lang]
        if key in t:
            self.lbl_status.setText(t[key])

    @Slot(bool, float)
    def on_sim_finished(self, success, duration):
        self.btn_start_sim.setEnabled(True)
        self.btn_start_opt.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        t = TRANSLATIONS[self.lang]
        if success:
            self.lbl_status.setText(t['status_sim_success'].format(f"{duration:.2f}"))
            # Render outputs in Table & Plots
            self.load_simulation_results()
            # Force auto-reload scene in 3D viewer
            self.reload_visualizer_scene()
        else:
            self.lbl_status.setText(t['status_sim_failed'])

    @Slot(int, int, float, list)
    def on_opt_step(self, iter_idx, max_iter, loss, voltages):
        self.progress_bar.setValue(iter_idx)
        t = TRANSLATIONS[self.lang]
        self.lbl_status.setText(t['status_opt_running'].format(iter_idx, max_iter, loss))
        
        # Save values for convergence plotting
        self.opt_iterations.append(iter_idx)
        self.opt_losses.append(loss)
        
        # Plot update
        self.canvas.axes.cla()
        self.canvas.axes.plot(self.opt_iterations, self.opt_losses, 'm-o', label='Função de Perda / Loss')
        self.canvas.axes.set_xlabel('Iteração / Iteration')
        self.canvas.axes.set_ylabel('Loss')
        self.canvas.axes.set_title('Convergência do Otimizador / Convergence')
        self.canvas.axes.legend()
        self.canvas.draw()
        
        # Update current best voltages in labels/text fields
        v_keys = ["Vdeteletrons", "Vgradepositiva", "Vgradenegativa", "Vlente", "Vdrift", "Vdetions"]
        sliders = [self.sld_vdet_el, self.sld_vgrid_pos, self.sld_vgrid_neg, self.sld_vlens, self.sld_vdrift, self.sld_vdet_ion]
        txt_boxes = [self.txt_vdet_el, self.txt_vgrid_pos, self.txt_vgrid_neg, self.txt_vlens, self.txt_vdrift, self.txt_vdet_ion]
        
        for idx, val in enumerate(voltages):
            txt_boxes[idx].setText(f"{val:.1f}")
            try:
                sliders[idx].setValue(int(val))
            except Exception:
                pass

    @Slot(bool, list)
    def on_opt_finished(self, success, best_voltages):
        self.btn_start_sim.setEnabled(True)
        self.btn_start_opt.setEnabled(True)
        self.btn_stop_opt.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        t = TRANSLATIONS[self.lang]
        self.lbl_status.setText(t['status_opt_success'])
        
        # Load final results of best run
        self.load_simulation_results()
        self.reload_visualizer_scene()

    def load_simulation_results(self):
        """Reads output files and populates results table & histograms."""
        tof_path = os.path.join(self.backend_dir, "tof.txt")
        if not os.path.exists(tof_path):
            return
            
        try:
            data = np.loadtxt(tof_path)
            if data.ndim == 1:
                data = np.expand_dims(data, axis=0)
            if data.size == 0 or len(data) == 0:
                return
                
            # 1. Transmission
            params = self.read_gui_parameters()
            n_part_gen = params.get("Npart1", 50000)
            n_part_rec = len(data)
            trans = (n_part_rec / n_part_gen) * 100.0 if n_part_gen > 0 else 0.0
            
            # 2. RMS Emittance
            x = data[:, 1]
            vx = data[:, 2]
            vz = data[:, 6]
            vz[vz == 0] = 1.0
            xp = vx / vz
            
            dx = x - np.mean(x)
            dxp = xp - np.mean(xp)
            x2_mean = np.mean(dx**2)
            xp2_mean = np.mean(dxp**2)
            xxp_mean = np.mean(dx * dxp)
            emitt = np.sqrt(max(0.0, x2_mean * xp2_mean - xxp_mean**2))
            
            # 3. FWHM of TOF (convert to nanoseconds)
            times = data[:, 0]
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
            fwhm_ns = fwhm_s * 1e9

            # Populate table
            t = TRANSLATIONS[self.lang]
            self.table_results.setItem(0, 0, QTableWidgetItem(t['lbl_res_transmission']))
            self.table_results.setItem(0, 1, QTableWidgetItem(f"{trans:.2f} %"))
            
            self.table_results.setItem(1, 0, QTableWidgetItem(t['lbl_res_emittance']))
            self.table_results.setItem(1, 1, QTableWidgetItem(f"{emitt:.4e}"))
            
            self.table_results.setItem(2, 0, QTableWidgetItem(t['lbl_res_fwhm']))
            self.table_results.setItem(2, 1, QTableWidgetItem(f"{fwhm_ns:.2f} ns"))
            
            # Update canvas to show TOF Histogram if not in optimization mode
            if not self.worker or not self.worker.is_opt:
                self.canvas.axes.cla()
                self.canvas.axes.hist(times * 1e6, bins=60, color='purple', edgecolor='violet')
                self.canvas.axes.set_xlabel('Tempo de Voo / Time of Flight (µs)')
                self.canvas.axes.set_ylabel('Contagem / Ion Count')
                self.canvas.axes.set_title('Espectro de Tempo de Voo / TOF Mass Spectrum')
                self.canvas.draw()
                
        except Exception as e:
            print("Error parsing simulation outputs in GUI:", e)

    def reload_visualizer_scene(self):
        """Tells PyVista widget to reload files and redraw scene."""
        self.pyvista_widget.clear_scene()
        
        # Load 3D boundary geometry
        obj_path = os.path.join(self.backend_dir, "geometry.obj")
        self.pyvista_widget.load_geometry(obj_path)
        
        # Load trajectories (in CW mode)
        mode = self.cb_mode.currentText()
        if mode == "CW":
            self.group_pic_anim.setEnabled(False)
            if self.animation_timer.isActive():
                self.animation_timer.stop()
            traj_path = os.path.join(self.backend_dir, "trajectories.txt")
            color_idx = self.combo_color_by.currentIndex()
            color_by = 'mass' if color_idx == 0 else ('charge' if color_idx == 1 else 'energy')
            self.pyvista_widget.load_trajectories(traj_path, color_by)
        else:
            self.group_pic_anim.setEnabled(True)
            self.pic_snapshots = []
            self.pic_times = []
            try:
                files = [f for f in os.listdir(self.backend_dir) if f.startswith("pout_") and f.endswith(".txt")]
                if files:
                    def get_time(fn):
                        s = fn[5:-4]
                        return float(s)
                    files.sort(key=get_time)
                    self.pic_snapshots = [os.path.join(self.backend_dir, f) for f in files]
                    self.pic_times = [get_time(f) for f in files]
                    
                    self.slider_pic.setEnabled(True)
                    self.slider_pic.setRange(0, len(self.pic_snapshots) - 1)
                    self.slider_pic.setValue(0)
                    
                    # Load the first snapshot
                    if self.pic_snapshots:
                        self.pyvista_widget.load_pic_snapshot(self.pic_snapshots[0])
                        t = TRANSLATIONS[self.lang]
                        self.lbl_pic_time.setText(t['lbl_pic_time'].format(self.pic_times[0]))
            except Exception as e:
                print("Error loading PIC snapshots:", e)

    def check_cfl_condition(self):
        try:
            h = float(self.txt_h.text())
            dt = float(self.txt_dt.text())
            m1 = float(self.txt_m1.text())
            q = float(self.txt_q.text())
            vdrift = abs(float(self.txt_vdrift.text()))
            
            # v = sqrt(2 * q * e * V / (m * u))
            # ratio e/u = 9.6489e7
            if m1 > 0:
                v_max = np.sqrt(2.0 * abs(q) * 9.6489e7 * vdrift / m1)
            else:
                v_max = 3e5
            
            t_cfl = h / v_max if v_max > 0 else 1e-6
            t = TRANSLATIONS[self.lang]
            
            if dt >= t_cfl:
                self.lbl_cfl_warning.setText(t['lbl_cfl_warn'] + f" (Max dt: {t_cfl:.2e} s)")
                self.lbl_cfl_warning.setStyleSheet("color: #ff3333; font-weight: bold;")
            else:
                self.lbl_cfl_warning.setText(t['lbl_cfl_safe'])
                self.lbl_cfl_warning.setStyleSheet("color: #33ff33; font-weight: bold;")
        except Exception:
            pass

    def toggle_pic_animation(self):
        t = TRANSLATIONS[self.lang]
        if self.animation_timer.isActive():
            self.animation_timer.stop()
            self.btn_play_pic.setText(t['btn_play'])
        else:
            if len(self.pic_snapshots) > 0:
                self.animation_timer.start()
                self.btn_play_pic.setText(t['btn_pause'])
            else:
                QMessageBox.information(
                    self, 
                    "Erro / Error", 
                    "Nenhum snapshot PIC encontrado. Execute uma simulação PIC primeiro." if self.lang == 'pt' else "No PIC snapshots found. Run a PIC simulation first."
                )

    def advance_pic_animation(self):
        if not self.pic_snapshots:
            self.animation_timer.stop()
            return
        curr = self.slider_pic.value()
        next_val = (curr + 1) % len(self.pic_snapshots)
        self.slider_pic.setValue(next_val)

    def on_pic_slider_changed(self, val):
        if 0 <= val < len(self.pic_snapshots):
            snap_file = self.pic_snapshots[val]
            snap_time = self.pic_times[val]
            self.pyvista_widget.load_pic_snapshot(snap_file)
            t = TRANSLATIONS[self.lang]
            self.lbl_pic_time.setText(t['lbl_pic_time'].format(snap_time))

    def change_visualizer_camera(self):
        idx = self.cb_view_type.currentIndex()
        if idx == 0:
            self.pyvista_widget.plotter.view_isometric()
        elif idx == 1:
            # ZX plane: Z is longitudinal (horizontal), X is transversal (vertical)
            self.pyvista_widget.plotter.view_xz()
        elif idx == 2:
            # ZY plane
            self.pyvista_widget.plotter.view_zy()
        elif idx == 3:
            # XY plane
            self.pyvista_widget.plotter.view_yx()
        self.pyvista_widget.plotter.reset_camera()

    def change_trajectory_colors(self):
        color_idx = self.combo_color_by.currentIndex()
        color_by = 'mass' if color_idx == 0 else ('charge' if color_idx == 1 else 'energy')
        self.pyvista_widget.plot_trajectories(color_by)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
