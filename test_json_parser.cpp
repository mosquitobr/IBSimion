/* * IBSimion 2.0 - Teste de Parser C++ para o JSON de Configuração
 * Este programa é um passo didático para validar a leitura dos parâmetros 
 * físicos da simulação antes de instanciarmos as classes pesadas do IBSimu.
 */

#include <iostream>
#include <fstream>
#include <string>
#include <vector>

// Para facilitar a leitura e não sobrecarregar com instalações manuais complexas,
// incluiremos a biblioteca header-only baixando-a diretamente no WSL2 no próximo passo.
// Por enquanto, vamos preparar a estrutura de dados que receberá as informações do JSON.

struct Eletrodo {
    int id;
    std::string nome;
    std::string tipo;
    double tensao;
    double translacao[3];
};

struct Feixe {
    std::string nome;
    int particulas;
    double massa;
    double carga;
    double corrente;
};

// Função simples para simular a leitura manual das chaves do arquivo JSON
// sem depender imediatamente de compiladores avançados.
bool ler_cenario_manualmente(const std::string &caminho_arquivo) {
    std::ifstream arquivo(caminho_arquivo);
    if (!arquivo.is_open()) {
        std::cerr << "[ERRO] Nao foi possivel abrir o arquivo: " << caminho_arquivo << std::endl;
        return false;
    }

    std::cout << "[PARSER] Abrindo arquivo de configuracao..." << std::endl;
    std::string linha;
    
    // Varredura didática linha por linha para extrair os dados e mostrar no terminal
    while (std::getline(arquivo, linha)) {
        // Busca simples por parâmetros textuais no JSON
        if (linha.find("simulation_mode") != std::string::npos) {
            std::cout << "  -> Modo de Simulacao Detectado: " << linha << std::endl;
        }
        else if (linha.find("mesh_h") != std::string::npos) {
            std::cout << "  -> Tamanho da Malha (h): " << linha << " metros" << std::endl;
        }
        else if (linha.find("name") != std::string::npos || linha.find("nome") != std::string::npos) {
            std::cout << "     * Elemento Configurado: " << linha << std::endl;
        }
        else if (linha.find("voltage") != std::string::npos || linha.find("voltage") != std::string::npos) {
            std::cout << "       Voltagem Dirichlet: " << linha << " V" << std::endl;
        }
    }
    
    arquivo.close();
    return true;
}

int main() {
    std::cout << "==========================================================" << std::endl;
    #if defined(_WIN32) || defined(_WIN64)
    std::cout << "   TESTE DO PARSER DE CONFIGURACAO - EXECUCAO: WINDOWS" << std::endl;
    #else
    std::cout << "   TESTE DO PARSER DE CONFIGURACAO - EXECUCAO: WSL2 (LINUX)" << std::endl;
    #endif
    std::cout << "==========================================================\n" << std::endl;

    std::string arquivo_config = "config_scenario_example.json";

    if (ler_cenario_manualmente(arquivo_config)) {
        std::cout << "\n[SUCESSO] O motor C++ conseguiu ler e mapear o arquivo JSON!" << std::endl;
    } else {
        std::cout << "\n[FALHA] Certifique-se de que o arquivo 'config_scenario_example.json' esta na mesma pasta." << std::endl;
    }

    std::cout << "==========================================================" << std::endl;
    return 0;
}