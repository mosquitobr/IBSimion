#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IBSimion 2.0 Global Regression Test Pipeline
Validates and compares the output of ibsimu_wrapper against native benchmarks sequentially.
"""

import os
import sys
import json
import subprocess
import time
import math

# Paths
BENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(BENT_DIR, "..", "backend"))

def to_wsl_path(win_path):
    if os.name != 'nt':
        return win_path.replace("\\", "/")
    p = win_path.replace("\\", "/")
    if len(p) >= 2 and p[1] == ":":
        drive = p[0].lower()
        return f"/mnt/{drive}{p[2:]}"
    return p

WSL_BENT_DIR = to_wsl_path(BENT_DIR)
WSL_BACKEND_DIR = to_wsl_path(BACKEND_DIR)

def run_cmd_wsl(cmd_str):
    if os.name == 'nt':
        print(f"Running in WSL: {cmd_str}")
        res = subprocess.run(
            ["wsl", "bash", "-c", cmd_str],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    else:
        print(f"Running natively: {cmd_str}")
        res = subprocess.run(
            ["bash", "-c", cmd_str],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    return res

def calculate_twiss_from_tof(tof_path):
    if not os.path.exists(tof_path):
        return None
    x_coords = []
    vx_coords = []
    vz_coords = []
    times = []
    
    with open(tof_path, "r") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split()
            if len(parts) >= 7:
                try:
                    # columns: t, x, vx, y, vy, z, vz
                    times.append(float(parts[0]))
                    x_coords.append(float(parts[1]))
                    vx_coords.append(float(parts[2]))
                    vz_coords.append(float(parts[6]))
                except ValueError:
                    pass
    
    num_particles = len(x_coords)
    if num_particles == 0:
        return None
        
    xp = [vx / vz if vz != 0 else 0.0 for vx, vz in zip(vx_coords, vz_coords)]
    
    mean_x = sum(x_coords) / num_particles
    mean_xp = sum(xp) / num_particles
    
    dx = [x - mean_x for x in x_coords]
    dxp = [p - mean_xp for p in xp]
    
    mean_dx2 = sum(d*d for d in dx) / num_particles
    mean_dxp2 = sum(dp*dp for dp in dxp) / num_particles
    mean_dx_dxp = sum(d*dp for d, dp in zip(dx, dxp)) / num_particles
    
    epsilon = math.sqrt(max(0.0, mean_dx2 * mean_dxp2 - mean_dx_dxp**2))
    beta = mean_dx2 / epsilon if epsilon > 0 else 0.0
    alpha = -mean_dx_dxp / epsilon if epsilon > 0 else 0.0
    mean_tof = sum(times) / num_particles
    
    return {
        "alpha": alpha,
        "beta": beta,
        "emittance": epsilon,
        "transmission": num_particles,
        "tof": mean_tof,
        "std_x": math.sqrt(mean_dx2),
        "std_xp": math.sqrt(mean_dxp2),
        "covariance": mean_dx_dxp
    }

def run_test1():
    print("\n==========================================")
    print("RUNNING TEST 1: TOFL20 (Vacuum with DXF)")
    print("==========================================")
    
    test_dir = os.path.join(BENT_DIR, "teste1")
    wsl_test_dir = f"{WSL_BENT_DIR}/teste1"
    
    # Clean previous output
    native_tof = os.path.join(test_dir, "tof.txt")
    wrapper_tof = os.path.join(BACKEND_DIR, "tof.txt")
    for f in [native_tof, wrapper_tof]:
        if os.path.exists(f):
            os.remove(f)
            
    # Compile native benchmark
    print("Compiling native tofl203d...")
    build_res = run_cmd_wsl(f"cd {wsl_test_dir} && make clean && make")
    if build_res.returncode != 0:
        print("Error compiling tofl203d:")
        print(build_res.stderr)
        return False, "Compilation error"
        
    # Run native benchmark (timeout because it launches GUI plotter)
    print("Running native tofl203d (timed run)...")
    run_cmd_wsl(f"cd {wsl_test_dir} && timeout 15 ./tofl203d")
    
    if not os.path.exists(native_tof):
        print("Error: Native run did not generate tof.txt")
        return False, "No native output"
        
    native_metrics = calculate_twiss_from_tof(native_tof)
    if not native_metrics:
        return False, "Failed to parse native metrics"
        
    # Write scenario JSON for wrapper
    scenario_json = {
        "mode": "CW",
        "h": 0.002,
        "xmin": -0.035,
        "xmax": 0.035,
        "ymin": -0.035,
        "ymax": 0.035,
        "zmin": 0.0,
        "zmax": 0.360,
        "threads": 4,
        "geometries": [
            {
                "name": "deteletrons",
                "file_path": "../bent/teste1/tofl203d.dxf",
                "layer": "deteletrons",
                "voltage": 3700.0,
                "type": "Dirichlet",
                "translation": [0.0, 0.0, 0.0],
                "scale": 0.001,
                "mapping": "rotz"
            },
            {
                "name": "gradepositiva",
                "file_path": "../bent/teste1/tofl203d.dxf",
                "layer": "gradepositiva",
                "voltage": 500.0,
                "type": "Dirichlet",
                "translation": [0.0, 0.0, 0.0],
                "scale": 0.001,
                "mapping": "rotz"
            },
            {
                "name": "gradenegativa",
                "file_path": "../bent/teste1/tofl203d.dxf",
                "layer": "gradenegativa",
                "voltage": -500.0,
                "type": "Dirichlet",
                "translation": [0.0, 0.0, 0.0],
                "scale": 0.001,
                "mapping": "rotz"
            },
            {
                "name": "lente",
                "file_path": "../bent/teste1/tofl203d.dxf",
                "layer": "lente",
                "voltage": -950.0,
                "type": "Dirichlet",
                "translation": [0.0, 0.0, 0.0],
                "scale": 0.001,
                "mapping": "rotz"
            },
            {
                "name": "drift",
                "file_path": "../bent/teste1/tofl203d.dxf",
                "layer": "drift",
                "voltage": -2924.0,
                "type": "Dirichlet",
                "translation": [0.0, 0.0, 0.0],
                "scale": 0.001,
                "mapping": "rotz"
            },
            {
                "name": "detions",
                "file_path": "../bent/teste1/tofl203d.dxf",
                "layer": "detions",
                "voltage": -4800.0,
                "type": "Dirichlet",
                "translation": [0.0, 0.0, 0.0],
                "scale": 0.001,
                "mapping": "rotz"
            }
        ],
        "beams": [
            {
                "nome": "Beam1",
                "particulas": 500,
                "corrente": 2.0348e-08,
                "massa": 136.2,
                "carga": 1.0,
                "energy": 0.0454,
                "emittance": 2.028e-05,
                "distribution": "Uniform",
                "radius": 0.0005,
                "z_start": 0.081,
                "orig_z": 0.081,
                "orig_x": 0.0,
                "orig_y": 0.0,
                "dir_x": 0.0,
                "dir_y": -1.0,
                "dir_z": 0.0,
                "Tp": 0.0233
            },
            {
                "nome": "Beam2",
                "particulas": 500,
                "corrente": 2.0252e-08,
                "massa": 137.2,
                "carga": 1.0,
                "energy": 0.0458,
                "emittance": 2.028e-05,
                "distribution": "Uniform",
                "radius": 0.0005,
                "z_start": 0.081,
                "orig_z": 0.081,
                "orig_x": 0.0,
                "orig_y": 0.0,
                "dir_x": 0.0,
                "dir_y": -1.0,
                "dir_z": 0.0,
                "Tp": 0.0235
            },
            {
                "nome": "Beam3",
                "particulas": 500,
                "corrente": 2.0108e-08,
                "massa": 138.2,
                "carga": 1.0,
                "energy": 0.0461,
                "emittance": 2.028e-05,
                "distribution": "Uniform",
                "radius": 0.0005,
                "z_start": 0.081,
                "orig_z": 0.081,
                "orig_x": 0.0,
                "orig_y": 0.0,
                "dir_x": 0.0,
                "dir_y": -1.0,
                "dir_z": 0.0,
                "Tp": 0.0237
            },
            {
                "nome": "Electrons",
                "particulas": 1500,
                "corrente": 5.0998e-07,
                "massa": 0.000544,
                "carga": -1.0,
                "energy": 12.7,
                "emittance": 2.42735e-09,
                "distribution": "Uniform",
                "radius": 0.0005,
                "z_start": 0.081,
                "orig_z": 0.081,
                "orig_x": 0.0,
                "orig_y": 0.0,
                "dir_x": 0.0,
                "dir_y": -1.0,
                "dir_z": 0.0,
                "Tp": 9.342e-8
            }
        ],
        "bfield_enabled": False,
        "magnetic_field_file": "",
        "diag_plane_z": 0.3549,
        "dump_potential": False,
        "dump_charge_density": False,
        "dump_trajectory_density": False,
        "dump_tof": True,
        "generate_jpg": 0,
        "interactive_plot": 0
    }
    
    json_path = os.path.join(test_dir, "config_scenario.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(scenario_json, f, indent=4)
        
    # Run wrapper simulation
    print("Running ibsimu_wrapper for test 1...")
    run_res = run_cmd_wsl(f"cd {WSL_BACKEND_DIR} && ./ibsimu_wrapper ../bent/teste1/config_scenario.json")
    if run_res.returncode != 0:
        print("Error running wrapper:")
        print(run_res.stderr)
        return False, "Wrapper run error"
        
    wrapper_metrics = calculate_twiss_from_tof(wrapper_tof)
    if not wrapper_metrics:
        return False, "Failed to parse wrapper metrics"
        
    # Compare
    em_bench = native_metrics["emittance"]
    em_sim = wrapper_metrics["emittance"]
    tof_bench = native_metrics["tof"]
    tof_sim = wrapper_metrics["tof"]
    
    div_em = abs(em_sim - em_bench) / em_bench if em_bench > 0 else 0.0
    div_tof = abs(tof_sim - tof_bench) / tof_bench if tof_bench > 0 else 0.0
    
    # Divergence is max of emittance and TOF errors
    divergence = max(div_em, div_tof)
    
    print(f"Test 1 Detailed Diagnostics:")
    print(f"  Benchmark:  emittance={em_bench:.6e} | std_x={native_metrics['std_x']:.6e} | std_xp={native_metrics['std_xp']:.6e} | cov={native_metrics['covariance']:.6e}")
    print(f"  Simulation: emittance={em_sim:.6e} | std_x={wrapper_metrics['std_x']:.6e} | std_xp={wrapper_metrics['std_xp']:.6e} | cov={wrapper_metrics['covariance']:.6e}")
    print(f"  TOF       (Bench): {tof_bench:.6e} | (Sim): {tof_sim:.6e} | Diff: {div_tof:.2%}")
    
    # Custom threshold for Test 1: emittance < 75%, TOF < 5%
    success = (div_em < 0.75 and div_tof < 0.05)
    return success, divergence

def run_test2():
    print("\n==========================================")
    print("RUNNING TEST 2: EINZEL3D (Focusing Einzel)")
    print("==========================================")
    
    test_dir = os.path.join(BENT_DIR, "teste2")
    wsl_test_dir = f"{WSL_BENT_DIR}/teste2"
    
    # Clean previous output
    native_emit = os.path.join(test_dir, "emit.txt")
    wrapper_tof = os.path.join(BACKEND_DIR, "tof.txt")
    for f in [native_emit, wrapper_tof]:
        if os.path.exists(f):
            os.remove(f)
            
    # Compile native benchmark
    print("Compiling native einzel3d...")
    build_res = run_cmd_wsl(f"cd {wsl_test_dir} && make clean && make")
    if build_res.returncode != 0:
        print("Error compiling einzel3d:")
        print(build_res.stderr)
        return False, "Compilation error"
        
    # Run native benchmark
    print("Running native einzel3d (timed run)...")
    run_cmd_wsl(f"cd {wsl_test_dir} && timeout 15 ./einzel3d")
    
    if not os.path.exists(native_emit):
        print("Error: Native run did not generate emit.txt")
        return False, "No native output"
        
    # Parse last line of emit.txt for alpha, beta, emittance
    bench_twiss = None
    with open(native_emit, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 3:
                try:
                    bench_twiss = [float(x) for x in parts]
                except ValueError:
                    pass
    if not bench_twiss:
        return False, "Failed to parse native emittance output"
        
    alpha_bench, beta_bench, epsilon_bench = bench_twiss
    
    # Write scenario JSON for wrapper
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
                "file_path": "../bent/teste2/einzel3d.dxf",
                "layer": "gnd",
                "voltage": 0.0,
                "type": "Dirichlet",
                "translation": [0.0, 0.0, 0.0],
                "scale": 0.001,
                "mapping": "rotz"
            },
            {
                "name": "einzel",
                "file_path": "../bent/teste2/einzel3d.dxf",
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
                "corrente": 1.0,
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
        "bfield_enabled": False,
        "magnetic_field_file": "",
        "diag_plane_z": 0.169,
        "dump_potential": False,
        "dump_charge_density": False,
        "dump_trajectory_density": False,
        "dump_tof": True,
        "generate_jpg": 0,
        "interactive_plot": 0
    }
    
    json_path = os.path.join(test_dir, "config_scenario.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(scenario_json, f, indent=4)
        
    # Run wrapper simulation
    print("Running ibsimu_wrapper for test 2...")
    run_res = run_cmd_wsl(f"cd {WSL_BACKEND_DIR} && ./ibsimu_wrapper ../bent/teste2/config_scenario.json")
    if run_res.returncode != 0:
        print("Error running wrapper:")
        print(run_res.stderr)
        return False, "Wrapper run error"
        
    wrapper_metrics = calculate_twiss_from_tof(wrapper_tof)
    if not wrapper_metrics:
        return False, "Failed to parse wrapper metrics"
        
    alpha_sim = wrapper_metrics["alpha"]
    beta_sim = wrapper_metrics["beta"]
    epsilon_sim = wrapper_metrics["emittance"]
    
    # Calculate errors
    alpha_err = abs(alpha_sim - alpha_bench)
    beta_err = abs(beta_sim - beta_bench)
    epsilon_err = abs(epsilon_sim - epsilon_bench) / epsilon_bench if epsilon_bench > 0 else 0.0
    
    print(f"Test 2 Results:")
    print(f"  Alpha:   Bench = {alpha_bench:.6f} | Sim = {alpha_sim:.6f} | Err: {alpha_err:.6e}")
    print(f"  Beta:    Bench = {beta_bench:.6f} | Sim = {beta_sim:.6f} | Err: {beta_err:.6e}")
    print(f"  Epsilon: Bench = {epsilon_bench:.6e} | Sim = {epsilon_sim:.6e} | Err: {epsilon_err:.2%}")
    
    success = (epsilon_err < 0.05 and alpha_err < 0.1 and beta_err < 0.1)
    return success, epsilon_err

def run_test3():
    print("\n==========================================")
    print("RUNNING TEST 3: SOLENOID (Magnetic Field in Vacuum)")
    print("==========================================")
    
    test_dir = os.path.join(BENT_DIR, "teste3")
    wsl_test_dir = f"{WSL_BENT_DIR}/teste3"
    
    # Clean previous output
    native_emit = os.path.join(test_dir, "emit.txt")
    wrapper_tof = os.path.join(BACKEND_DIR, "tof.txt")
    for f in [native_emit, wrapper_tof]:
        if os.path.exists(f):
            os.remove(f)
            
    # Compile native benchmark
    print("Compiling native solenoid...")
    build_res = run_cmd_wsl(f"cd {wsl_test_dir} && make clean && make")
    if build_res.returncode != 0:
        print("Error compiling solenoid:")
        print(build_res.stderr)
        return False, "Compilation error"
        
    # Run native benchmark
    print("Running native solenoid (timed run)...")
    run_cmd_wsl(f"cd {wsl_test_dir} && timeout 15 ./solenoid")
    
    if not os.path.exists(native_emit):
        print("Error: Native run did not generate emit.txt")
        return False, "No native output"
        
    # Parse last line of emit.txt for alpha, beta, emittance
    bench_twiss = None
    with open(native_emit, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 3:
                try:
                    bench_twiss = [float(x) for x in parts]
                except ValueError:
                    pass
    if not bench_twiss:
        return False, "Failed to parse native emittance output"
        
    alpha_bench, beta_bench, epsilon_bench = bench_twiss
    
    # Write scenario JSON for wrapper
    # In solenoid.cpp: r0 = 25e-3, Tt = 0.01, E0 = 80000.0 => emittance_ref = r0 * sqrt(Tt / E0)
    emittance_ref = 0.025 * math.sqrt(0.01 / 80000.0)
    
    scenario_json = {
        "mode": "CW",
        "h": 0.002,
        "xmin": -0.05,
        "xmax": 0.05,
        "ymin": -0.05,
        "ymax": 0.05,
        "zmin": -0.250,
        "zmax": 0.250,
        "iterations": 1,
        "threads": 4,
        "geometries": [],  # Pure Vacuum Neumann Boundaries
        "beams": [
            {
                "nome": "Beam1",
                "particulas": 1000,
                "corrente": 0.1,  # 100uA
                "massa": 40.0,
                "carga": 8.0,
                "energy": 80000.0,
                "emittance": emittance_ref,
                "distribution": "Uniform",
                "radius": 0.025,
                "z_start": -0.250,
                "orig_z": -0.250,
                "orig_x": 0.0,
                "orig_y": 0.0,
                "dir_x": 0.0,
                "dir_z": 1.0
            }
        ],
        "bfield_enabled": True,
        "magnetic_field_file": "../bent/teste3/sol.txt",
        "magnetic_field_scale": 0.7,
        "diag_plane_z": 0.249,
        "dump_potential": False,
        "dump_charge_density": False,
        "dump_trajectory_density": False,
        "dump_tof": True,
        "generate_jpg": 0,
        "interactive_plot": 0
    }
    
    json_path = os.path.join(test_dir, "config_scenario.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(scenario_json, f, indent=4)
        
    # Run wrapper simulation
    print("Running ibsimu_wrapper for test 3...")
    run_res = run_cmd_wsl(f"cd {WSL_BACKEND_DIR} && ./ibsimu_wrapper ../bent/teste3/config_scenario.json")
    if run_res.returncode != 0:
        print("Error running wrapper:")
        print(run_res.stderr)
        return False, "Wrapper run error"
        
    wrapper_metrics = calculate_twiss_from_tof(wrapper_tof)
    if not wrapper_metrics:
        return False, "Failed to parse wrapper metrics"
        
    alpha_sim = wrapper_metrics["alpha"]
    beta_sim = wrapper_metrics["beta"]
    epsilon_sim = wrapper_metrics["emittance"]
    
    # Calculate errors
    alpha_err = abs(alpha_sim - alpha_bench)
    beta_err = abs(beta_sim - beta_bench)
    epsilon_err = abs(epsilon_sim - epsilon_bench) / epsilon_bench if epsilon_bench > 0 else 0.0
    
    print(f"Test 3 Results:")
    print(f"  Alpha:   Bench = {alpha_bench:.6f} | Sim = {alpha_sim:.6f} | Err: {alpha_err:.6e}")
    print(f"  Beta:    Bench = {beta_bench:.6f} | Sim = {beta_sim:.6f} | Err: {beta_err:.6e}")
    print(f"  Epsilon: Bench = {epsilon_bench:.6e} | Sim = {epsilon_sim:.6e} | Err: {epsilon_err:.2%}")
    
    success = (epsilon_err < 0.05 and alpha_err < 0.2 and beta_err < 0.2)
    return success, epsilon_err

def main():
    print("Starting IBSimion 2.0 Global Regression Test Robot...")
    
    t1_pass, t1_div = run_test1()
    t2_pass, t2_div = run_test2()
    t3_pass, t3_div = run_test3()
    
    print("\n==========================================")
    print("GLOBAL REGRESSION REPORT")
    print("==========================================")
    
    def report_line(test_num, name, success, div):
        status = "PASS" if success else "FAIL"
        div_str = f"{div:.2%}" if isinstance(div, float) else str(div)
        print(f"Teste {test_num} ({name}): Divergência {div_str} - {status}")
        
    report_line(1, "tofl203d", t1_pass, t1_div)
    report_line(2, "einzel3d", t2_pass, t2_div)
    report_line(3, "solenoid", t3_pass, t3_div)
    
    if t1_pass and t2_pass and t3_pass:
        print("\n[SUCCESS] All regression tests passed successfully!")
        sys.exit(0)
    else:
        print("\n[FAIL] Some regression tests failed or exceeded divergence thresholds.")
        sys.exit(1)

if __name__ == "__main__":
    main()
