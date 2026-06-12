# -*- coding: utf-8 -*-
# export_gif.py
# Helper utility to export temporal PIC snapshots as an animated GIF

import os
import numpy as np
import matplotlib
matplotlib.use('qtagg')  # non-interactive backend for safety
import matplotlib.pyplot as plt
from PIL import Image

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(script_dir, "backend")
    
    if not os.path.exists(backend_dir):
        print(f"Error: Backend directory {backend_dir} not found.")
        return

    # Scan and sort snapshots by timestamp
    files = [f for f in os.listdir(backend_dir) if f.startswith("pout_") and f.endswith(".txt")]
    if not files:
        print("No PIC snapshots (pout_*.txt) found. Run a PIC simulation in the UI first.")
        return

    def get_time(fn):
        try:
            return float(fn[5:-4])
        except ValueError:
            return 0.0

    files.sort(key=get_time)
    print(f"Found {len(files)} snapshots. Generating GIF frames...")

    frames = []
    
    # visual bounds matching physical spectrometer
    z_min, z_max = 0.08, 0.36
    trans_limit = 0.035

    fig = plt.figure(figsize=(9, 6), facecolor='#1e1e1e')
    ax = fig.add_subplot(111)
    
    for idx, f in enumerate(files):
        filepath = os.path.join(backend_dir, f)
        t = get_time(f)
        
        try:
            # Row format: t x vx y vy z vz
            data = np.loadtxt(filepath)
            if data.ndim == 1:
                data = np.expand_dims(data, axis=0)
            if data.size == 0:
                continue
        except Exception as e:
            print(f"Skipping file {f} due to error: {e}")
            continue

        ax.cla()
        ax.set_facecolor('#121212')
        
        # Plot particles: Z (col 5) vs X (col 1)
        ax.plot(data[:, 5], data[:, 1], 'r.', markersize=2, label='Íons / Ions')
        
        ax.set_xlim([z_min, z_max])
        ax.set_ylim([-trans_limit, trans_limit])
        ax.set_xlabel('Eixo Longitudinal Z (m)', color='#e0e0e0')
        ax.set_ylabel('Eixo Transversal X (m)', color='#e0e0e0')
        ax.tick_params(colors='#e0e0e0', which='both')
        for spine in ax.spines.values():
            spine.set_color('#3d3d3d')
            
        time_us = t * 1e6
        ax.set_title(f'IBSimion PIC TOF | t = {time_us:.3f} µs', color='#7d56f4', fontsize=14, fontweight='bold')
        ax.grid(True, linestyle='--', color='#2d2d2d')
        
        # Render frame to canvas and capture buffer
        fig.canvas.draw()
        rgba = fig.canvas.buffer_rgba()
        width, height = fig.canvas.get_width_height()
        
        img = Image.frombuffer("RGBA", (width, height), rgba, "raw", "RGBA", 0, 1)
        frames.append(img.convert("RGB"))
        
        if (idx + 1) % 10 == 0 or idx == len(files) - 1:
            print(f"Processed {idx + 1}/{len(files)} frames...")

    plt.close(fig)

    if frames:
        gif_path = os.path.join(script_dir, "pic_simulation.gif")
        print("Saving animated GIF...")
        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            optimize=True,
            duration=150,  # 150 ms per frame
            loop=0
        )
        print(f"\nSuccess! Animated GIF saved to: {gif_path}")
    else:
        print("Error: No frames generated.")

if __name__ == "__main__":
    main()
