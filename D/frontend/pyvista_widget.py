# -*- coding: utf-8 -*-
# pyvista_widget.py

import os
import numpy as np
import pyvista as pv
pv.global_theme.allow_empty_mesh = True
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import QVBoxLayout, QWidget

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
        self.plotter.set_background("#E5E7EB")
        self.plotter.show_axes()
        self.plotter.show_grid(color="#6B7280")
        
        # Tracks dictionary for fast lookup/removal
        self.trajectories = []
        self.electrode_mesh = None

    def clear_scene(self):
        """Clears all meshes from the plotter except grid/axes."""
        self.plotter.clear()
        self.plotter.show_axes()
        self.plotter.show_grid(color="#6B7280")
        self.trajectories = []
        self.electrode_mesh = None

    def load_geometry(self, obj_path):
        """Loads and renders the OBJ geometry file."""
        if not os.path.exists(obj_path):
            print(f"Geometry file not found: {obj_path}")
            return False
            
        try:
            self.electrode_mesh = pv.read(obj_path)
            self.plotter.add_mesh(
                self.electrode_mesh, 
                color="silver", 
                opacity=0.35, 
                show_edges=True, 
                edge_color="dimgray",
                name="electrodes"
            )
            self.plotter.reset_camera()
            return True
        except Exception as e:
            print(f"Error loading geometry mesh: {e}")
            return False

    def load_trajectories(self, traj_path, color_by='mass'):
        """Parses and renders the particle tracks from trajectories.txt."""
        if not os.path.exists(traj_path):
            print(f"Trajectory file not found: {traj_path}")
            return False
            
        try:
            # Parse trajectories.txt
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
                        if len(parts) == 4 and current_traj is not None:
                            t, x, y, z = map(float, parts)
                            # In IBSimu 3D coordinates, z is longitudinal, x/y are transversal.
                            # We keep them in order (x, y, z) for 3D plotting
                            current_traj["points"].append([x, y, z])
            
            # Plot trajectories
            self.plot_trajectories(color_by)
            return True
        except Exception as e:
            print(f"Error loading trajectories: {e}")
            return False

    def plot_trajectories(self, color_by='mass'):
        """Plots the loaded trajectories color-coded by the selected attribute (species, mass, charge, energy, current)."""
        # First, remove old trajectory meshes
        for name in list(self.plotter.renderer.actors.keys()):
            if name.startswith("track_"):
                self.plotter.remove_actor(name)
                
        if not self.trajectories:
            return

        # Discrete high-contrast color palette for species or attributes
        colors_palette = ["#3B82F6", "#F43F5E", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4"]

        # Find unique values for mass, charge, current to map to discrete colors
        unique_masses = sorted(list(set(t["mass"] for t in self.trajectories)))
        unique_charges = sorted(list(set(t["charge"] for t in self.trajectories)))
        unique_currents = sorted(list(set(t["curr"] for t in self.trajectories)))

        for idx, traj in enumerate(self.trajectories):
            pts = np.array(traj["points"])
            if len(pts) < 2:
                continue
                
            poly = pv.MultipleLines(points=pts)
            
            # 5 discrete coloring options
            if color_by == 'species':
                # Color by trajectory ID (distinct species index)
                c_idx = idx % len(colors_palette)
                color = colors_palette[c_idx]
            elif color_by == 'mass':
                # Color based on unique mass values
                m_idx = unique_masses.index(traj["mass"]) if traj["mass"] in unique_masses else 0
                c_idx = m_idx % len(colors_palette)
                color = colors_palette[c_idx]
            elif color_by == 'charge':
                # Color based on positive vs negative charge
                if traj["charge"] > 0:
                    color = "#10B981" # Green for positive
                elif traj["charge"] < 0:
                    color = "#F43F5E" # Pink/Red for negative
                else:
                    color = "#9CA3AF" # Muted gray for neutral
            elif color_by == 'energy':
                # Show an energy gradient along the trajectory (using Z coordinate position as proxy for energy gain)
                # We can add scalars to the polydata and render with a colormap
                z_coords = pts[:, 2]
                poly.point_data["Z"] = z_coords
                scalar_bar_args = {
                    'title_font_size': 12,
                    'label_font_size': 10,
                    'color': 'black',  # Garante que as fontes numéricas e títulos fiquem visíveis no tema claro
                    'fmt': '%.2e'      # Formata a notação científica de forma limpa (ex: 1.00e-02)
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
                # Color based on unique current values
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
        
    def load_pic_snapshot(self, snapshot_data_or_path):
        """Loads a single PIC snapshot (list of coordinates at time t) and renders particles as spheres."""
        # Remove old particles
        for name in list(self.plotter.renderer.actors.keys()):
            if name.startswith("pic_particles"):
                self.plotter.remove_actor(name)

        try:
            if isinstance(snapshot_data_or_path, str):
                if not os.path.exists(snapshot_data_or_path):
                    return False
                data = np.loadtxt(snapshot_data_or_path)
            else:
                data = snapshot_data_or_path

            if data is None:
                return False
            if data.ndim == 1:
                data = np.expand_dims(data, axis=0)
            if data.size == 0 or len(data) == 0:
                return False

            # Extract coordinates (x, y, z are cols 1, 3, 5)
            # Row format: t x vx y vy z vz
            pts = np.column_stack((data[:, 1], data[:, 3], data[:, 5]))
            
            # Create point cloud
            point_cloud = pv.PolyData(pts)
            
            # Plot as glyph (spheres)
            self.plotter.add_mesh(
                point_cloud, 
                color="#F43F5E", 
                point_size=12.0, 
                render_points_as_spheres=True, 
                name="pic_particles"
            )
            self.plotter.render()
            return True
        except Exception as e:
            print(f"Error loading PIC snapshot: {e}")
            return False

    def apply_clipping_plane(self, coord, normal=(0, 0, -1), origin=None):
        """Applies a clipping plane to the loaded electrode mesh at the specified coordinate and normal."""
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
            
            self.plotter.add_mesh(
                clipped,
                color="silver",
                opacity=0.35,
                show_edges=True,
                edge_color="dimgray",
                name="electrodes"
            )
            self.plotter.render()
        except Exception as e:
            print(f"Error applying clipping plane: {e}")


