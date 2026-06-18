# -*- coding: utf-8 -*-
"""
IBSimion 2.0 - Workstation Científica de Alta Fidelidade
Aba 1: Trajetórias e Eletrodos (Corte 2D)
Aba 2: Campos Elétricos e Linhas Equipotenciais (Mapas de Contorno Reais do Solver)
Aba 3: Configuração Fina de Feixes e Parâmetros de Partículas
"""

import os
import json
import subprocess
import numpy as np
import tkinter as tk
from tkinter import messagebox, ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import Rectangle

# Configurações Estéticas Premium (Obsidian Dark Theme)
COLOR_BG = "#0B0F19"
COLOR_CARD = "#111827"
COLOR_BORDER = "#1F2937"
COLOR_TEXT = "#F3F4F6"
COLOR_MUTED = "#9CA3AF"
COLOR_BLUE = "#3B82F6"
COLOR_PINK = "#F43F5E"
COLOR_CYAN = "#10B981"

class IBSimionApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IBSimion 2.0 - Estação de Trabalho Científica")
        self.geometry("1360x860")
        self.configure(bg=COLOR_BG)
        
        self.caminho_json = "config_scenario_example.json"
        self.caminho_trajetorias = "trajectories.txt"
        self.config_data = {}
        
        self.eletrodos_widgets = []
        self.feixes_widgets = []
        
        self.criar_layout()
        self.carregar_configuracao_inicial()
        
    def criar_layout(self):
        # ----------------------------------------------------------------------
        # SIDEBAR ESQUERDA: CONTROLES GERAIS
        # ----------------------------------------------------------------------
        self.sidebar = tk.Frame(self, bg=COLOR_CARD, width=420, highlightthickness=1, highlightbackground=COLOR_BORDER)
        self.sidebar.pack(side="left", fill="y", padx=15, pady=15)
        self.sidebar.pack_propagate(False)
        
        # Header do Painel
        frame_header = tk.Frame(self.sidebar, bg=COLOR_CARD)
        frame_header.pack(fill="x", padx=20, pady=15)
        
        lbl_titulo = tk.Label(frame_header, text="IBSimion Workstation", 
                              font=("Segoe UI", 16, "bold"), bg=COLOR_CARD, fg=COLOR_TEXT)
        lbl_titulo.pack(anchor="w")
        
        lbl_sub = tk.Label(frame_header, text="Simulação de Trajetórias e Solucionador Poisson 2D", 
                             font=("Segoe UI", 8), bg=COLOR_CARD, fg=COLOR_MUTED)
        lbl_sub.pack(anchor="w", pady=2)
        
        tk.Frame(frame_header, bg=COLOR_BLUE, height=2).pack(fill="x", pady=10)

        # Caderno de Abas Esquerda (Notebook para organizar os Parâmetros)
        self.tabs_controle = ttk.Notebook(self.sidebar)
        self.tabs_controle.pack(fill="both", expand=True, padx=15, pady=5)
        
        # Estilização das abas no Windows
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=COLOR_CARD, borderwidth=0)
        style.configure("TNotebook.Tab", background=COLOR_BORDER, foreground=COLOR_TEXT, 
                        font=("Segoe UI", 8, "bold"), padding=[10, 4])
        style.map("TNotebook.Tab", background=[("selected", COLOR_BLUE)])
        
        # Aba Controle 1: Eletrodos (Tensões)
        self.tab_ctrl_eletrodos = tk.Frame(self.tabs_controle, bg=COLOR_CARD)
        self.tabs_controle.add(self.tab_ctrl_eletrodos, text="Lentes (V)")
        
        # Aba Controle 2: Feixes (Física de Partículas)
        self.tab_ctrl_feixes = tk.Frame(self.tabs_controle, bg=COLOR_CARD)
        self.tabs_controle.add(self.tab_ctrl_feixes, text="Feixes (Física)")

        # Área de Ações Finais na Sidebar
        self.card_acoes = tk.Frame(self.sidebar, bg=COLOR_CARD)
        self.card_acoes.pack(side="bottom", fill="x", padx=20, pady=15)
        
        self.btn_salvar = tk.Button(self.card_acoes, text="Salvar Alterações (JSON)", command=self.salvar_dados_json,
                               bg="#1F2937", fg=COLOR_TEXT, font=("Segoe UI", 9, "bold"), 
                               relief="flat", height=1, activebackground="#374151", activeforeground=COLOR_TEXT, bd=0)
        self.btn_salvar.pack(fill="x", pady=4)
        
        self.btn_rodar = tk.Button(self.card_acoes, text="Executar Motor C++ (WSL2)", command=self.disparar_motor_wsl,
                              bg=COLOR_BLUE, fg="white", font=("Segoe UI", 10, "bold"), 
                              relief="flat", height=2, activebackground="#2563EB", activeforeground="white", bd=0)
        self.btn_rodar.pack(fill="x", pady=4)
        
        # Terminal Log
        self.txt_log = tk.Text(self.sidebar, height=7, bg="#030712", fg=COLOR_CYAN,
                               insertbackground="white", font=("Consolas", 8), wrap="word", bd=0,
                               highlightthickness=1, highlightbackground=COLOR_BORDER)
        self.txt_log.pack(side="bottom", fill="x", padx=20, pady=5)

        # ----------------------------------------------------------------------
        # ÁREA GRÁFICA DIREITA (Visualizador Científico)
        # ----------------------------------------------------------------------
        self.panel_grafico = tk.Frame(self, bg=COLOR_BG)
        self.panel_grafico.pack(side="right", fill="both", expand=True, padx=15, pady=15)
        
        # Caderno de Abas Gráfico (Notebook Direito)
        self.tabs_graficos = ttk.Notebook(self.panel_grafico)
        self.tabs_graficos.pack(fill="both", expand=True)
        
        # Aba Gráfica 1: Trajetórias 2D
        self.tab_plot_trajetorias = tk.Frame(self.tabs_graficos, bg=COLOR_BG)
        self.tabs_graficos.add(self.tab_plot_trajetorias, text=" Trajetórias de Feixes ")
        
        # Aba Gráfica 2: Linhas Equipotenciais (Campos do Solver)
        self.tab_plot_campos = tk.Frame(self.tabs_graficos, bg=COLOR_BG)
        self.tabs_graficos.add(self.tab_plot_campos, text=" Mapa de Equipotenciais (EpotField) ")

        # Inicialização dos Canvas de Plotagem do Matplotlib
        self.fig1, self.ax1 = plt.subplots(figsize=(8, 6), facecolor=COLOR_BG)
        self.ax1.set_facecolor("#0F172A")
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=self.tab_plot_trajetorias)
        self.canvas1.get_tk_widget().pack(fill="both", expand=True)
        
        # Toolbar para o Canvas 1
        self.toolbar1 = NavigationToolbar2Tk(self.canvas1, self.tab_plot_trajetorias)
        self.toolbar1.configure(bg=COLOR_CARD)
        for child in self.toolbar1.winfo_children():
            try: child.configure(bg=COLOR_CARD, fg=COLOR_TEXT)
            except: pass
        self.toolbar1.update()

        # Canvas para o Mapa de Campos Equipotenciais (2)
        self.fig2, self.ax2 = plt.subplots(figsize=(8, 6), facecolor=COLOR_BG)
        self.ax2.set_facecolor("#0F172A")
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.tab_plot_campos)
        self.canvas2.get_tk_widget().pack(fill="both", expand=True)
        
        # Toolbar para o Canvas 2
        self.toolbar2 = NavigationToolbar2Tk(self.canvas2, self.tab_plot_campos)
        self.toolbar2.configure(bg=COLOR_CARD)
        for child in self.toolbar2.winfo_children():
            try: child.configure(bg=COLOR_CARD, fg=COLOR_TEXT)
            except: pass
        self.toolbar2.update()

    def carregar_configuracao_inicial(self):
        """Lê o arquivo JSON de configuração exemplo e popula a interface."""
        if not os.path.exists(self.caminho_json):
            self.txt_log.insert("end", f"[ERRO] {self.caminho_json} não encontrado.\n")
            return
            
        try:
            with open(self.caminho_json, 'r') as f:
                self.config_data = json.load(f)
            
            # Limpa widgets anteriores
            for widget in self.eletrodos_widgets:
                widget[1].master.destroy()
            self.eletrodos_widgets.clear()
            
            for widget in self.feixes_widgets:
                widget[1].master.destroy()
            self.feixes_widgets.clear()
            
            # 1. Popula Aba de Eletrodos (Tensões)
            if "geometries" in self.config_data:
                for idx, geom in enumerate(self.config_data["geometries"]):
                    frame_row = tk.Frame(self.tab_ctrl_eletrodos, bg=COLOR_CARD)
                    frame_row.pack(fill="x", padx=10, pady=8)
                    
                    tensao = geom.get("voltage", 0.0)
                    led_color = COLOR_PINK if tensao >= 0 else COLOR_BLUE
                    lbl_led = tk.Label(frame_row, text="● ", font=("Segoe UI", 10), bg=COLOR_CARD, fg=led_color)
                    lbl_led.pack(side="left")
                    
                    lbl_nome = tk.Label(frame_row, text=geom.get("name", "Eletrodo"), 
                                        font=("Segoe UI", 9, "bold"), bg=COLOR_CARD, fg=COLOR_TEXT, width=15, anchor="w")
                    lbl_nome.pack(side="left")
                    
                    entry_volt = tk.Entry(frame_row, width=12, bg="#1F2937", fg=COLOR_TEXT, 
                                          insertbackground="white", justify="center", bd=0, 
                                          font=("Consolas", 10, "bold"), highlightthickness=1, highlightbackground=COLOR_BORDER)
                    entry_volt.insert(0, str(tensao))
                    entry_volt.pack(side="right", padx=5)
                    
                    self.eletrodos_widgets.append((geom, entry_volt, lbl_led))
            
            # 2. Popula Aba de Feixes (Física de Partículas Dinâmica)
            if "beams" in self.config_data:
                for idx, feixe in enumerate(self.config_data["beams"]):
                    frame_feixe_card = tk.LabelFrame(self.tab_ctrl_feixes, text=f" {feixe.get('nome', 'Feixe')} ", 
                                                     font=("Segoe UI", 8, "bold"), bg=COLOR_CARD, fg=COLOR_TEXT,
                                                     bd=1, relief="flat", highlightthickness=1, highlightbackground=COLOR_BORDER)
                    frame_feixe_card.pack(fill="x", padx=10, pady=8)
                    
                    # Campo 1: Energia Cinética (eV)
                    frame_row1 = tk.Frame(frame_feixe_card, bg=COLOR_CARD)
                    frame_row1.pack(fill="x", padx=5, pady=4)
                    tk.Label(frame_row1, text="Energia (eV):", font=("Segoe UI", 8), bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="left")
                    entry_energy = tk.Entry(frame_row1, width=10, bg="#1F2937", fg=COLOR_TEXT, bd=0, justify="center", font=("Consolas", 9, "bold"))
                    entry_energy.insert(0, str(feixe.get("energy", 1000.0)))
                    entry_energy.pack(side="right")
                    
                    # Campo 2: Dispersão Inicial (m)
                    frame_row2 = tk.Frame(frame_feixe_card, bg=COLOR_CARD)
                    frame_row2.pack(fill="x", padx=5, pady=4)
                    tk.Label(frame_row2, text="Diâmetro (mm):", font=("Segoe UI", 8), bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="left")
                    entry_disp = tk.Entry(frame_row2, width=10, bg="#1F2937", fg=COLOR_TEXT, bd=0, justify="center", font=("Consolas", 9, "bold"))
                    # Exibe em milímetros para o usuário
                    entry_disp.insert(0, str(feixe.get("dispersion", 0.004) * 1000.0))
                    entry_disp.pack(side="right")

                    # Campo 3: Parâmetro Físico Carga (e)
                    frame_row3 = tk.Frame(frame_feixe_card, bg=COLOR_CARD)
                    frame_row3.pack(fill="x", padx=5, pady=4)
                    tk.Label(frame_row3, text="Carga (e):", font=("Segoe UI", 8), bg=COLOR_CARD, fg=COLOR_MUTED).pack(side="left")
                    entry_q = tk.Entry(frame_row3, width=10, bg="#1F2937", fg=COLOR_TEXT, bd=0, justify="center", font=("Consolas", 9, "bold"))
                    entry_q.insert(0, str(feixe.get("carga", 1.0)))
                    entry_q.pack(side="right")

                    self.feixes_widgets.append((feixe, entry_energy, entry_disp, entry_q))
                    
            self.txt_log.insert("end", "[INFO] Configuração carregada com sucesso!\n")
            self.atualizar_grafico()
            
        except Exception as e:
            self.txt_log.insert("end", f"[ERRO] Erro ao carregar JSON: {str(e)}\n")

    def salvar_dados_json(self):
        """Coleta as tensões e os novos parâmetros de partículas e grava no JSON."""
        try:
            # Salva eletrodos
            for geom, widget, led in self.eletrodos_widgets:
                valor_str = widget.get()
                tensao = float(valor_str)
                geom["voltage"] = tensao
                led.config(fg=COLOR_PINK if tensao >= 0 else COLOR_BLUE)
                
            # Salva feixes
            for feixe, entry_energy, entry_disp, entry_q in self.feixes_widgets:
                feixe["energy"] = float(entry_energy.get())
                # Converte de milímetros da GUI de volta para metros do motor C++
                feixe["dispersion"] = float(entry_disp.get()) / 1000.0
                feixe["carga"] = float(entry_q.get())
                
            with open(self.caminho_json, 'w') as f:
                json.dump(self.config_data, f, indent=4)
                
            self.txt_log.delete("1.0", "end")
            self.txt_log.insert("end", "[SUCESSO] Arquivo de cenário JSON atualizado!\n")
            self.atualizar_grafico()
        except ValueError:
            messagebox.showerror("Erro de Formatação", "Por favor, insira valores numéricos válidos.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar JSON: {str(e)}")

    def disparar_motor_wsl(self):
        """Aciona o WSL2 para rodar o motor físico do IBSimu e captura o log."""
        self.salvar_dados_json()
        self.txt_log.delete("1.0", "end")
        self.txt_log.insert("end", "[DISPARO] Enviando simulação para o kernel Linux (WSL2)...\n")
        self.update()
        
        comando = ["wsl", "./ibsimion_backend_v2", "config_scenario_example.json"]
        
        try:
            processo = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = processo.communicate()
            
            self.txt_log.insert("end", stdout)
            if stderr:
                self.txt_log.insert("end", f"\n[AVISO Linux]:\n{stderr}")
                
            if processo.returncode == 0:
                self.txt_log.insert("end", "\n[SUCESSO] Simulação concluída com êxito! Atualizando plots...\n")
                self.atualizar_grafico()
            else:
                self.txt_log.insert("end", f"\n[FALHA] Motor físico retornou código de erro: {processo.returncode}\n")
                
        except Exception as e:
            self.txt_log.insert("end", f"\n[ERRO DE BRIDGE] Falha ao disparar o WSL2:\n{str(e)}\n")

    def atualizar_grafico(self):
        """Re-renderiza o gráfico com a geometria de eletrodos, as novas trajetórias e equipotenciais."""
        self.ax1.clear()
        self.ax1.set_facecolor("#0F172A")
        
        self.ax2.clear()
        self.ax2.set_facecolor("#0F172A")
        
        # 1. Desenhar a estrutura das Lentes nos dois plots (em milímetros!)
        for ax in [self.ax1, self.ax2]:
            if "geometries" in self.config_data:
                for geom in self.config_data["geometries"]:
                    z_pos_mm = 0.0
                    if "translation" in geom and len(geom["translation"]) >= 3:
                        z_pos_mm = geom["translation"][2] * 1000
                        
                    tensao = geom.get("voltage", 0.0)
                    cor_eletrodo = COLOR_PINK if tensao > 0 else (COLOR_BLUE if tensao < 0 else "#6c757d")
                    
                    espessura_mm = 15.0
                    raio_int_mm = 15.0
                    comprimento_mm = 10.0
                    
                    rect_top = Rectangle((z_pos_mm, raio_int_mm), comprimento_mm, espessura_mm, 
                                         edgecolor=cor_eletrodo, facecolor=cor_eletrodo, alpha=0.35, linewidth=1.5)
                    rect_bot = Rectangle((z_pos_mm, -raio_int_mm - espessura_mm), comprimento_mm, espessura_mm, 
                                         edgecolor=cor_eletrodo, facecolor=cor_eletrodo, alpha=0.35, linewidth=1.5)
                    
                    ax.add_patch(rect_top)
                    ax.add_patch(rect_bot)
                    
                    ax.text(z_pos_mm + comprimento_mm/2, raio_int_mm + espessura_mm + 2, f"{geom.get('name')}\n{tensao:.1f} V", 
                            color=COLOR_TEXT, fontsize=7, ha="center", va="bottom", weight="bold")

        # 2. Plotar as Trajetórias Físicas Reais do feixe (Aba 1)
        if os.path.exists(self.caminho_trajetorias):
            trajetorias_por_especie = {}
            with open(self.caminho_trajetorias, 'r') as f:
                for linha in f:
                    if linha.startswith("#") or not linha.strip():
                        continue
                    partes = linha.split(",")
                    if len(partes) >= 5:
                        z = float(partes[0])
                        y = float(partes[1])
                        massa = float(partes[3])
                        
                        id_especie = "Íon Pesado (136.2 u)" if massa > 1.0 else "Elétron Rápido (0.00054 u)"
                        if id_especie not in trajetorias_por_especie:
                            trajetorias_por_especie[id_especie] = []
                        
                        trajetorias_por_especie[id_especie].append((z, y))
            
            for especie, pontos in trajetorias_por_especie.items():
                pontos = np.array(pontos)
                z_diffs = np.diff(pontos[:, 0])
                quebras = np.where(z_diffs < 0)[0] + 1
                raios = np.split(pontos, quebras)
                
                cor = COLOR_BLUE if "Íon" in especie else COLOR_PINK
                espessura_linha = 1.2 if "Íon" in especie else 0.8
                alfa = 0.7 if "Íon" in especie else 0.5
                
                for idx, raio in enumerate(raios):
                    if len(raio) > 1:
                        lbl = especie if idx == 0 else ""
                        self.ax1.plot(raio[:, 0] * 1000, raio[:, 1] * 1000, color=cor, 
                                      alpha=alfa, linewidth=espessura_linha, label=lbl)

        # 3. Plotar o Mapa Térmico e as Linhas Equipotenciais Reais do Solver (Aba 2)
        if os.path.exists("potential.txt"):
            try:
                with open("potential.txt", "r") as f:
                    header = f.readline().split()
                    nos_z = int(header[0])
                    nos_r = int(header[1])
                    h = float(header[2])
                
                pot_matrix = np.loadtxt("potential.txt", skiprows=1)
                
                # Malha 2D do espaço para plotagem (Z, R em milímetros)
                zs = np.linspace(0, (nos_z-1) * h * 1000, nos_z)
                rs = np.linspace(0, (nos_r-1) * h * 1000, nos_r)
                Z_grid, R_grid = np.meshgrid(zs, rs)
                
                # Espelha a matriz de potencial para baixo do eixo de simetria (R negativo) para visualização coaxial completa
                Z_double = np.vstack((Z_grid, Z_grid[::-1, :]))
                R_double = np.vstack((R_grid, -R_grid[::-1, :]))
                pot_double = np.vstack((pot_matrix, pot_matrix[::-1, :]))
                
                # Renderiza o mapa térmico do potencial elétrico (Background colormap)
                im = self.ax2.pcolormesh(Z_double, R_double, pot_double, cmap="bwr", shading="auto", alpha=0.6, vmin=-5000, vmax=5000)
                
                # Plota as linhas de contorno de voltagem (Equipotenciais)
                n_linhas = 20
                contornos = self.ax2.contour(Z_double, R_double, pot_double, n_linhas, colors="#f5f5f5", linewidths=0.5, alpha=0.5)
                self.ax2.clabel(contornos, inline=True, fontsize=7, fmt="%d V")
                
            except Exception as e:
                self.txt_log.insert("end", f"[WARNING Plot]: Erro ao ler mapa de potenciais: {str(e)}\n")

        # Configurações de Eixos e Escalas Científicas
        z_max_mm = self.config_data.get("mesh_dimensions", {}).get("z_max", 0.36) * 1000
        r_max_mm = self.config_data.get("mesh_dimensions", {}).get("r_max", 0.035) * 1000
        
        for ax in [self.ax1, self.ax2]:
            ax.set_xlim(-10, z_max_mm + 10)
            ax.set_ylim(-r_max_mm - 5, r_max_mm + 5)
            ax.set_xlabel("Posição Coaxial Z (mm)", color=COLOR_MUTED, fontname="Segoe UI", weight="semibold", fontsize=9)
            ax.set_ylabel("Deflexão Radial R (mm)", color=COLOR_MUTED, fontname="Segoe UI", weight="semibold", fontsize=9)
            ax.grid(True, which="both", color="#1E293B", linestyle="--", linewidth=0.5)
            ax.axhline(0, color="#ffffff", linestyle="-.", linewidth=0.8, alpha=0.3)
            ax.tick_params(colors=COLOR_MUTED, labelsize=8)
            
        self.ax1.set_title("Visualização de Trajetórias Coaxiais e Lentes", color=COLOR_TEXT, fontsize=11, fontname="Segoe UI", weight="bold", pad=12)
        self.ax2.set_title("Mapa de Linhas Equipotenciais (EpotField)", color=COLOR_TEXT, fontsize=11, fontname="Segoe UI", weight="bold", pad=12)
        
        self.ax1.legend(facecolor=COLOR_CARD, edgecolor=COLOR_BORDER, labelcolor=COLOR_TEXT, loc="upper right", fontsize=8)
        
        self.fig1.tight_layout()
        self.fig2.tight_layout()
        
        self.canvas1.draw()
        self.canvas2.draw()

if __name__ == "__main__":
    app = IBSimionApp()
    app.mainloop()