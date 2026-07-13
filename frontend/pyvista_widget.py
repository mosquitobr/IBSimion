# -*- coding: utf-8 -*-
# pyvista_widget.py
# Optimized 3D Viewport Widget for IBSimion v2.0.1.e4l

import os
import numpy as np
import pyvista as pv
pv.global_theme.allow_empty_mesh = True
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import QVBoxLayout, QWidget

def resolve_path(path):
    """Resolve caminhos relativos à pasta data/ do projeto de forma portável."""
    if not path:
        return ""
    p = path.replace("\\", "/")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    
    if p.startswith("./data/") or p.startswith("data/") or p.startswith("../data/"):
        if p.startswith("../data/"):
            normalized = p[3:]
        else:
            normalized = p.lstrip("./")
        return os.path.abspath(os.path.join(repo_root, normalized))
        
    if not os.path.dirname(p):
        data_path = os.path.join(repo_root, "data", p)
        if os.path.exists(data_path):
            return os.path.abspath(data_path)
            
    return os.path.abspath(path)

class PyVistaWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # PyVista Interactor
        self.plotter = QtInteractor(self)
        self.layout.addWidget(self.plotter)
        
        # Default styling
        self.theme_mode = "dark"
        self.plotter.set_background("#E5E7EB")
        self.plotter.show_axes()
        self.plotter.show_grid(color="#6B7280", font_size=10)
        
        # Tracks dictionary for fast lookup/removal
        self.trajectories = []
        self.electrode_mesh = None
        
        # Cache para reconstrução sob alteração de tema
        self.geometries_cache = None
        self.obj_path_cache = None
        
        # Caching de malhas originais para fatiamento reativo
        self.loaded_meshes = []
        self.pic_mode = False
        self.fading_trail = False
        self.trail_opacity = 0.85


    def set_theme_mode(self, theme_mode):
        """Aplica cores de fundo, eixos e contraste dinâmico de triângulos com base no tema."""
        self.theme_mode = theme_mode
        color_rgb = (0, 0, 0) if theme_mode == "light" else (1, 1, 1)
        grid_color = "#D1D5DB" if theme_mode == "light" else "#1F2937"
        bg_color = "#F3F4F6" if theme_mode == "light" else "#0B0F19"
        
        self.plotter.set_background(bg_color)
        
        # Update theme font color
        self.plotter.theme.font.color = "black" if theme_mode == "light" else "white"
        
        # Redraw grid with correct colors and larger font size
        self.plotter.show_grid(color=grid_color, font_size=10)
        
        # Update cube axes colors and font sizes if they exist
        cube_axes = getattr(self.plotter, 'cube_axes_actor', None)
        if cube_axes:
            for i in range(3):
                try:
                    cube_axes.GetTitleTextProperty(i).SetColor(*color_rgb)
                    cube_axes.GetTitleTextProperty(i).SetFontSize(12)
                except Exception:
                    pass
                try:
                    cube_axes.GetLabelTextProperty(i).SetColor(*color_rgb)
                    cube_axes.GetLabelTextProperty(i).SetFontSize(10)
                except Exception:
                    pass
                
        # Update scalar bars text colors and font sizes
        for name, scalar_bar in self.plotter.scalar_bars.items():
            try:
                scalar_bar.GetTitleTextProperty().SetColor(*color_rgb)
                scalar_bar.GetTitleTextProperty().SetFontSize(12)
            except Exception:
                pass
            try:
                scalar_bar.GetLabelTextProperty().SetColor(*color_rgb)
                scalar_bar.GetLabelTextProperty().SetFontSize(10)
            except Exception:
                pass
            try:
                scalar_bar.GetAnnotationTextProperty().SetColor(*color_rgb)
                scalar_bar.GetAnnotationTextProperty().SetFontSize(10)
            except Exception:
                pass
                
        # Reconstrói os meshes de geometria no plotter com o novo tema
        if self.geometries_cache is not None:
            self.load_geometry_data(self.geometries_cache, self.obj_path_cache)
            
        self.plotter.render()

    def clear_scene(self):
        """Limpa a cena mantendo o grid de eixos em conformidade com o tema."""
        self.plotter.clear()
        self.plotter.show_axes()
        
        theme_mode = getattr(self, 'theme_mode', 'dark')
        grid_color = "#D1D5DB" if theme_mode == "light" else "#1F2937"
        self.plotter.show_grid(color=grid_color, font_size=10)
        
        # Re-apply colors to cube axes
        color_rgb = (0, 0, 0) if theme_mode == "light" else (1, 1, 1)
        cube_axes = getattr(self.plotter, 'cube_axes_actor', None)
        if cube_axes:
            for i in range(3):
                try:
                    cube_axes.GetTitleTextProperty(i).SetColor(*color_rgb)
                    cube_axes.GetTitleTextProperty(i).SetFontSize(12)
                    cube_axes.GetLabelTextProperty(i).SetColor(*color_rgb)
                    cube_axes.GetLabelTextProperty(i).SetFontSize(10)
                except Exception:
                    pass
                
        self.trajectories = []
        self.electrode_mesh = None
        self.geometries_cache = None
        self.obj_path_cache = None
        self.loaded_meshes = []

    def load_geometry_data(self, geometries_list, obj_path=None):
        """Carrega e renderiza STL nativamente em alta resolução, e usa OBJ de fallback para DXF/malhas gerais."""
        # Salva em cache para re-renderização sob troca de tema
        self.geometries_cache = geometries_list
        self.obj_path_cache = obj_path
        
        # Limpar atores de geometria anteriores
        for name in list(self.plotter.actors.keys()):
            if name.startswith("stl_electrode_") or name == "electrodes":
                self.plotter.remove_actor(name)
                
        self.electrode_mesh = None
        self.loaded_meshes = []
        has_stl = False
        
        theme_mode = getattr(self, 'theme_mode', 'dark')
        
        # Paleta de cores com base no tema para contraste perfeito
        # Eletrodos mais escuros no tema claro e mais claros no tema escuro
        el_color = "#4B5563" if theme_mode == "light" else "#9CA3AF"
        el_edge = "#111827" if theme_mode == "light" else "#4B5563"
        
        # Carrega cada STL original listado
        if geometries_list:
            for idx, geom in enumerate(geometries_list):
                file_path = geom.get("file_path", "")
                if not file_path or not file_path.lower().endswith(".stl"):
                    continue
                    
                abs_path = resolve_path(file_path)
                if os.path.exists(abs_path):
                    try:
                        # Lê o arquivo STL original via PyVista
                        mesh = pv.read(abs_path)
                        
                        # Aplica escala
                        scale = geom.get("scale", 1.0)
                        mesh.scale(scale, inplace=True)
                        
                        # Aplica translação
                        tx, ty, tz = geom.get("translation", [0.0, 0.0, 0.0])
                        mesh.translate([tx, ty, tz], inplace=True)
                        
                        actor_name = f"stl_electrode_{idx}_{geom.get('name', 'Solid')}"
                        self.plotter.add_mesh(
                            mesh,
                            color=el_color,
                            opacity=0.45,
                            show_edges=True,
                            edge_color=el_edge,
                            name=actor_name
                        )
                        has_stl = True
                        
                        self.loaded_meshes.append({
                            "mesh": mesh.copy(),
                            "color": el_color,
                            "opacity": 0.45,
                            "show_edges": True,
                            "edge_color": el_edge,
                            "name": actor_name
                        })
                    except Exception as e:
                        print(f"Error loading STL directly in PyVista: {e}")
        
        # Carrega fallback/DXF do geometry.obj se disponível
        if obj_path and os.path.exists(obj_path):
            try:
                self.electrode_mesh = pv.read(obj_path)
                # Se renderizou STL, o fallback é secundário (exibe DXF), reduzimos a opacidade
                opacity_val = 0.15 if has_stl else 0.35
                obj_color = "#374151" if theme_mode == "light" else "silver"
                
                self.plotter.add_mesh(
                    self.electrode_mesh, 
                    color=obj_color, 
                    opacity=opacity_val, 
                    show_edges=True, 
                    edge_color=el_edge,
                    name="electrodes"
                )
                
                self.loaded_meshes.append({
                    "mesh": self.electrode_mesh.copy(),
                    "color": obj_color,
                    "opacity": opacity_val,
                    "show_edges": True,
                    "edge_color": el_edge,
                    "name": "electrodes"
                })
            except Exception as e:
                print(f"Error loading geometry fallback mesh: {e}")
                
        self.plotter.reset_camera()
        return True

    def load_geometry(self, obj_path):
        """Mantenabilidade e retrocompatibilidade com chamadas herdadas."""
        return self.load_geometry_data(self.geometries_cache, obj_path)

    def load_trajectories(self, traj_path, color_by='mass', sample_step=1):
        """Lê e renderiza os arquivos de trajetórias simulados."""
        if not os.path.exists(traj_path):
            print(f"Trajectory file not found: {traj_path}")
            return False
            
        try:
            self.trajectories = []
            current_traj = None
            
            with open(traj_path, "r") as f:
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
                        self.trajectories.append(current_traj)
                    else:
                        parts = line.strip().split()
                        if current_traj is not None:
                            if len(parts) == 4:
                                t, x, y, z = map(float, parts)
                                if self.pic_mode:
                                    current_traj["points"].append([t, x, y, z])
                                else:
                                    current_traj["points"].append([x, y, z])
                            elif len(parts) == 3:
                                x, y, z = map(float, parts)
                                if self.pic_mode:
                                    current_traj["points"].append([0.0, x, y, z])
                                else:
                                    current_traj["points"].append([x, y, z])
            
            self.plot_trajectories(color_by, sample_step=sample_step)
            return True
        except Exception as e:
            print(f"Error loading trajectories: {e}")
            return False

    def plot_trajectories(self, color_by='mass', sample_step=1):
        """Renderiza as trajetórias com cores e legendas de eixos em tamanho High-DPI."""
        try:
            sample_step = int(sample_step)
            if sample_step < 1:
                sample_step = 1
        except Exception:
            sample_step = 1

        for name in list(self.plotter.actors.keys()):
            if name.startswith("track_"):
                self.plotter.remove_actor(name)
                
        if self.pic_mode:
            return  # Hide complete trajectory lines in PIC mode
            
        if not self.trajectories:
            return
            
        theme_mode = getattr(self, 'theme_mode', 'dark')
        text_color = 'black' if theme_mode == 'light' else 'white'

        colors_palette = ["#3B82F6", "#F43F5E", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4"]
        unique_masses = sorted(list(set(t["mass"] for t in self.trajectories)))
        unique_charges = sorted(list(set(t["charge"] for t in self.trajectories)))
        unique_currents = sorted(list(set(t["curr"] for t in self.trajectories)))

        for idx, traj in enumerate(self.trajectories):
            if idx % sample_step != 0:
                continue
                
            if traj is None:
                continue
            traj_points = traj.get("points")
            if traj_points is None:
                continue
            try:
                traj_data = np.array(traj_points)
            except Exception:
                continue
            if traj_data is not None and hasattr(traj_data, "shape") and len(traj_data.shape) >= 2:
                if traj_data.shape[0] >= 2 and traj_data.shape[1] >= 2:
                    pts = traj_data
                else:
                    continue
            else:
                continue
                
            if pts.shape[1] == 4:
                xyz_pts = pts[:, 1:]
            else:
                xyz_pts = pts
            poly = pv.MultipleLines(points=xyz_pts)
            
            if color_by == 'species':
                c_idx = idx % len(colors_palette)
                color = colors_palette[c_idx]
            elif color_by == 'mass':
                m_idx = unique_masses.index(traj["mass"]) if traj["mass"] in unique_masses else 0
                c_idx = m_idx % len(colors_palette)
                color = colors_palette[c_idx]
            elif color_by == 'charge':
                if traj["charge"] > 0:
                    color = "#10B981"
                elif traj["charge"] < 0:
                    color = "#F43F5E"
                else:
                    color = "#9CA3AF"
            elif color_by == 'energy':
                z_coords = xyz_pts[:, 2]
                poly.point_data["Z"] = z_coords
                scalar_bar_args = {
                    'title_font_size': 12,
                    'label_font_size': 10,
                    'color': text_color,
                    'fmt': '%.2e'
                }
                self.plotter.add_mesh(
                    poly,
                    scalars="Z",
                    cmap="plasma",
                    line_width=2.5,
                    name=f"track_{traj['id']}",
                    scalar_bar_args=scalar_bar_args
                )
                continue
            elif color_by == 'current':
                curr_idx = unique_currents.index(traj["curr"]) if traj["curr"] in unique_currents else 0
                c_idx = curr_idx % len(colors_palette)
                color = colors_palette[c_idx]
            else:
                color = "#3B82F6"
                
            self.plotter.add_mesh(
                poly, 
                color=color, 
                line_width=2.5, 
                name=f"track_{traj['id']}"
            )
            
        self.plotter.render()
        
    def load_pic_snapshot(self, snapshot_data_or_path, current_time=None):
        """Carrega e renderiza snapshots de partículas PIC."""
        # Validação defensiva explícita de dados de entrada
        is_valid = True
        if snapshot_data_or_path is None:
            is_valid = False
        elif isinstance(snapshot_data_or_path, str):
            if not os.path.exists(snapshot_data_or_path) or os.path.getsize(snapshot_data_or_path) == 0:
                is_valid = False
        else:
            try:
                if not hasattr(snapshot_data_or_path, 'ndim') or snapshot_data_or_path.size == 0 or len(snapshot_data_or_path) == 0:
                    is_valid = False
            except Exception:
                is_valid = False

        if not is_valid:
            try:
                actors_keys = list(self.plotter.actors.keys())
                for name in actors_keys:
                    if name.startswith("pic_particles"):
                        self.plotter.remove_actor(name)
                if "pic_trails" in actors_keys:
                    self.plotter.remove_actor("pic_trails")
            except Exception as e:
                print(f"Error cleaning actors in load_pic_snapshot (invalid snapshot): {e}")
            self.plotter.render()
            return True

        # Amostragem e opacidade obtidos logo após a validação
        sample_step = getattr(self, "sample_step", 1)
        trail_opacity = getattr(self, "trail_opacity", 0.85)

        try:
            # Limpeza inicial de atores PIC antigos
            try:
                actors_keys = list(self.plotter.actors.keys())
                for name in actors_keys:
                    if name.startswith("pic_particles"):
                        self.plotter.remove_actor(name)
                if "pic_trails" in actors_keys:
                    self.plotter.remove_actor("pic_trails")
            except Exception as e:
                print(f"Error cleaning actors in load_pic_snapshot: {e}")

            # If trajectories are available, render the dynamic state of all particles at current_time
            if current_time is not None and hasattr(self, "trajectories") and self.trajectories:
                pts_list = []
                mass_list = []
                charge_list = []
                for idx_traj, traj in enumerate(self.trajectories):
                    if idx_traj % sample_step != 0:
                        continue
                        
                    if traj is None:
                        continue
                    traj_points = traj.get("points")
                    if traj_points is None:
                        continue
                    try:
                        traj_data = np.array(traj_points)
                    except Exception:
                        continue
                    if traj_data is not None and hasattr(traj_data, "shape") and len(traj_data.shape) >= 2:
                        if traj_data.shape[0] > 0 and traj_data.shape[1] >= 2:
                            pts = traj_data
                        else:
                            continue
                    else:
                        continue
                    
                    t = pts[:, 0]
                    # Rotina de sumiço fluido: se o tempo de amostragem passou do fim ou antes do início, a partícula não é renderizada
                    if current_time < t[0] or current_time > t[-1]:
                        continue
                        
                    idx = np.searchsorted(t, current_time)
                    if idx == 0:
                        pos = pts[0, 1:]
                    else:
                        t0 = t[idx - 1]
                        t1 = t[idx]
                        p0 = pts[idx - 1, 1:]
                        p1 = pts[idx, 1:]
                        fraction = (current_time - t0) / (t1 - t0 + 1e-20)
                        pos = p0 + fraction * (p1 - p0)
                    
                    pts_list.append(pos)
                    mass_list.append(traj["mass"])
                    charge_list.append(traj["charge"])
                
                # Renderização dos rastros se a flag fading_trail estiver ativa
                if getattr(self, "fading_trail", False) and self.trajectories:
                    all_times = []
                    for t_tr in self.trajectories:
                        if t_tr is None:
                            continue
                        traj_points = t_tr.get("points")
                        if traj_points is None:
                            continue
                        try:
                            traj_data = np.array(traj_points)
                        except Exception:
                            continue
                        if traj_data is not None and hasattr(traj_data, "shape") and len(traj_data.shape) >= 2:
                            if traj_data.shape[0] > 0 and traj_data.shape[1] >= 2:
                                all_times.append(traj_data[0][0])
                                all_times.append(traj_data[-1][0])
                            else:
                                continue
                        else:
                            continue
                    if all_times:
                        total_time_range = max(all_times) - min(all_times)
                        trail_dt = total_time_range * 0.08  # Rastro com 8% do range total
                    else:
                        trail_dt = 1e-8
                        
                    pts_accumulator = []
                    lines_accumulator = []
                    opacity_vals = []
                    current_pt_idx = 0
                    
                    for idx_traj, traj in enumerate(self.trajectories):
                        if idx_traj % sample_step != 0:
                            continue
                            
                        if traj is None:
                            continue
                        traj_points = traj.get("points")
                        if traj_points is None:
                            continue
                        try:
                            traj_data = np.array(traj_points)
                        except Exception:
                            continue
                        if traj_data is not None and hasattr(traj_data, "shape") and len(traj_data.shape) >= 2:
                            if traj_data.shape[0] > 0 and traj_data.shape[1] >= 2:
                                pts = traj_data
                            else:
                                continue
                        else:
                            continue
                        t = pts[:, 0]
                        if current_time < t[0]:
                            continue
                        if current_time > t[-1] + trail_dt:
                            continue
                            
                        # Seleciona os pontos pertencentes à janela de tempo do rastro [current_time - trail_dt, current_time]
                        mask = (t <= current_time) & (t >= current_time - trail_dt)
                        indices = np.where(mask)[0]
                        
                        segment_pts = []
                        segment_times = []
                        
                        for i_idx in indices:
                            segment_pts.append(pts[i_idx, 1:])
                            segment_times.append(pts[i_idx, 0])
                            
                        # Se a partícula está ativa, interpola a ponta exata
                        if current_time <= t[-1]:
                            last_idx = np.searchsorted(t, current_time)
                            if last_idx > 0 and last_idx < len(t):
                                t0, t1 = t[last_idx - 1], t[last_idx]
                                p0, p1 = pts[last_idx - 1, 1:], pts[last_idx, 1:]
                                fraction = (current_time - t0) / (t1 - t0 + 1e-20)
                                pos = p0 + fraction * (p1 - p0)
                                segment_pts.append(pos)
                                segment_times.append(current_time)
                            elif last_idx == 0:
                                segment_pts.append(pts[0, 1:])
                                segment_times.append(t[0])
                        else:
                            # Se a partícula já saiu, garante a ponta de saída
                            if len(indices) == 0 or indices[-1] != len(t) - 1:
                                segment_pts.append(pts[-1, 1:])
                                segment_times.append(t[-1])
                            
                        if len(segment_pts) >= 2:
                            n_pts = len(segment_pts)
                            pts_accumulator.append(np.array(segment_pts))
                            lines_accumulator.append([n_pts] + list(range(current_pt_idx, current_pt_idx + n_pts)))
                            
                            for st in segment_times:
                                # Mapeia opacidade linear (fading) de 0 (mais antigo) a 1 (partícula)
                                op = (st - (current_time - trail_dt)) / (trail_dt + 1e-20)
                                op = max(0.0, min(1.0, op)) * self.trail_opacity
                                opacity_vals.append(op)
                                
                            current_pt_idx += n_pts
                            
                    if pts_accumulator:
                        flat_pts = np.vstack(pts_accumulator)
                        flat_lines = np.hstack(lines_accumulator)
                        trail_mesh = pv.PolyData(flat_pts, lines=flat_lines)
                        trail_mesh.point_data["opacity"] = np.array(opacity_vals)
                        
                        actor = self.plotter.add_mesh(
                            trail_mesh,
                            opacity=np.array(opacity_vals),
                            color="#3B82F6",
                            line_width=2.0,
                            name="pic_trails"
                        )
                        if actor is not None:
                            try:
                                actor.prop.opacity = self.trail_opacity
                            except Exception:
                                pass

                
                if pts_list:
                    pts = np.array(pts_list)
                    point_cloud = pv.PolyData(pts)
                    masses = np.array(mass_list)
                    
                    unique_masses = sorted(list(set(mass_list)))
                    colors_palette = ["#3B82F6", "#F43F5E", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4"]
                    from matplotlib.colors import to_rgb
                    palette_rgb = [to_rgb(c) for c in colors_palette]
                    
                    pt_colors = []
                    for m in masses:
                        m_idx = unique_masses.index(m) if m in unique_masses else 0
                        c_idx = m_idx % len(palette_rgb)
                        pt_colors.append(palette_rgb[c_idx])
                    
                    point_cloud.point_data["colors"] = np.array(pt_colors)
                    self.plotter.add_mesh(
                        point_cloud,
                        scalars="colors",
                        rgb=True,
                        point_size=5.0,  # Reduzido para pontos nítidos
                        render_points_as_spheres=False,  # direct pixel points
                        name="pic_particles"
                    )
                self.plotter.render()
                return True
                    
            if isinstance(snapshot_data_or_path, str):
                if not os.path.exists(snapshot_data_or_path):
                    return False
                if os.path.getsize(snapshot_data_or_path) == 0:
                    self.plotter.render()
                    return True
                try:
                    data = np.loadtxt(snapshot_data_or_path)
                except Exception as ex:
                    print(f"Empty snapshot or error: {ex}")
                    self.plotter.render()
                    return True
            else:
                data = snapshot_data_or_path
 
            if data is None or not hasattr(data, 'ndim') or data.size == 0 or len(data) == 0:
                self.plotter.render()
                return True
                
            # Apply amostragem to loaded snapshot points
            if sample_step > 1:
                data = data[::sample_step]
                
            if data.ndim == 1:
                data = np.expand_dims(data, axis=0)
 
            # Columns in data: t, x, vx, y, vy, z, vz, [mass, charge]
            pts = np.column_stack((data[:, 1], data[:, 3], data[:, 5]))
            point_cloud = pv.PolyData(pts)
            
            # Dynamic color mapping by mass (column 7) if present
            if data.shape[1] >= 8:
                masses = data[:, 7]
                unique_masses = sorted(list(set(masses)))
                
                # Align unique masses with trajectories if possible
                if hasattr(self, "trajectories") and self.trajectories:
                    traj_masses = sorted(list(set(t["mass"] for t in self.trajectories)))
                    for m in traj_masses:
                        if m not in unique_masses:
                            unique_masses.append(m)
                    unique_masses.sort()
                
                colors_palette = ["#3B82F6", "#F43F5E", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4"]
                from matplotlib.colors import to_rgb
                palette_rgb = [to_rgb(c) for c in colors_palette]
                
                pt_colors = []
                for m in masses:
                    m_idx = unique_masses.index(m) if m in unique_masses else 0
                    c_idx = m_idx % len(palette_rgb)
                    pt_colors.append(palette_rgb[c_idx])
                
                point_cloud.point_data["colors"] = np.array(pt_colors)
                
                self.plotter.add_mesh(
                    point_cloud,
                    scalars="colors",
                    rgb=True,
                    point_size=5.0,
                    render_points_as_spheres=False,
                    name="pic_particles"
                )
            else:
                # Fallback to default red
                self.plotter.add_mesh(
                    point_cloud, 
                    color="#F43F5E", 
                    point_size=5.0, 
                    render_points_as_spheres=False, 
                    name="pic_particles"
                )
                
            self.plotter.render()
            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error loading PIC snapshot: {e}")
            return False

    def apply_clipping_plane(self, coord, normal=(0, 0, -1), origin=None):
        """Aplica corte transversal (clipping) nas geometrias 3D."""
        if self.electrode_mesh is None:
            return
        
        try:
            self.plotter.remove_actor("electrodes")
            
            if origin is None:
                if normal == (0, 0, -1):
                    origin = (0, 0, coord)
                elif normal == (0, -1, 0):
                    origin = (0, coord, 0)
                elif normal == (-1, 0, 0):
                    origin = (coord, 0, 0)
                else:
                    origin = (0, 0, coord)
                
            clipped = self.electrode_mesh.clip(normal=normal, origin=origin)
            
            theme_mode = getattr(self, 'theme_mode', 'dark')
            el_edge = "#111827" if theme_mode == "light" else "#4B5563"
            obj_color = "#374151" if theme_mode == "light" else "silver"
            
            self.plotter.add_mesh(
                clipped,
                color=obj_color,
                opacity=0.35,
                show_edges=True,
                edge_color=el_edge,
                name="electrodes"
            )
            self.plotter.render()
        except Exception as e:
            print(f"Error applying clipping plane: {e}")

    def apply_reactive_clipping(self, clip_x=None, clip_y=None, clip_z=None):
        """Aplica cortes transversais reativos em X, Y, e/ou Z a todos os meshes de eletrodos."""
        if not hasattr(self, 'loaded_meshes') or not self.loaded_meshes:
            return
            
        for mesh_info in self.loaded_meshes:
            mesh = mesh_info["mesh"]
            actor_name = mesh_info["name"]
            
            # Remove previous actor
            try:
                if hasattr(self.plotter, "actors") and actor_name in self.plotter.actors:
                    self.plotter.remove_actor(actor_name)
            except Exception as e:
                print(f"Error removing actor {actor_name} in apply_reactive_clipping: {e}")
            
            # Apply clipping sequentially if enabled
            clipped_mesh = mesh
            try:
                if clip_x is not None:
                    clipped_mesh = clipped_mesh.clip(normal=(-1, 0, 0), origin=(clip_x, 0, 0))
                if clip_y is not None:
                    clipped_mesh = clipped_mesh.clip(normal=(0, -1, 0), origin=(0, clip_y, 0))
                if clip_z is not None:
                    clipped_mesh = clipped_mesh.clip(normal=(0, 0, -1), origin=(0, 0, clip_z))
                
                self.plotter.add_mesh(
                    clipped_mesh,
                    color=mesh_info["color"],
                    opacity=mesh_info["opacity"],
                    show_edges=mesh_info["show_edges"],
                    edge_color=mesh_info["edge_color"],
                    name=actor_name
                )
            except Exception:
                pass
        self.plotter.render()

    def get_geometry_bounds(self):
        """Retorna os limites (bounds) das geometrias ativas [xmin, xmax, ymin, ymax, zmin, zmax]."""
        xmin, xmax = -0.05, 0.05
        ymin, ymax = -0.05, 0.05
        zmin, zmax = 0.0, 0.35
        
        has_bounds = False
        if self.electrode_mesh is not None:
            try:
                b = self.electrode_mesh.bounds
                if len(b) == 6:
                    xmin, xmax, ymin, ymax, zmin, zmax = b
                    has_bounds = True
            except Exception:
                pass
                
        if not has_bounds:
            try:
                if hasattr(self.plotter, "actors"):
                    actors_dict = dict(self.plotter.actors.items())
                    for name, actor in actors_dict.items():
                        if name.startswith("stl_electrode_"):
                            try:
                                b = actor.GetBounds()
                                if b and len(b) == 6:
                                    if not has_bounds:
                                        xmin, xmax, ymin, ymax, zmin, zmax = b
                                        has_bounds = True
                                    else:
                                        xmin = min(xmin, b[0])
                                        xmax = max(xmax, b[1])
                                        ymin = min(ymin, b[2])
                                        ymax = max(ymax, b[3])
                                        zmin = min(zmin, b[4])
                                        zmax = max(zmax, b[5])
                            except Exception:
                                pass
            except Exception as e:
                print(f"Error accessing actors in get_geometry_bounds: {e}")
        return [xmin, xmax, ymin, ymax, zmin, zmax]

    def render_heatmap_overlay(self, h_coords, v_coords, matrix, plane_orient=1, coord_val=0.0, log_scale=False, title=""):
        """Renderiza a sobreposição escalar (heatmap) na viewport 3D com interpolação bilinear suave."""
        try:
            actors_keys = list(self.plotter.actors.keys())
            if "heatmap_overlay" in actors_keys:
                self.plotter.remove_actor("heatmap_overlay")
                
            last_title = getattr(self, "last_heatmap_title", None)
            if last_title:
                try:
                    self.plotter.remove_scalar_bar(title=last_title)
                except Exception:
                    pass
                self.last_heatmap_title = None
        except Exception as e:
            print(f"Error cleaning heatmap actors in render_heatmap_overlay: {e}")
            
        if matrix is None or len(h_coords) < 2 or len(v_coords) < 2:
            return
            
        try:
            if plane_orient == 0:  # XY (Z = coord_val)
                grid = pv.RectilinearGrid(h_coords, v_coords, np.array([coord_val]))
                scalars = matrix.flatten(order='C')
            elif plane_orient == 1:  # XZ (Y = coord_val)
                grid = pv.RectilinearGrid(v_coords, np.array([coord_val]), h_coords)
                scalars = matrix.flatten(order='F')
            else:  # YZ (X = coord_val)
                grid = pv.RectilinearGrid(np.array([coord_val]), v_coords, h_coords)
                scalars = matrix.flatten(order='F')
                
            # Aplicar valor absoluto para admitir cargas negativas e densidades
            scalars = np.abs(scalars)
            if log_scale:
                # Tratamento do piso logarítmico
                scalars = np.maximum(scalars, 1e-12)
                
            n_points = grid.n_points
            if len(scalars) != n_points:
                print(f"Warning: scalars size {len(scalars)} does not match grid points {n_points}. Reshaping...")
                if len(scalars) < n_points:
                    scalars = np.pad(scalars, (0, n_points - len(scalars)), mode='constant')
                else:
                    scalars = scalars[:n_points]
                    
            grid.point_data["scalars"] = scalars
            
            theme_mode = getattr(self, 'theme_mode', 'dark')
            text_color = 'black' if theme_mode == 'light' else 'white'
            
            scalar_bar_args = {
                'title': title,
                'title_font_size': 12,
                'label_font_size': 10,
                'color': text_color,
                'fmt': '%.2e'
            }
            
            actor = self.plotter.add_mesh(
                grid,
                scalars="scalars",
                cmap="plasma",
                opacity=0.85,
                log_scale=log_scale,
                name="heatmap_overlay",
                scalar_bar_args=scalar_bar_args
            )
            if actor is not None:
                actor.prop.interpolation = 'Gouraud'  # Interpolação bilinear suave via VTK actor properties
            self.last_heatmap_title = title
            self.plotter.render()
        except Exception as e:
            print(f"Error rendering heatmap overlay: {e}")

    def export_screenshot(self, filepath):
        """Exporta o buffer atual em formato PNG."""
        try:
            self.plotter.screenshot(filepath)
            return True
        except Exception as e:
            print(f"Error exporting screenshot: {e}")
            return False

    def reset_camera_to_actors(self):
        """Executa um reset_camera focado estritamente nas caixas delimitadoras dos atores ativos."""
        try:
            xmin, xmax = float('inf'), float('-inf')
            ymin, ymax = float('inf'), float('-inf')
            zmin, zmax = float('inf'), float('-inf')
            
            # 1. Coletar bounds das trajetórias
            has_elements = False
            if self.trajectories:
                for traj in self.trajectories:
                    if traj is None:
                        continue
                    traj_points = traj.get("points")
                    if traj_points is None:
                        continue
                    try:
                        traj_data = np.array(traj_points)
                    except Exception:
                        continue
                    if traj_data is not None and hasattr(traj_data, "shape") and len(traj_data.shape) >= 2:
                        if traj_data.shape[0] > 0 and traj_data.shape[1] >= 2:
                            pts = traj_data
                        else:
                            continue
                    else:
                        continue
                    
                    # Detecção dinâmica de dimensionalidade (evita ValueError de desempacotamento)
                    if pts.shape[1] == 4:
                        xyz_pts = pts[:, 1:]
                    else:
                        xyz_pts = pts
                    has_elements = True
                    t_xmin, t_ymin, t_zmin = np.min(xyz_pts, axis=0)
                    t_xmax, t_ymax, t_zmax = np.max(xyz_pts, axis=0)
                    xmin = min(xmin, t_xmin)
                    xmax = max(xmax, t_xmax)
                    ymin = min(ymin, t_ymin)
                    ymax = max(ymax, t_ymax)
                    zmin = min(zmin, t_zmin)
                    xmax_val = t_xmax  # dummy check/compilation check
                    zmax = max(zmax, t_zmax)
                        
            # 2. Coletar bounds dos eletrodos em self.electrode_mesh
            if self.electrode_mesh is not None:
                try:
                    b = self.electrode_mesh.bounds
                    if len(b) == 6:
                        has_elements = True
                        xmin = min(xmin, b[0])
                        xmax = max(xmax, b[1])
                        ymin = min(ymin, b[2])
                        ymax = max(ymax, b[3])
                        zmin = min(zmin, b[4])
                        zmax = max(zmax, b[5])
                except Exception:
                    pass
                    
            # 3. Coletar bounds dos atores STL individuais
            try:
                if hasattr(self.plotter, "actors"):
                    actors_dict = dict(self.plotter.actors.items())
                    for name, actor in actors_dict.items():
                        if name.startswith("stl_electrode_"):
                            try:
                                b = actor.GetBounds()
                                if b and len(b) == 6:
                                    has_elements = True
                                    xmin = min(xmin, b[0])
                                    xmax = max(xmax, b[1])
                                    ymin = min(ymin, b[2])
                                    ymax = max(ymax, b[3])
                                    zmin = min(zmin, b[4])
                                    zmax = max(zmax, b[5])
                            except Exception:
                                pass
            except Exception as e:
                print(f"Error accessing actors in reset_camera_to_actors: {e}")

            if has_elements and xmin < xmax and ymin < ymax and zmin < zmax:
                # Aplica uma margem de segurança de 10%
                dx = (xmax - xmin) * 0.1
                dy = (ymax - ymin) * 0.1
                dz = (zmax - zmin) * 0.1
                # Evita margem nula se for unidimensional
                dx = max(dx, 0.001)
                dy = max(dy, 0.001)
                dz = max(dz, 0.001)
                
                bounds = [
                    xmin - dx, xmax + dx,
                    ymin - dy, ymax + dy,
                    zmin - dz, zmax + dz
                ]
                self.plotter.reset_camera(bounds=bounds)
            else:
                self.plotter.reset_camera()
        except Exception as e:
            print(f"Error resetting camera focus: {e}")
            self.plotter.reset_camera()
        self.plotter.render()
