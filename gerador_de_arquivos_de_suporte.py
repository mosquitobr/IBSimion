# -*- coding: utf-8 -*-
"""
IBSimion 2.0 - Gerador Automatizado de Assets (C++ & JSON)
Grava os arquivos de suporte no disco com codificação correta.
"""

import os

# 1. Conteúdo do JSON de Configuração
json_content = """{
  "simulation_mode": "PIC",
  "mesh_h": 0.001,
  "mesh_dimensions": {
    "z_max": 0.36,
    "r_max": 0.035
  },
  "solver_params": {
    "max_iterations": 150,
    "dt": 5.0e-9
  },
  "geometries": [
    {
      "id": 1,
      "name": "Source Body",
      "file_path": "source_body.stl",
      "type": "Dirichlet",
      "voltage": 5000.0,
      "translation": [0.0, 0.0, 0.02]
    },
    {
      "id": 2,
      "name": "Grade Positiva",
      "file_path": "tofl203d.dxf",
      "layer": "GRID_POS",
      "type": "Dirichlet",
      "voltage": 500.0,
      "translation": [0.0, 0.0, 0.11]
    },
    {
      "id": 3,
      "name": "Tubo de Drift",
      "file_path": "drift_tube.stl",
      "type": "Dirichlet",
      "voltage": -2924.0,
      "translation": [0.0, 0.0, 0.22]
    }
  ],
  "beams": [
    {"nome": "Feixe de Ions Pesados 1", "particulas": 5000, "massa": 136.2, "carga": 1.0, "corrente": 0.001},
    {"nome": "Feixe de Eletrons Rapidos", "particulas": 3000, "massa": 0.00054, "carga": -1.0, "corrente": 0.005}
  ]
}"""

# 2. Conteúdo do Esqueleto C++
cpp_content = """/*
 * IBSimion 2.0 - Motor Fisico Dinamico e Parser de Cenarios (C++ / IBSimu)
 * Esqueleto de implementacao para leitura de configuracao JSON e
 * instanciacao de componentes fisicos do resolvedor IBSimu.
 */

#include <iostream>
#include <fstream>
#include <string>
#include <vector>

void carregar_cenario_json(const std::string &caminho_arquivo) {
    std::cout << "[BACKEND] Lendo definicoes de cenario: " << caminho_arquivo << std::endl;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        std::cerr << "[ERRO] Arquivo de cenario JSON nao fornecido!" << std::endl;
        std::cerr << "Uso: " << argv[0] << " <caminho_para_config.json>" << std::endl;
        return 1;
    }

    std::string config_path = argv[1];
    carregar_cenario_json(config_path);

    double h = 0.001; 
    double z_max = 0.36;
    double r_max = 0.035;
    
    std::cout << "-> Inicializando limites do Resolvedor Poisson..." << std::endl;

    std::cout << "-> Mapeando solidos CAD para condicoes de contorno Dirichlet..." << std::endl;

    std::cout << "-> Calculando Potenciais e Campo Eletrostatico..." << std::endl;
    int iteracoes = 0;
    double residuo = 1.0;
    while(iteracoes < 10 && residuo > 1e-5) {
        residuo = 0.5 / (iteracoes + 1);
        std::cout << "   Iteracao " << iteracoes + 1 << " - Residuo: " << residuo << std::endl;
        iteracoes++;
    }

    std::cout << "-> Configurando Banco de Dados de Particulas (ParticleDatabase)..." << std::endl;
    double dt_global = 5e-9;

    std::cout << "-> Calculando trajetorias transientes com tratamento de sub-stepping..." << std::endl;
    
    double massa_eletron = 0.00054; 
    double dt_eletron = dt_global / 1000.0; 

    std::cout << "   [SUCESSO] Trajetorias integradas." << std::endl;

    std::cout << "-> Gravando matrizes de campo scalar V(x,y,z) e vetores de trajetorias..." << std::endl;
    
    std::ofstream out_trajetorias("trajectories.txt");
    out_trajetorias << "# z, y, x, massa, carga, t" << std::endl;
    out_trajetorias.close();

    std::cout << "[BACKEND] Processamento finalizado com sucesso." << std::endl;
    return 0;
}"""

# Escrita dos arquivos
with open("config_scenario_example.json", "w", encoding="utf-8") as f:
    f.write(json_content)
print("[SUCESSO] Arquivo 'config_scenario_example.json' gerado!")

with open("ibsimion_backend_skeleton.cpp", "w", encoding="utf-8") as f:
    f.write(cpp_content)
print("[SUCESSO] Arquivo 'ibsimion_backend_skeleton.cpp' gerado!")
print("Todos os assets de engenharia foram salvos com a codificacao perfeita!")