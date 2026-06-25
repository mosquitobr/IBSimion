#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IBSimion 2.0 Regression Test Robot
Compares the output of IBSimion 2.0 (via ibsimu_wrapper) against the native einzel3d benchmark.
"""

import os
import sys
import json
import subprocess
import time
import math

# Paths
TEST2_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(TEST2_DIR, "..", "..", "backend"))
BASE_DIR = os.path.abspath(os.path.join(TEST2_DIR, "..", "..", ".."))

# WSL path conversion
def to_wsl_path(win_path):
    p = win_path.replace("\\", "/")
    if len(p) >= 2 and p[1] == ":":
        drive = p[0].lower()
        return f"/mnt/{drive}{p[2:]}"
    return p

WSL_TEST2_DIR = to_wsl_path(TEST2_DIR)
WSL_BACKEND_DIR = to_wsl_path(BACKEND_DIR)

def run_cmd_wsl(cmd_str):
    print(f"Running in WSL: {cmd_str}")
    res = subprocess.run(
        ["wsl", "bash", "-c", cmd_str],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return res

def clean_old_files():
    print("Cleaning old output files...")
    for f in [os.path.join(TEST2_DIR, "emit.txt"), os.path.join(BACKEND_DIR, "tof.txt")]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception as e:
                print(f"Warning: could not remove {f}: {e}")

def run_native_benchmark():
    print("--- 1. BUILDING & RUNNING NATIVE BENCHMARK ---")
    # Clean and build
    build_res = run_cmd_wsl(f"cd {WSL_TEST2_DIR} && make clean && make")
    if build_res.returncode != 0:
        print("Error compiling native benchmark einzel3d:")
        print(build_res.stderr)
        sys.exit(1)
        
    print("Compilado com sucesso. Executando einzel3d...")
    # Run with timeout to prevent hanging on GTKPlotter GUI
    run_res = run_cmd_wsl(f"cd {WSL_TEST2_DIR} && timeout 10 ./einzel3d")
    
    emit_path = os.path.join(TEST2_DIR, "emit.txt")
    if not os.path.exists(emit_path):
        print("Error: emit.txt not found in teste2 directory. Benchmark run failed.")
        print(run_res.stderr)
        sys.exit(1)
        
    # Read Twiss parameters from last line of emit.txt
    bench_data = []
    with open(emit_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 3:
                try:
                    bench_data.append([float(x) for x in parts])
                except ValueError:
                    pass
                    
    if not bench_data:
        print("Error: emit.txt is empty or invalid.")
        sys.exit(1)
        
    # Last line is the final converged cycle
    last_cycle = bench_data[-1]
    alpha_bench, beta_bench, epsilon_bench = last_cycle
    print(f"Benchmark Twiss parameters:")
    print(f"  Alpha:   {alpha_bench:.6f}")
    print(f"  Beta:    {beta_bench:.6f}")
    print(f"  Epsilon: {epsilon_bench:.6e} m-rad")
    return alpha_bench, beta_bench, epsilon_bench

def run_ibsimion_simulation():
    print("--- 2. RUNNING IBSIMION 2.0 PIPELINE ---")
    # emittance = r0 * sqrt(Tt / E0)
    # Tt = 0.01, E0 = 80000, r0 = 0.01 => emittance = 0.01 * sqrt(0.01 / 80000) = 3.5355339059327376e-06
    emittance_val = 0.01 * math.sqrt(0.01 / 80000.0)
    
    scenario_json = {
        "mode": "CW",
        "h": 0.001,
        "xmin": -0.035,
        "xmax": 0.035,
        "ymin": -0.035,
        "ymax": 0.035,
        "zmin": 0.0,
        "zmax": 0.170,
        "threads": 4,
        "geometries": [
            {
                "name": "gnd",
                "file_path": f"{WSL_TEST2_DIR}/einzel3d.dxf",
                "layer": "gnd",
                "voltage": 0.0,
                "type": "Dirichlet",
                "translation": [0.0, 0.0, 0.0],
                "scale": 0.001,
                "mapping": "rotz"
            },
            {
                "name": "einzel",
                "file_path": f"{WSL_TEST2_DIR}/einzel3d.dxf",
                "layer": "einzel",
                "voltage": -15000.0,
                "type": "Dirichlet",
                "translation": [0.0, 0.0, 0.0],
                "scale": 0.001,
                "mapping": "rotz"
            }
        ],
        "beams": [
            {
                "nome": "Beam1",
                "particulas": 1000,
                "corrente": 1.0, # 1mA
                "massa": 40.0,
                "carga": 8.0,
                "energy": 80000.0,
                "emittance": emittance_val,
                "distribution": "Uniform",
                "radius": 0.01,
                "z_start": 0.0,
                "orig_z": 0.0,
                "orig_x": 0.0,
                "orig_y": 0.0,
                "dir_x": 0.0,
                "dir_z": 1.0
            }
        ],
        "magnetic_field_file": "",
        "diag_plane_z": 0.169,
        "dump_potential": False,
        "dump_charge_density": False,
        "dump_trajectory_density": False,
        "dump_tof": True,
        "generate_jpg": 0,
        "interactive_plot": 0
    }
    
    # Write json to backend
    json_path = os.path.join(BACKEND_DIR, "config_scenario.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(scenario_json, f, indent=4)
    print(f"Generated config_scenario.json at {json_path}")
    
    # Execute ibsimu_wrapper in WSL
    run_res = run_cmd_wsl(f"cd {WSL_BACKEND_DIR} && ./ibsimu_wrapper config_scenario.json")
    if run_res.returncode != 0:
        print("Error running ibsimu_wrapper in WSL:")
        print(run_res.stderr)
        sys.exit(1)
        
    tof_path = os.path.join(BACKEND_DIR, "tof.txt")
    if not os.path.exists(tof_path):
        print("Error: tof.txt not generated by simulation wrapper.")
        sys.exit(1)
        
    # Read tof.txt data
    x_coords = []
    vx_coords = []
    vz_coords = []
    with open(tof_path, "r") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split()
            if len(parts) >= 7:
                try:
                    # tof.txt columns: t, x, vx, y, vy, z, vz, ...
                    x_coords.append(float(parts[1]))
                    vx_coords.append(float(parts[2]))
                    vz_coords.append(float(parts[6]))
                except ValueError:
                    pass
                    
    num_particles = len(x_coords)
    print(f"Successfully loaded {num_particles} particles from tof.txt.")
    if num_particles == 0:
        print("ERROR: Zero particles reached the detector plane. Possible beam alignment or geometry collision error!")
        sys.exit(1)
        
    # Mathematical Twiss and emittance calculation
    xp = [vx / vz for vx, vz in zip(vx_coords, vz_coords)]
    
    mean_x = sum(x_coords) / num_particles
    mean_xp = sum(xp) / num_particles
    
    dx = [x - mean_x for x in x_coords]
    dxp = [p - mean_xp for p in xp]
    
    mean_dx2 = sum(d*d for d in dx) / num_particles
    mean_dxp2 = sum(dp*dp for dp in dxp) / num_particles
    mean_dx_dxp = sum(d*dp for d, dp in zip(dx, dxp)) / num_particles
    
    epsilon_sim = math.sqrt(max(0.0, mean_dx2 * mean_dxp2 - mean_dx_dxp**2))
    if epsilon_sim < 1e-20:
        print("Error: Simulated emittance is zero or negative.")
        sys.exit(1)
        
    beta_sim = mean_dx2 / epsilon_sim
    alpha_sim = -mean_dx_dxp / epsilon_sim
    
    print(f"Simulation Twiss parameters:")
    print(f"  Alpha:   {alpha_sim:.6f}")
    print(f"  Beta:    {beta_sim:.6f}")
    print(f"  Epsilon: {epsilon_sim:.6e} m-rad")
    return alpha_sim, beta_sim, epsilon_sim

def compare_and_validate(bench, sim):
    alpha_bench, beta_bench, epsilon_bench = bench
    alpha_sim, beta_sim, epsilon_sim = sim
    
    alpha_err = abs(alpha_sim - alpha_bench)
    beta_err = abs(beta_sim - beta_bench)
    epsilon_err = abs(epsilon_sim - epsilon_bench) / epsilon_bench
    
    print("\n--- 3. COMPARISON & MATHEMATICAL VERIFICATION ---")
    print(f"{'Métrica':<15} | {'Benchmark':<15} | {'IBSimion 2.0':<15} | {'Erro Absoluto':<15}")
    print("-" * 68)
    print(f"{'Alpha':<15} | {alpha_bench:<15.6f} | {alpha_sim:<15.6f} | {alpha_err:<15.6e}")
    print(f"{'Beta':<15} | {beta_bench:<15.6f} | {beta_sim:<15.6f} | {beta_err:<15.6e}")
    print(f"{'Epsilon (m-rad)':<15} | {epsilon_bench:<15.6e} | {epsilon_sim:<15.6e} | {abs(epsilon_sim - epsilon_bench):<15.6e}")
    print(f"{'Erro Relat. Ep.':<15} | {'-':<15} | {'-':<15} | {epsilon_err:<15.2%}")
    
    # Strict thresholds
    success = True
    if alpha_err > 1e-2:
        print("\n[FAIL] Alpha divergence too high. Inverted geometry IDs or incorrect potential bounds likely.")
        success = False
    if beta_err > 1e-2:
        print("\n[FAIL] Beta divergence too high. Incorrect focus or beam shape.")
        success = False
    if epsilon_err > 0.05: # 5% relative error
        print("\n[FAIL] Epsilon emittance divergence too high. Particle distribution setup mismatch.")
        success = False
        
    if success:
        print("\n[SUCCESS] Regression test passed with flying colors! Mathematical error is near zero.")
        sys.exit(0)
    else:
        print("\n[FAIL] Regression test failed. Mismatch detected.")
        sys.exit(1)

if __name__ == "__main__":
    clean_old_files()
    bench_vals = run_native_benchmark()
    sim_vals = run_ibsimion_simulation()
    compare_and_validate(bench_vals, sim_vals)
