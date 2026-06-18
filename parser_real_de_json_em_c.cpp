/* * IBSimion 2.0 - Parser Estruturado C++ usando nlohmann/json
 * Este arquivo lê o arquivo 'config_scenario_example.json' e mapeia as informações
 * diretamente para estruturas fortes de C++. Esse é o cérebro que conectará
 * as configurações visuais do Windows com o motor físico IBSimu.
 */

#include <iostream>
#include <fstream>
#include <string>
#include <vector>
// Biblioteca profissional de manipulação de JSON para C++
#include <nlohmann/json.hpp>

using json = nlohmann::json;

// Estruturas de dados fortemente tipadas para receber os dados do JSON
struct DimensõesMalha {
    double z_max;
    double r_max;
};

struct ParâmetrosResolvedor {
    int max_iterations;
    double dt;
};

struct GeometriaCAD {
    int id;
    std::string nome;
    std::string file_path;
    std::string type;
    double voltage;
    std::vector<double> translation;
};

struct FeixeParticulas {
    std::string nome;
    int particulas;
    double massa;
    double carga;
    double corrente;
};

int main() {
    std::cout << "==========================================================" << std::endl;
    std::cout << "      PARSER REAL DE CENARIOS - MOTOR IBSIMION 2.0" << std::endl;
    std::cout << "==========================================================\n" << std::endl;

    std::string caminho_json = "config_scenario_example.json";
    std::ifstream arquivo(caminho_json);

    if (!arquivo.is_open()) {
        std::cerr << "[ERRO] Falha ao abrir o arquivo: " << caminho_json << std::endl;
        std::cerr << "Certifique-se de que o arquivo config_scenario_example.json existe na pasta!" << std::endl;
        return 1;
    }

    // Leitura automática do JSON pela biblioteca
    json dados_json;
    try {
        arquivo >> dados_json;
    } catch (const json::parse_error& e) {
        std::cerr << "[ERRO] Erro crítico de sintaxe no arquivo JSON: " << e.what() << std::endl;
        return 1;
    }
    arquivo.close();

    std::cout << "[SUCESSO] Arquivo JSON parseado com integridade!" << std::endl;

    // 1. Extraindo Parâmetros Globais da Simulação
    std::string modo_simulacao = dados_json.value("simulation_mode", "CW");
    double h = dados_json.value("mesh_h", 0.001);

    std::cout << "\n--- Configurações Globais do Domínio ---" << std::endl;
    std::cout << "  * Modo de Operação: " << modo_simulacao << std::endl;
    std::cout << "  * Passo da Malha (h): " << h << " m" << std::endl;

    // Mapeando dimensões da malha
    if (dados_json.contains("mesh_dimensions")) {
        DimensõesMalha malha;
        malha.z_max = dados_json["mesh_dimensions"].value("z_max", 0.1);
        malha.r_max = dados_json["mesh_dimensions"].value("r_max", 0.01);
        std::cout << "  * Limites Físicos: Z max = " << malha.z_max << " m | R max = " << malha.r_max << " m" << std::endl;
    }

    // 2. Extraindo os Sólidos Eletrodos (STL / DXF)
    std::cout << "\n--- Mapeamento de Geometrias e Eletrodos Dirichlet ---" << std::endl;
    if (dados_json.contains("geometries")) {
        for (const auto& item : dados_json["geometries"]) {
            GeometriaCAD geo;
            geo.id = item.value("id", 0);
            geo.nome = item.value("name", "Eletrodo Sem Nome");
            geo.file_path = item.value("file_path", "");
            geo.voltage = item.value("voltage", 0.0);
            
            std::cout << "  [Eletrodo ID " << geo.id << "] " << geo.nome << std::endl;
            std::cout << "    Arquivo CAD: " << geo.file_path << std::endl;
            std::cout << "    Potencial Dirichlet Aplicado: " << geo.voltage << " V" << std::endl;
            
            if (item.contains("translation")) {
                geo.translation = item["translation"].get<std::vector<double>>();
                if (geo.translation.size() >= 3) {
                    std::cout << "    Vetor Translação XYZ: [" 
                              << geo.translation[0] << ", " 
                              << geo.translation[1] << ", " 
                              << geo.translation[2] << "] m" << std::endl;
                }
            }
            std::cout << std::endl;
        }
    }

    // 3. Extraindo os Feixes de Partículas (Injetores Multi-Espécie)
    std::cout << "--- Parametrização Dinâmica de Injeção de Feixes ---" << std::endl;
    if (dados_json.contains("beams")) {
        for (const auto& item : dados_json["beams"]) {
            FeixeParticulas feixe;
            feixe.nome = item.value("nome", "Feixe");
            feixe.particulas = item.value("particulas", 1000);
            feixe.massa = item.value("massa", 1.0);
            feixe.carga = item.value("carga", 1.0);
            feixe.corrente = item.value("corrente", 0.0);

            std::cout << "  * Feixe: " << feixe.nome << std::endl;
            std::cout << "    - Contagem de Macro-Partículas: " << feixe.particulas << std::endl;
            std::cout << "    - Massa Equivalente: " << feixe.massa << " u" << std::endl;
            std::cout << "    - Carga Relativa: " << feixe.carga << " e" << std::endl;
            std::cout << "    - Corrente Elétrica Total: " << feixe.corrente << " A" << std::endl;
            std::cout << std::endl;
        }
    }

    std::cout << "==========================================================" << std::endl;
    return 0;
}