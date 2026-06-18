# -*- coding: utf-8 -*-
# main.py
# Refactored PySide6 Application for IBSimion 2.0

import os
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
    QDialog, QMenuBar, QTextEdit, QSplitter, QListWidget
)

from pyvista_widget import PyVistaWidget

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
    if not filepath or not os.path.exists(filepath):
        return []
    try:
        import ezdxf
        doc = ezdxf.readfile(filepath)
        layers_with_entities = set()
        for entity in doc.modelspace():
            if hasattr(entity.dxf, 'layer') and entity.dxf.layer:
                layers_with_entities.add(entity.dxf.layer)
        layers = {layer for layer in layers_with_entities if layer != '0'}
        return sorted(list(layers))
    except Exception as e:
        print(f"Error reading DXF layers with ezdxf: {e}")
        return []

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manual de Uso e Fundamentos Físicos - IBSimion 2.0")
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
        self.topic_list.addItems([
            "Parâmetros de Malhas",
            "Configuração de Feixes",
            "Gerenciador de Geometrias",
            "Otimizador Nelder-Mead",
            "Paralelismo & Dumps"
        ])
        splitter.addWidget(self.topic_list)
        
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        splitter.addWidget(self.text_area)
        
        splitter.setSizes([250, 750])
        main_layout.addWidget(splitter)
        
        btn_layout = QHBoxLayout()
        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        main_layout.addLayout(btn_layout)
        
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
                    <li><b>Massa (u):</b> A massa das partículas em unidades de massa atômica unificada (u) (ex: próton = 1.0 u, elétron = 5.4e-4 u, íon de Xenônio = 131.2 u).</li>
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
                    <li><b>Processo de Otimização:</b> O algoritmo ajusta iterativamente as tensões de todos os eletrodos Dirichlet. A cada passo, executa a simulação física em WSL, lê o arquivo de saída <code>tof.txt</code> e calcula a Função de Perda (Loss).</li>
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
}
QPushButton:pressed {
    background-color: #3B82F6;
}
QPushButton#btn_run {
    background-color: #10B981;
    border: 1px solid #10B981;
}
QPushButton#btn_run:hover {
    background-color: #34D399;
}
QPushButton#btn_opt {
    background-color: #3B82F6;
    border: 1px solid #3B82F6;
}
QPushButton#btn_opt:hover {
    background-color: #60A5FA;
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

