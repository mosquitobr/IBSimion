# -*- coding: utf-8 -*-
# translation.py

TRANSLATIONS = {
    'pt': {
        'window_title': 'IBSimion - Simulador de Ótica de Partículas (Baseado em IBSimu)',
        'tab_config': 'Parâmetros Gerais',
        'tab_geom': 'Importação & CAD',
        'tab_run': 'Simular e Otimizar',
        'tab_visualizer': 'Visualizador 3D',
        'lang_label': 'Idioma / Language:',
        
        # Parâmetros Gerais
        'group_voltages': 'Tensões dos Eletrodos (V)',
        'lbl_vdet_el': 'Detector de Elétrons:',
        'lbl_vgrid_pos': 'Grade Positiva:',
        'lbl_vgrid_neg': 'Grade Negativa:',
        'lbl_vlens': 'Lente Eletrostática:',
        'lbl_vdrift': 'Tubo de Drift:',
        'lbl_vdet_ion': 'Detector de Íons:',
        
        'group_beams': 'Parâmetros do Feixe de Íons',
        'lbl_npart': 'Quantidade de Partículas:',
        'lbl_q': 'Carga do Íon (e):',
        'lbl_m1': 'Massa Íon 1 (u):',
        'lbl_m2': 'Massa Íon 2 (u):',
        'lbl_m3': 'Massa Íon 3 (u):',
        'lbl_r0': 'Raio do Feixe (m):',
        'lbl_tp': 'Temp. Paralela (eV):',
        'lbl_tt': 'Temp. Transversal (eV):',
        
        'group_mesh': 'Dimensões da Malha (Mesh)',
        'lbl_h': 'Tamanho do Passo h (m):',
        'lbl_zmax': 'Z Max (Comprimento m):',
        'lbl_xymax': 'Limites Transversais (m):',
        
        # CAD
        'group_import': 'Importação de Geometria',
        'lbl_import_mode': 'Modo de Importação:',
        'lbl_dxf_file': 'Arquivo DXF:',
        'btn_browse': 'Procurar...',
        'group_stl_files': 'Arquivos STL 3D (para modo STL)',
        
        'lbl_stl_det_el': 'Detector Elétrons STL:',
        'lbl_stl_grid_pos': 'Grade Positiva STL:',
        'lbl_stl_grid_neg': 'Grade Negativa STL:',
        'lbl_stl_lens': 'Lente STL:',
        'lbl_stl_drift': 'Drift STL:',
        'lbl_stl_det_ion': 'Detector Íons STL:',
        'group_offset': 'Translação/Offset Tridimensional (m)',
        'lbl_dx': 'Offset X:',
        'lbl_dy': 'Offset Y:',
        'lbl_dz': 'Offset Z:',
        
        # Simular e Otimizar
        'group_sim_mode': 'Modo de Simulação',
        'lbl_mode': 'Modo:',
        'lbl_dt': 'Passo de Tempo dt (s):',
        'lbl_tfinal': 'Tempo Final (s):',
        
        'group_opt': 'Configuração do Otimizador',
        'lbl_opt_w_trans': 'Peso Transmissão:',
        'lbl_opt_w_emit': 'Peso Emitância (RMS):',
        'lbl_opt_w_tof': 'Peso Resolução (TOF FWHM):',
        'lbl_opt_max_iter': 'Número Máx. Iterações:',
        'btn_start_sim': 'Executar Simulação Simples',
        'btn_start_opt': 'Iniciar Otimização',
        'btn_stop_opt': 'Interromper',
        
        'group_results': 'Resultados da Simulação',
        'lbl_res_transmission': 'Transmissão:',
        'lbl_res_emittance': 'Emitância RMS X (m·rad):',
        'lbl_res_fwhm': 'FWHM do Tempo de Voo (ns):',
        
        # Visualizador
        'btn_load_geom': 'Carregar Geometria e Trajetórias 3D',
        'lbl_view_type': 'Visualização:',
        'cb_color_by': 'Colorir Trajetórias Por:',
        'color_mass': 'Massa',
        'color_charge': 'Carga',
        'color_energy': 'Energia',
        
        # Status Messages
        'status_ready': 'Pronto.',
        'status_running_sim': 'Executando simulação IBSimu no WSL...',
        'status_sim_success': 'Simulação executada com sucesso em {} s.',
        'status_sim_failed': 'Falha na execução da simulação. Verifique os logs.',
        'status_opt_running': 'Otimizando... Iteração {}/{} | Função de Perda atual: {:.4f}',
        'status_opt_success': 'Otimização concluída com sucesso! Melhores tensões aplicadas.',
        
        # PIC Animation & CFL
        'group_pic_anim': 'Controle de Animação PIC',
        'btn_play': 'Animar (Play)',
        'btn_pause': 'Pausar (Pause)',
        'lbl_pic_time': 'Tempo: {:.2e} s',
        'lbl_cfl_safe': 'CFL: OK (dt < h/v_max)',
        'lbl_cfl_warn': '⚠️ Aviso CFL: dt >= h/v_max! Risco de divergência.',
    },
    'en': {
        'window_title': 'IBSimion - Particle Optics Simulator (Based on IBSimu)',
        'tab_config': 'General Settings',
        'tab_geom': 'CAD & Import',
        'tab_run': 'Run & Optimize',
        'tab_visualizer': '3D Visualizer',
        'lang_label': 'Language / Idioma:',
        
        # General Settings
        'group_voltages': 'Electrode Voltages (V)',
        'lbl_vdet_el': 'Electron Detector:',
        'lbl_vgrid_pos': 'Positive Grid:',
        'lbl_vgrid_neg': 'Negative Grid:',
        'lbl_vlens': 'Electrostatic Lens:',
        'lbl_vdrift': 'Drift Tube:',
        'lbl_vdet_ion': 'Ions Detector:',
        
        'group_beams': 'Ion Beam Parameters',
        'lbl_npart': 'Particle Count:',
        'lbl_q': 'Ion Charge (e):',
        'lbl_m1': 'Ion Mass 1 (u):',
        'lbl_m2': 'Ion Mass 2 (u):',
        'lbl_m3': 'Ion Mass 3 (u):',
        'lbl_r0': 'Beam Radius (m):',
        'lbl_tp': 'Parallel Temp. (eV):',
        'lbl_tt': 'Transverse Temp. (eV):',
        
        'group_mesh': 'Mesh Dimensions',
        'lbl_h': 'Grid Step Size h (m):',
        'lbl_zmax': 'Z Max (Length m):',
        'lbl_xymax': 'Transverse Limits (m):',
        
        # CAD
        'group_import': 'Geometry Import',
        'lbl_import_mode': 'Import Mode:',
        'lbl_dxf_file': 'DXF File:',
        'btn_browse': 'Browse...',
        'group_stl_files': '3D STL Files (for STL mode)',
        
        'lbl_stl_det_el': 'STL Electron Detector:',
        'lbl_stl_grid_pos': 'STL Positive Grid:',
        'lbl_stl_grid_neg': 'STL Negative Grid:',
        'lbl_stl_lens': 'STL Lens:',
        'lbl_stl_drift': 'STL Drift:',
        'lbl_stl_det_ion': 'STL Ions Detector:',
        'group_offset': 'Three-Dimensional Translation Offset (m)',
        'lbl_dx': 'Offset X:',
        'lbl_dy': 'Offset Y:',
        'lbl_dz': 'Offset Z:',
        
        # Run & Optimize
        'group_sim_mode': 'Simulation Mode',
        'lbl_mode': 'Mode:',
        'lbl_dt': 'Time Step dt (s):',
        'lbl_tfinal': 'Final Time (s):',
        
        'group_opt': 'Optimizer Settings',
        'lbl_opt_w_trans': 'Transmission Weight:',
        'lbl_opt_w_emit': 'Emittance (RMS) Weight:',
        'lbl_opt_w_tof': 'Resolution (TOF FWHM) Weight:',
        'lbl_opt_max_iter': 'Max Iterations:',
        'btn_start_sim': 'Run Simple Simulation',
        'btn_start_opt': 'Start Optimization',
        'btn_stop_opt': 'Stop',
        
        'group_results': 'Simulation Results',
        'lbl_res_transmission': 'Transmission:',
        'lbl_res_emittance': 'RMS Emittance X (m·rad):',
        'lbl_res_fwhm': 'TOF FWHM (ns):',
        
        # Visualizer
        'btn_load_geom': 'Load 3D Geometry and Trajectories',
        'lbl_view_type': 'Visualization:',
        'cb_color_by': 'Color Trajectories By:',
        'color_mass': 'Mass',
        'color_charge': 'Charge',
        'color_energy': 'Energy',
        
        # Status Messages
        'status_ready': 'Ready.',
        'status_running_sim': 'Running IBSimu simulation in WSL...',
        'status_sim_success': 'Simulation executed successfully in {} s.',
        'status_sim_failed': 'Simulation failed. Check logs.',
        'status_opt_running': 'Optimizing... Iteration {}/{} | Current Loss: {:.4f}',
        'status_opt_success': 'Optimization completed successfully! Best voltages applied.',
        
        # PIC Animation & CFL
        'group_pic_anim': 'PIC Animation Control',
        'btn_play': 'Play Animation',
        'btn_pause': 'Pause',
        'lbl_pic_time': 'Time: {:.2e} s',
        'lbl_cfl_safe': 'CFL: OK (dt < h/v_max)',
        'lbl_cfl_warn': '⚠️ CFL Warning: dt >= h/v_max! Divergence risk.',
    }
}