class SimWorker(QThread):
    status_signal = Signal(str)
    log_signal = Signal(str)
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
        backend_dir = get_backend_dir()
        wsl_dir = backend_dir.replace("\\", "/").replace("C:", "/mnt/c").replace("c:", "/mnt/c")
        config_path = os.path.join(backend_dir, "config_scenario.json")
        
        if not self.is_opt:
            self.status_signal.emit("Executando simulação física no WSL...")
            self.write_config(config_path, self.params)
            success = self.execute_wsl(wsl_dir)
            duration = time.time() - start_time
            self.finished_signal.emit(success, duration)
        else:
            self.status_signal.emit("Iniciando otimização física...")
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
                success = True
            except Exception as e:
                print("Optimization run stopped:", e)
                success = False
                
            self.opt_finished_signal.emit(self.running and success, list(best_x))

    def write_config(self, filepath, params):
        import copy
        p_copy = copy.deepcopy(params)
        
        def clean_path(val):
            if isinstance(val, str):
                p = val.replace("\\", "/")
                # Check specific prefixes
                for prefix in ["//wsl.localhost/Ubuntu-24.04/", "//wsl$/Ubuntu-24.04/"]:
                    if p.startswith(prefix):
                        return "/" + p[len(prefix):]
                # Fallback check for any other wsl.localhost/wsl$ distro mount
                if p.startswith("//wsl.localhost/"):
                    parts = p.split("/", 4)
                    if len(parts) >= 4:
                        return "/" + parts[3]
                elif p.startswith("//wsl$/"):
                    parts = p.split("/", 4)
                    if len(parts) >= 4:
                        return "/" + parts[3]
                return p
            return val

        if "geometries" in p_copy and isinstance(p_copy["geometries"], list):
            for geom in p_copy["geometries"]:
                if "file_path" in geom:
                    geom["file_path"] = clean_path(geom["file_path"])
        
        if "magnetic_field_file" in p_copy:
            p_copy["magnetic_field_file"] = clean_path(p_copy["magnetic_field_file"])

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(p_copy, f, indent=4)

    def execute_wsl(self, wsl_dir):
        cmd = f'wsl bash -c "cd {wsl_dir} && ./ibsimu_wrapper config_scenario.json"'
        try:
            process = subprocess.Popen(
                cmd, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True,
                bufsize=1
            )
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    self.log_signal.emit(line)
            return process.returncode == 0
        except Exception as e:
            self.log_signal.emit(f"Exceção de Execução no WSL: {e}\n")
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
        fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#111827')
        self.axes = fig.add_subplot(111)
        self.axes.set_facecolor('#0B0F19')
        self.axes.spines['bottom'].set_color('#1F2937')
        self.axes.spines['top'].set_color('#1F2937')
        self.axes.spines['left'].set_color('#1F2937')
        self.axes.spines['right'].set_color('#1F2937')
        self.axes.tick_params(colors='#F3F4F6', which='both')
        self.axes.xaxis.label.set_color('#F3F4F6')
        self.axes.yaxis.label.set_color('#F3F4F6')
        self.axes.title.set_color('#3B82F6')
        super().__init__(fig)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.backend_dir = get_backend_dir()
        self.setStyleSheet(STYLESHEET)
        
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
        
        # PIC animation state variables
        self.animation_timer = QTimer(self)
        self.animation_timer.setInterval(200)
        self.animation_timer.timeout.connect(self.advance_pic_animation)
        self.pic_snapshots = []
        self.pic_times = []
        self._current_geom_row = None

        self.setup_ui()
        self.reload_geometries_table()
        self.reload_beams_table()
        
    def setup_ui(self):
        self.setWindowTitle("IBSimion 2.0 (v2.2.0-Beta - Core Pipeline Upgrade)")
        self.resize(1360, 860)
        
        # Menu Bar
        self.menu_bar = self.menuBar()
        
        # Menu Arquivo
        self.menu_arquivo = self.menu_bar.addMenu("Arquivo")
        self.action_abrir = self.menu_arquivo.addAction("Abrir Projeto (.JSON)")
        self.action_abrir.triggered.connect(self.abrir_projeto)
        self.action_salvar = self.menu_arquivo.addAction("Salvar Projeto (.JSON)")
        self.action_salvar.triggered.connect(self.salvar_projeto)
        self.menu_arquivo.addSeparator()
        self.action_sair = self.menu_arquivo.addAction("Sair")
        self.action_sair.triggered.connect(self.close)
        
        # Menu Ajuda
        self.menu_ajuda = self.menu_bar.addMenu("Ajuda")
        self.action_manual = self.menu_ajuda.addAction("Manual de Uso")
        self.action_manual.triggered.connect(self.show_help_dialog)
        self.action_sobre = self.menu_ajuda.addAction("Sobre")
        self.action_sobre.triggered.connect(self.show_about_dialog)
        
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

    def show_help_dialog(self):
        dialog = HelpDialog(self)
        dialog.exec()

    def show_about_dialog(self):
        QMessageBox.information(
            self,
            "Sobre o IBSimion",
            "IBSimion 2.0\n"
            "Versão: v2.2.0-Beta - Core Pipeline Upgrade\n\n"
            "Ambiente de simulação coaxial generalista integrado com o resolvedor físico IBSimu."
        )

    def create_config_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # Left Panel (Mesh settings & external field)
        left_layout = QVBoxLayout()
        mesh_box = QGroupBox("Arquitetura de Malhas e Mapas Magnéticos")
        grid_mesh = QGridLayout(mesh_box)
        
        grid_mesh.addWidget(QLabel("Passo da Malha h (m):"), 0, 0)
        self.txt_h = QLineEdit("0.001")
        grid_mesh.addWidget(self.txt_h, 0, 1)
        
        grid_mesh.addWidget(QLabel("Limite longitudinal Z max (m):"), 1, 0)
        self.txt_zmax = QLineEdit("0.36")
        grid_mesh.addWidget(self.txt_zmax, 1, 1)
        
        grid_mesh.addWidget(QLabel("Limite radial R max (m):"), 2, 0)
        self.txt_rmax = QLineEdit("0.035")
        grid_mesh.addWidget(self.txt_rmax, 2, 1)
        
        # External Magnetic Field
        grid_mesh.addWidget(QLabel("Mapear Campo Magnético Externo (.TXT):"), 3, 0)
        self.chk_bfield = QCheckBox("Habilitar")
        self.chk_bfield.setStyleSheet("color: #F3F4F6;")
        grid_mesh.addWidget(self.chk_bfield, 3, 1)
        
        self.txt_bfield_path = QLineEdit("field.txt")
        grid_mesh.addWidget(self.txt_bfield_path, 4, 0)
        self.btn_browse_bfield = QPushButton("Procurar...")
        self.btn_browse_bfield.clicked.connect(self.browse_bfield_file)
        grid_mesh.addWidget(self.btn_browse_bfield, 4, 1)
        
        left_layout.addWidget(mesh_box)
        
        # Simulation Regime
        regime_box = QGroupBox("Configuração de Regime / Simulação")
        grid_regime = QGridLayout(regime_box)
        grid_regime.addWidget(QLabel("Modo de Regime:"), 0, 0)
        self.cb_regime = QComboBox()
        self.cb_regime.addItems(["CW", "PIC"])
        self.cb_regime.currentIndexChanged.connect(self.toggle_regime_fields)
        grid_regime.addWidget(self.cb_regime, 0, 1)
        
        grid_regime.addWidget(QLabel("Passo de tempo PIC dt (s):"), 1, 0)
        self.txt_dt = QLineEdit("5e-8")
        grid_regime.addWidget(self.txt_dt, 1, 1)
        
        grid_regime.addWidget(QLabel("Tempo de simulação final T (s):"), 2, 0)
        self.txt_tfinal = QLineEdit("5.1e-6")
        grid_regime.addWidget(self.txt_tfinal, 2, 1)
        
        self.lbl_cfl = QLabel("CFL: OK")
        self.lbl_cfl.setStyleSheet("color: #10B981; font-weight: bold;")
        grid_regime.addWidget(self.lbl_cfl, 3, 0, 1, 2)
        
        # Connect inputs to update CFL and plane Z coordinates
        self.txt_h.textChanged.connect(self.check_cfl)
        self.txt_dt.textChanged.connect(self.check_cfl)
        self.txt_h.textChanged.connect(self.update_plane_z_from_mesh)
        self.txt_zmax.textChanged.connect(self.update_plane_z_from_mesh)
        self.update_plane_z_from_mesh()
        
        left_layout.addWidget(regime_box)
        left_layout.addStretch()
        layout.addLayout(left_layout, 1)
        
        # Right Panel (Beams manager)
        right_layout = QVBoxLayout()
        beams_box = QGroupBox("Configuração Fina de Feixes")
        beam_main_layout = QVBoxLayout(beams_box)
        
        self.table_beams = QTableWidget()
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
        
        # Selected beam properties editor
        self.group_beam_editor = QGroupBox("Editor de Feixe Selecionado")
        self.group_beam_editor.setEnabled(False)
        beam_editor_layout = QGridLayout(self.group_beam_editor)
        
        beam_editor_layout.addWidget(QLabel("Nome do Feixe:"), 0, 0)
        self.beam_editor_name = QLineEdit()
        beam_editor_layout.addWidget(self.beam_editor_name, 0, 1)
        
        beam_editor_layout.addWidget(QLabel("Macropartículas:"), 0, 2)
        self.beam_editor_particles = QSpinBox()
        self.beam_editor_particles.setRange(1, 1000000)
        beam_editor_layout.addWidget(self.beam_editor_particles, 0, 3)
        
        beam_editor_layout.addWidget(QLabel("Corrente (mA):"), 1, 0)
        self.beam_editor_current = QDoubleSpinBox()
        self.beam_editor_current.setRange(0.0, 1000.0)
        self.beam_editor_current.setDecimals(4)
        beam_editor_layout.addWidget(self.beam_editor_current, 1, 1)
        
        beam_editor_layout.addWidget(QLabel("Massa (u):"), 1, 2)
        self.beam_editor_mass = QDoubleSpinBox()
        self.beam_editor_mass.setRange(0.0001, 1000.0)
        self.beam_editor_mass.setDecimals(4)
        beam_editor_layout.addWidget(self.beam_editor_mass, 1, 3)
        
        beam_editor_layout.addWidget(QLabel("Carga (e):"), 2, 0)
        self.beam_editor_charge = QDoubleSpinBox()
        self.beam_editor_charge.setRange(-10.0, 10.0)
        self.beam_editor_charge.setSingleStep(1.0)
        beam_editor_layout.addWidget(self.beam_editor_charge, 2, 1)
        
        beam_editor_layout.addWidget(QLabel("Energia (eV):"), 2, 2)
        self.beam_editor_energy = QDoubleSpinBox()
        self.beam_editor_energy.setRange(0.1, 1000000.0)
        self.beam_editor_energy.setSingleStep(100.0)
        beam_editor_layout.addWidget(self.beam_editor_energy, 2, 3)
        
        beam_editor_layout.addWidget(QLabel("Emitância (m-rad):"), 3, 0)
        self.beam_editor_emittance = QDoubleSpinBox()
        self.beam_editor_emittance.setRange(0.0, 0.1)
        self.beam_editor_emittance.setDecimals(8)
        self.beam_editor_emittance.setSingleStep(1e-7)
        beam_editor_layout.addWidget(self.beam_editor_emittance, 3, 1)
        
        beam_editor_layout.addWidget(QLabel("Distribuição:"), 3, 2)
        self.beam_editor_dist = QComboBox()
        self.beam_editor_dist.addItems(["Uniform", "Gaussian"])
        beam_editor_layout.addWidget(self.beam_editor_dist, 3, 3)
        
        beam_editor_layout.addWidget(QLabel("Origem Z, X, Y (m):"), 4, 0)
        orig_layout = QHBoxLayout()
        self.beam_editor_oz = QDoubleSpinBox()
        self.beam_editor_oz.setRange(-10.0, 10.0)
        self.beam_editor_oz.setDecimals(4)
        self.beam_editor_oz.setSingleStep(0.01)
        self.beam_editor_ox = QDoubleSpinBox()
        self.beam_editor_ox.setRange(-10.0, 10.0)
        self.beam_editor_ox.setDecimals(4)
        self.beam_editor_ox.setSingleStep(0.01)
        self.beam_editor_oy = QDoubleSpinBox()
        self.beam_editor_oy.setRange(-10.0, 10.0)
        self.beam_editor_oy.setDecimals(4)
        self.beam_editor_oy.setSingleStep(0.01)
        orig_layout.addWidget(self.beam_editor_oz)
        orig_layout.addWidget(self.beam_editor_ox)
        orig_layout.addWidget(self.beam_editor_oy)
        beam_editor_layout.addLayout(orig_layout, 4, 1, 1, 3)
        
        beam_editor_layout.addWidget(QLabel("Direção ux, uz:"), 5, 0)
        dir_layout = QHBoxLayout()
        self.beam_editor_dx = QDoubleSpinBox()
        self.beam_editor_dx.setRange(-1.0, 1.0)
        self.beam_editor_dx.setDecimals(4)
        self.beam_editor_dx.setSingleStep(0.05)
        self.beam_editor_dz = QDoubleSpinBox()
        self.beam_editor_dz.setRange(-1.0, 1.0)
        self.beam_editor_dz.setDecimals(4)
        self.beam_editor_dz.setSingleStep(0.05)
        dir_layout.addWidget(self.beam_editor_dx)
        dir_layout.addWidget(self.beam_editor_dz)
        beam_editor_layout.addLayout(dir_layout, 5, 1, 1, 3)
        
        self.btn_apply_beam_edits = QPushButton("Aplicar Edições no Feixe")
        self.btn_apply_beam_edits.setStyleSheet("background-color: #3B82F6; color: white; font-weight: bold;")
        self.btn_apply_beam_edits.clicked.connect(self.apply_beam_sidebar_edits)
        beam_editor_layout.addWidget(self.btn_apply_beam_edits, 6, 0, 1, 4)
        
        beam_main_layout.addWidget(self.group_beam_editor)
        
        right_layout.addWidget(beams_box)
        layout.addLayout(right_layout, 2)
        
        self.tabs.addTab(tab, "Configurações & Feixes")
        self.toggle_regime_fields()

    def create_workstation_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)
        
        # Left sidebar: Solids manager tree list & lateral properties fields
        left_panel = QVBoxLayout()
        solids_box = QGroupBox("Gerenciador de Geometrias e Sólidos")
        solids_layout = QVBoxLayout(solids_box)
        
        self.table_geoms = QTableWidget()
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
        
        left_panel.addWidget(solids_box)
        
        # Sidebar Editor panel
        self.group_editor = QGroupBox("Editor de Objeto Físico Selecionado")
        self.group_editor.setEnabled(False)
        editor_layout = QGridLayout(self.group_editor)
        
        editor_layout.addWidget(QLabel("Nome do Objeto:"), 0, 0)
        self.editor_name = QLineEdit()
        editor_layout.addWidget(self.editor_name, 0, 1)
        
        editor_layout.addWidget(QLabel("Caminho do Arquivo:"), 1, 0)
        self.editor_file = QLineEdit()
        self.editor_file.setReadOnly(True)
        editor_layout.addWidget(self.editor_file, 1, 1)
        self.btn_browse_geom = QPushButton("...")
        self.btn_browse_geom.clicked.connect(self.browse_geom_file)
        editor_layout.addWidget(self.btn_browse_geom, 1, 2)
        
        editor_layout.addWidget(QLabel("Tipo de Fronteira:"), 2, 0)
        self.editor_btype = QComboBox()
        self.editor_btype.addItems(["Dirichlet", "Neumann"])
        editor_layout.addWidget(self.editor_btype, 2, 1)
        
        editor_layout.addWidget(QLabel("Potencial Elétrico (V):"), 3, 0)
        self.editor_voltage = QDoubleSpinBox()
        self.editor_voltage.setRange(-100000.0, 100000.0)
        self.editor_voltage.setSingleStep(50.0)
        editor_layout.addWidget(self.editor_voltage, 3, 1)
        
        editor_layout.addWidget(QLabel("Offsets de Translação (m):"), 4, 0)
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
        editor_layout.addWidget(QLabel("Escala (STL/DXF):"), 5, 0)
        self.editor_scale = QDoubleSpinBox()
        self.editor_scale.setRange(1e-6, 100.0)
        self.editor_scale.setDecimals(6)
        self.editor_scale.setValue(0.001)
        editor_layout.addWidget(self.editor_scale, 5, 1)
        
        # Layer
        editor_layout.addWidget(QLabel("Camada DXF (Layer):"), 6, 0)
        self.editor_layer = QComboBox()
        editor_layout.addWidget(self.editor_layer, 6, 1)
        
        # Modo de Sólido 3D
        editor_layout.addWidget(QLabel("Modo de Sólido 3D:"), 7, 0)
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
        viewport_ctrls.addWidget(QLabel("Visualização:"))
        self.cb_view_mode = QComboBox()
        self.cb_view_mode.addItems(["3D Perspectiva", "Plano ZX (2D)", "Plano ZY (2D)", "Plano XY (2D)"])
        self.cb_view_mode.currentIndexChanged.connect(self.change_camera_view)
        viewport_ctrls.addWidget(self.cb_view_mode)
        
        viewport_ctrls.addWidget(QLabel("Colorir Trajetórias:"))
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
        
        actions_box = QGroupBox("Ações de Controle")
        actions_layout = QVBoxLayout(actions_box)
        
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
        
        left_layout.addWidget(actions_box)
        
        # Optimizer parameters
        opt_params_box = QGroupBox("Parâmetros do Otimizador")
        grid_opt = QGridLayout(opt_params_box)
        
        grid_opt.addWidget(QLabel("Peso Transmissão:"), 0, 0)
        self.txt_w_trans = QLineEdit("2.0")
        grid_opt.addWidget(self.txt_w_trans, 0, 1)
        
        grid_opt.addWidget(QLabel("Peso Emitância:"), 1, 0)
        self.txt_w_emit = QLineEdit("0.5")
        grid_opt.addWidget(self.txt_w_emit, 1, 1)
        
        grid_opt.addWidget(QLabel("Peso TOF FWHM:"), 2, 0)
        self.txt_w_tof = QLineEdit("1.0")
        grid_opt.addWidget(self.txt_w_tof, 2, 1)
        
        grid_opt.addWidget(QLabel("Iterações Máximas:"), 3, 0)
        self.txt_max_iter = QLineEdit("20")
        grid_opt.addWidget(self.txt_max_iter, 3, 1)
        
        left_layout.addWidget(opt_params_box)
        
        # Configuração de Execução e Dumps
        dumps_box = QGroupBox("Configuração de Execução e Dumps")
        dumps_layout = QGridLayout(dumps_box)
        
        dumps_layout.addWidget(QLabel("Threads Computacionais:"), 0, 0)
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
        
        left_layout.addWidget(dumps_box)
        
        # Console Log Console
        console_box = QGroupBox("Logs do Kernel Linux / WSL2")
        console_layout = QVBoxLayout(console_box)
        from PySide6.QtWidgets import QTextEdit
        self.txt_console = QTextEdit()
        self.txt_console.setReadOnly(True)
        self.txt_console.setStyleSheet("background-color: #030712; color: #10B981; font-family: Consolas; font-size: 10px;")
        console_layout.addWidget(self.txt_console)
        left_layout.addWidget(console_box, 1)
        
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
        diag_ctrl_box = QGroupBox("Configurações do Plano de Corte")
        grid_diag = QGridLayout(diag_ctrl_box)
        
        grid_diag.addWidget(QLabel("Modo de Plano:"), 0, 0)
        self.cb_plane_mode = QComboBox()
        self.cb_plane_mode.addItems(["Automático (Detector)", "Arbitrário"])
        self.cb_plane_mode.currentIndexChanged.connect(self.on_plane_mode_changed)
        grid_diag.addWidget(self.cb_plane_mode, 0, 1)
        
        grid_diag.addWidget(QLabel("Coordenada Z do Plano (m):"), 1, 0)
        self.txt_plane_z = QLineEdit("0.3549")
        grid_diag.addWidget(self.txt_plane_z, 1, 1)
        
        self.btn_update_diagnostics = QPushButton("Atualizar Diagnósticos")
        self.btn_update_diagnostics.clicked.connect(self.calculate_diagnostics_plots)
        grid_diag.addWidget(self.btn_update_diagnostics, 2, 0, 1, 2)
        
        left_layout.addWidget(diag_ctrl_box)
        
        # Estilo & Exportação TOF
        tof_opt_box = QGroupBox("Estilo & Exportação TOF")
        grid_tof_opt = QGridLayout(tof_opt_box)
        
        grid_tof_opt.addWidget(QLabel("Estilo Histograma:"), 0, 0)
        self.cb_tof_style = QComboBox()
        self.cb_tof_style.addItems(["Barras Preenchidas", "Linha Suavizada", "Dispersão com Tendência"])
        self.cb_tof_style.currentIndexChanged.connect(self.calculate_diagnostics_plots)
        grid_tof_opt.addWidget(self.cb_tof_style, 0, 1)
        
        self.btn_export_tof = QPushButton("Exportar Dados TOF (.TXT)")
        self.btn_export_tof.clicked.connect(self.export_tof_data)
        grid_tof_opt.addWidget(self.btn_export_tof, 1, 0, 1, 2)
        
        left_layout.addWidget(tof_opt_box)
        
        # Metrics Table
        metrics_box = QGroupBox("Métricas Científicas")
        metrics_layout = QVBoxLayout(metrics_box)
        self.table_metrics = QTableWidget(3, 2)
        self.table_metrics.setHorizontalHeaderLabels(["Métrica", "Valor"])
        self.table_metrics.horizontalHeader().setStretchLastSection(True)
        self.table_metrics.setItem(0, 0, QTableWidgetItem("Transmissão (%)"))
        self.table_metrics.setItem(1, 0, QTableWidgetItem("Emitância RMS X (m·rad)"))
        self.table_metrics.setItem(2, 0, QTableWidgetItem("FWHM do Tempo de Voo (ns)"))
        metrics_layout.addWidget(self.table_metrics)
        left_layout.addWidget(metrics_box)
        left_layout.addStretch()
        
        layout.addLayout(left_layout, 1)
        
        # Right Panel (Tabbed Matplotlib graphs: TOF, Profile, Contours)
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
        
        # Sub tab 3: 2D Field Contour map (potential and space charge density)
        sub_tab_contours = QWidget()
        contours_layout = QVBoxLayout(sub_tab_contours)
        self.canvas_contours = MplCanvas(self)
        self.toolbar_contours = NavigationToolbar(self.canvas_contours, self)
        self.style_navigation_toolbar(self.toolbar_contours)
        contours_layout.addWidget(self.canvas_contours)
        contours_layout.addWidget(self.toolbar_contours)
        self.diag_tabs.addTab(sub_tab_contours, "Mapa de Campo 2D & Equipotenciais")
        
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
        selected_rows = self.table_geoms.selectedItems()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        self.geometries.pop(row)
        self._current_geom_row = None
        self.reload_geometries_table()
        self.group_editor.setEnabled(False)
        self.reload_visualizer_scene()

    def on_geometry_selected(self):
        selected_rows = self.table_geoms.selectedItems()
        if not selected_rows:
            self.group_editor.setEnabled(False)
            self._current_geom_row = None
            return
            
        row = selected_rows[0].row()
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
        self.editor_scale.setValue(geom["scale"])
        
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
            abs_path = file_path
            if not os.path.isabs(abs_path):
                abs_path = os.path.join(self.backend_dir, file_path)
            
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
            self.table_beams.setItem(idx, 2, QTableWidgetItem(f"{beam['corrente']:.3f}"))
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
        selected = self.table_beams.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        self.beams.pop(row)
        self.reload_beams_table()
        self.group_beam_editor.setEnabled(False)

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
        except Exception as e:
            QMessageBox.warning(self, "Valor Inválido", f"Erro ao atualizar feixe: {e}")
            self.reload_beams_table()

    def on_beam_selected(self):
        selected = self.table_beams.selectedItems()
        if not selected:
            self.group_beam_editor.setEnabled(False)
            return
            
        row = selected[0].row()
        beam = self.beams[row]
        
        self.beam_editor_name.blockSignals(True)
        self.beam_editor_particles.blockSignals(True)
        self.beam_editor_current.blockSignals(True)
        self.beam_editor_mass.blockSignals(True)
        self.beam_editor_charge.blockSignals(True)
        self.beam_editor_energy.blockSignals(True)
        self.beam_editor_emittance.blockSignals(True)
        self.beam_editor_dist.blockSignals(True)
        self.beam_editor_oz.blockSignals(True)
        self.beam_editor_ox.blockSignals(True)
        self.beam_editor_oy.blockSignals(True)
        self.beam_editor_dx.blockSignals(True)
        self.beam_editor_dz.blockSignals(True)
        
        self.beam_editor_name.setText(beam["nome"])
        self.beam_editor_particles.setValue(beam["particulas"])
        self.beam_editor_current.setValue(beam["corrente"])
        self.beam_editor_mass.setValue(beam["massa"])
        self.beam_editor_charge.setValue(beam["carga"])
        self.beam_editor_energy.setValue(beam["energy"])
        self.beam_editor_emittance.setValue(beam["emittance"])
        self.beam_editor_dist.setCurrentText(beam["distribution"])
        self.beam_editor_oz.setValue(beam.get("orig_z", beam.get("z_start", 0.081)))
        self.beam_editor_ox.setValue(beam.get("orig_x", 0.0))
        self.beam_editor_oy.setValue(beam.get("orig_y", 0.0))
        self.beam_editor_dx.setValue(beam.get("dir_x", 0.0))
        self.beam_editor_dz.setValue(beam.get("dir_z", 1.0))
        
        self.group_beam_editor.setEnabled(True)
        
        self.beam_editor_name.blockSignals(False)
        self.beam_editor_particles.blockSignals(False)
        self.beam_editor_current.blockSignals(False)
        self.beam_editor_mass.blockSignals(False)
        self.beam_editor_charge.blockSignals(False)
        self.beam_editor_energy.blockSignals(False)
        self.beam_editor_emittance.blockSignals(False)
        self.beam_editor_dist.blockSignals(False)
        self.beam_editor_oz.blockSignals(False)
        self.beam_editor_ox.blockSignals(False)
        self.beam_editor_oy.blockSignals(False)
        self.beam_editor_dx.blockSignals(False)
        self.beam_editor_dz.blockSignals(False)

    def apply_beam_sidebar_edits(self):
        selected = self.table_beams.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        beam = self.beams[row]
        
        beam["nome"] = self.beam_editor_name.text()
        beam["particulas"] = self.beam_editor_particles.value()
        beam["corrente"] = self.beam_editor_current.value()
        beam["massa"] = self.beam_editor_mass.value()
        beam["carga"] = self.beam_editor_charge.value()
        beam["energy"] = self.beam_editor_energy.value()
        beam["emittance"] = self.beam_editor_emittance.value()
        beam["distribution"] = self.beam_editor_dist.currentText()
        beam["orig_z"] = self.beam_editor_oz.value()
        beam["orig_x"] = self.beam_editor_ox.value()
        beam["orig_y"] = self.beam_editor_oy.value()
        beam["dir_x"] = self.beam_editor_dx.value()
        beam["dir_z"] = self.beam_editor_dz.value()
        
        beam["z_start"] = beam["orig_z"]
        
        self.reload_beams_table()
        
        self.table_beams.blockSignals(True)
        self.table_beams.selectRow(row)
        self.table_beams.blockSignals(False)

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
        
        # Translate geometries file paths
        wsl_geoms = []
        for geom in self.geometries:
            geom_copy = geom.copy()
            geom_copy["file_path"] = self.to_wsl_path(geom["file_path"])
            # Ensure name and layer are aligned for DXF files
            is_dxf = geom["file_path"].lower().endswith(".dxf")
            if is_dxf and "layer" in geom:
                geom_copy["name"] = geom["layer"]
                geom_copy["layer"] = geom["layer"]
            wsl_geoms.append(geom_copy)
            
        bfield_wsl = self.to_wsl_path(self.txt_bfield_path.text()) if self.chk_bfield.isChecked() else ""
        
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
        self.btn_start_sim.setEnabled(False)
        self.btn_start_opt.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0) # Infinite scrolling
        self.txt_console.clear()
        
        params = self.read_all_scenario_parameters()
        self.worker = SimWorker(is_opt=False, params=params)
        self.worker.status_signal.connect(self.update_status_msg)
        self.worker.log_signal.connect(self.append_log)
        self.worker.finished_signal.connect(self.on_sim_finished)
        self.worker.start()

    def run_optimization(self):
        self.btn_start_sim.setEnabled(False)
        self.btn_start_opt.setEnabled(False)
        self.btn_stop_opt.setEnabled(True)
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
        
        self.worker = SimWorker(is_opt=True, params=params)
        self.worker.status_signal.connect(self.update_status_msg)
        self.worker.log_signal.connect(self.append_log)
        self.worker.opt_step_signal.connect(self.on_opt_step)
        self.worker.opt_finished_signal.connect(self.on_opt_finished)
        self.worker.start()

    def stop_worker(self):
        if self.worker and self.worker.isRunning():
            self.worker.running = False
            self.btn_stop_opt.setEnabled(False)
            self.lbl_status.setText("Cancelando...")

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
            self.lbl_status.setText(f"Simulação concluída com sucesso em {duration:.2f} s.")
            self.reload_visualizer_scene()
            self.calculate_diagnostics_plots()
        else:
            self.lbl_status.setText("Erro na simulação física. Verifique os logs.")

    @Slot(int, int, float, list)
    def on_opt_step(self, iter_idx, max_iter, loss, voltages):
        self.progress_bar.setValue(iter_idx)
        self.lbl_status.setText(f"Otimizando... Iteração {iter_idx}/{max_iter} | Loss: {loss:.4f}")
        
        self.opt_iterations.append(iter_idx)
        self.opt_losses.append(loss)
        
        self.canvas_convergence.axes.cla()
        self.canvas_convergence.axes.set_facecolor('#0B0F19')
        self.canvas_convergence.axes.plot(self.opt_iterations, self.opt_losses, 'c-o', label='Loss / Perda')
        self.canvas_convergence.axes.set_xlabel('Iteração', color='#F3F4F6')
        self.canvas_convergence.axes.set_ylabel('Loss', color='#F3F4F6')
        self.canvas_convergence.axes.set_title('Convergência do Otimizador', color='#3B82F6')
        self.canvas_convergence.axes.legend(facecolor='#111827', edgecolor='#1F2937', labelcolor='#F3F4F6')
        self.canvas_convergence.axes.grid(True, color='#1F2937')
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
        self.lbl_status.setText("Otimização concluída!")
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
            self.pyvista_widget.load_pic_snapshot(self.pic_snapshots[val])
            self.lbl_pic_time.setText(f"Tempo: {self.pic_times[val]:.2e} s")

    # -------------------------------------------------------------------------
    # Diagnostics & Cuts logic
    # -------------------------------------------------------------------------
    def calculate_diagnostics_plots(self):
        """Analisa os arquivos dat/txt e gera os histogramas de TOF, perfil radial, e contornos equipotenciais 2D."""
        tof_path = os.path.join(self.backend_dir, "tof.txt")
        pot_field_path = os.path.join(self.backend_dir, "potential_field.dat")
        rho_field_path = os.path.join(self.backend_dir, "charge_density.dat")
        
        # 1. Load TOF and metrics
        if os.path.exists(tof_path):
            try:
                data = np.loadtxt(tof_path)
                if data.ndim == 1:
                    data = np.expand_dims(data, axis=0)
                
                times = data[:, 0]
                x_pos = data[:, 1]
                y_pos = data[:, 3]
                
                # TOF Histogram / Plot
                self.canvas_tof.axes.cla()
                self.canvas_tof.axes.set_facecolor('#0B0F19')
                
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
                elif style_idx == 2:  # Dispersão com Linha de Tendência
                    counts, bin_edges = np.histogram(times * 1e6, bins=60)
                    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
                    self.canvas_tof.axes.scatter(bin_centers, counts, color='#EC4899', alpha=0.7, edgecolors='none', s=25, label='Bins')
                    if len(bin_centers) > 3:
                        try:
                            coefs = np.polyfit(bin_centers, counts, 3)
                            poly = np.poly1d(coefs)
                            x_trend = np.linspace(bin_centers.min(), bin_centers.max(), 200)
                            y_trend = poly(x_trend)
                            y_trend = np.clip(y_trend, 0, None)
                            self.canvas_tof.axes.plot(x_trend, y_trend, color='#F472B6', linewidth=2, linestyle='--', label='Tendência (Grau 3)')
                        except Exception:
                            pass
                    self.canvas_tof.axes.legend(facecolor='#111827', edgecolor='#1F2937', labelcolor='#F3F4F6')

                self.canvas_tof.axes.set_xlabel('Tempo de Voo (µs)', color='#F3F4F6')
                self.canvas_tof.axes.set_ylabel('Contagem de Íons', color='#F3F4F6')
                self.canvas_tof.axes.set_title('Espectro de Tempo de Voo (TOF)', color='#3B82F6')
                self.canvas_tof.axes.grid(True, color='#1F2937')
                self.canvas_tof.draw()
                
                # Beam Profile cut (X vs Y scatter plot at the detector Z plane)
                self.canvas_profile.axes.cla()
                self.canvas_profile.axes.set_facecolor('#0B0F19')
                self.canvas_profile.axes.scatter(x_pos * 1000, y_pos * 1000, color='#10B981', alpha=0.6, edgecolors='none', s=8)
                self.canvas_profile.axes.set_xlabel('Deflexão X (mm)', color='#F3F4F6')
                self.canvas_profile.axes.set_ylabel('Deflexão Y (mm)', color='#F3F4F6')
                self.canvas_profile.axes.set_title('Corte Transversal do Feixe no Detector', color='#3B82F6')
                self.canvas_profile.axes.grid(True, color='#1F2937')
                self.canvas_profile.draw()
                
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
                
                # Emittance RMS X
                vx = data[:, 2]
                vz = data[:, 6]
                vz[vz == 0] = 1.0
                xp = vx / vz
                dx = x_pos - np.mean(x_pos)
                dxp = xp - np.mean(xp)
                emitt = np.sqrt(max(0.0, np.mean(dx**2) * np.mean(dxp**2) - np.mean(dx * dxp)**2))
                
                self.table_metrics.setItem(0, 1, QTableWidgetItem(f"{trans:.2f} %"))
                self.table_metrics.setItem(1, 1, QTableWidgetItem(f"{emitt:.4e}"))
                self.table_metrics.setItem(2, 1, QTableWidgetItem(f"{fwhm_s*1e9:.2f} ns"))
                
            except Exception as e:
                print("Erro ao atualizar os gráficos de diagnósticos:", e)
                
        # 2. Slice potential and charge densities 2D contours at Y ≈ 0
        if os.path.exists(pot_field_path) and os.path.exists(rho_field_path):
            try:
                # Load slice manually at Y=0
                zs, xs, V_matrix = self.load_grid_slice(pot_field_path, 3) # V is column index 3
                _, _, rho_matrix = self.load_grid_slice(rho_field_path, 3) # rho is column index 3
                
                if zs is not None and xs is not None:
                    self.canvas_contours.axes.cla()
                    self.canvas_contours.axes.set_facecolor('#0B0F19')
                    
                    # Remove any existing colorbar axes to prevent duplicates
                    for extra_ax in list(self.canvas_contours.figure.axes):
                        if extra_ax is not self.canvas_contours.axes:
                            self.canvas_contours.figure.delaxes(extra_ax)
                    
                    # Colormap background representing charge density
                    Z_grid, X_grid = np.meshgrid(zs * 1000, xs * 1000) # scale to mm
                    im = None
                    if rho_matrix is not None:
                        im = self.canvas_contours.axes.pcolormesh(
                            Z_grid, X_grid, rho_matrix, cmap='plasma', shading='auto', alpha=0.6
                        )
                    
                    # Equipotential contour lines
                    contours = self.canvas_contours.axes.contour(
                        Z_grid, X_grid, V_matrix, levels=15, colors='#E5E7EB', linewidths=0.7, alpha=0.8
                    )
                    self.canvas_contours.axes.clabel(contours, inline=True, fontsize=8, fmt="%d V")
                    
                    self.canvas_contours.axes.set_xlabel('Posição Longitudinal Z (mm)', color='#F3F4F6')
                    self.canvas_contours.axes.set_ylabel('Posição Transversal X (mm)', color='#F3F4F6')
                    self.canvas_contours.axes.set_title('Equipotenciais (V) e Densidade de Carga (pcolormesh)', color='#3B82F6')
                    self.canvas_contours.axes.grid(True, color='#1F2937')
                    
                    if im is not None:
                        # Determine label dynamically
                        bg_path = rho_field_path
                        label_text = "Densidade de Corrente (A/m²)"
                        if "potential_field" in bg_path:
                            label_text = "Potencial (V)"
                        elif "magnetic" in bg_path or "bfield" in bg_path:
                            label_text = "Campo Magnético (T)"
                        elif "trajectory_density" in bg_path:
                            label_text = "Densidade de Corrente (A/m²)"
                            
                        cbar = self.canvas_contours.figure.colorbar(im, ax=self.canvas_contours.axes, orientation='vertical')
                        cbar.set_label(label_text, color="white")
                        cbar.ax.yaxis.set_tick_params(color='white', labelcolor='white')
                        cbar.ax.tick_params(colors='white')
                        cbar.outline.set_edgecolor('#1F2937')
                        
                    self.canvas_contours.draw()
            except Exception as e:
                print("Erro ao carregar o contorno do campo elétrico:", e)

    def load_grid_slice(self, filepath, val_col_idx):
        if not os.path.exists(filepath):
            return None, None, None
        try:
            raw = np.loadtxt(filepath)
            if raw.ndim == 1:
                raw = np.expand_dims(raw, axis=0)
            
            # Find closest y coordinates to 0
            ys = raw[:, 1]
            unique_ys = np.unique(ys)
            if len(unique_ys) == 0:
                return None, None, None
            
            y_slice = unique_ys[np.argmin(np.abs(unique_ys))]
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
        except Exception as e:
            print(f"Error loading grid slice from {filepath}: {e}")
            return None, None, None

    def salvar_projeto(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Salvar Projeto IBSimion", "", "JSON Files (*.json)")
        if not file_path:
            return
            
        try:
            project_data = {
                "h": self.txt_h.text(),
                "zmax": self.txt_zmax.text(),
                "rmax": self.txt_rmax.text(),
                "bfield_enabled": self.chk_bfield.isChecked(),
                "bfield_path": self.txt_bfield_path.text(),
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
                "geometries": self.geometries,
                "beams": self.beams,
                "tof_style": self.cb_tof_style.currentIndex(),
                "plane_z": self.txt_plane_z.text(),
                "plane_mode": self.cb_plane_mode.currentIndex()
            }
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(project_data, f, indent=4)
                
            self.lbl_status.setText(f"Projeto salvo em: {os.path.basename(file_path)}")
            QMessageBox.information(self, "Projeto Salvo", f"O projeto foi salvo com sucesso em:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Salvar", f"Não foi possível salvar o projeto:\n{e}")

    def abrir_projeto(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Abrir Projeto IBSimion", "", "JSON Files (*.json)")
        if not file_path:
            return
            
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
            
            self.geometries = project_data.get("geometries", [])
            for geom in self.geometries:
                if "mapping" not in geom:
                    geom["mapping"] = "rotz"
            self.beams = project_data.get("beams", [])
            for beam in self.beams:
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
            
            self.lbl_status.setText(f"Projeto carregado: {os.path.basename(file_path)}")
            QMessageBox.information(self, "Projeto Carregado", f"O projeto foi carregado com sucesso de:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Abrir", f"Não foi possível carregar o projeto:\n{e}")

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
                data = np.loadtxt(tof_histo_path)
                if data.ndim == 1:
                    data = np.expand_dims(data, axis=0)
                times_us = data[:, 0] * 1e6
                counts = data[:, 1]
            else:
                raw_data = np.loadtxt(tof_raw_path)
                if raw_data.ndim == 1:
                    raw_data = np.expand_dims(raw_data, axis=0)
                if raw_data.size == 0 or len(raw_data) == 0:
                    raise Exception("O arquivo raw tof.txt está vazio.")
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
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
