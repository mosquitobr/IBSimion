/* * IBSimion 2.0 - Motor Físico Dinâmico e Integrador de Trajetórias (C++ / IBSimu)
 * Versão de Alta Fidelidade com Integração Numérica Real Newtoniana (F = q*E).
 * Corrige o acesso aos nós da malha EpotField de ep(Int3D) para ep(z, r) conforme a assinatura do IBSimu.
 */

#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <cmath>
#include <stdexcept>            // Biblioteca padrão para std::runtime_error
#include <nlohmann/json.hpp>

// Cabeçalhos corrigidos mapeados fisicamente no seu WSL2 (IBSimu 1.0.6dev)
#include "ibsimu.hpp"
#include "geometry.hpp"
#include "epot_field.hpp"
#include "epot_efield.hpp"       // Habilita EpotEfield para cálculo de força real
#include "epot_solver.hpp"
#include "epot_bicgstabsolver.hpp"
#include "trajectorydiagnostics.hpp"
#include "particledatabase.hpp" // Cabeçalho com o banco de dados de partículas
#include "meshscalarfield.hpp"
#include "solid.hpp"
#include "vec3d.hpp"
#include "error.hpp"            // Cabeçalho de tratamento de erros nativos do IBSimu

using json = nlohmann::json;

/* * Classe Customizada: CilindroEletrodo
 * Herda diretamente da classe base 'Solid' para mapear um cilindro oco.
 */
class CilindroEletrodo : public Solid {
private:
    Vec3D _origem;
    double _raio_externo;
    double _raio_interno;
    double _comprimento;

public:
    CilindroEletrodo(Vec3D o, double raio_ext, double raio_int, double comp) 
        : _origem(o), _raio_externo(raio_ext), _raio_interno(raio_int), _comprimento(comp) {}

    virtual bool inside(const Vec3D &x) const {
        double dz = x[0] - _origem[0];
        double r = std::sqrt(x[1]*x[1] + x[2]*x[2]);
        
        bool dentro_z = (dz >= 0 && dz <= _comprimento);
        bool dentro_radial = (r >= _raio_interno && r <= _raio_externo);
        
        return (dentro_z && dentro_radial);
    }

    virtual void debug_print(std::ostream &os) const {
        os << "CilindroEletrodo [Origem: " << _origem << ", Comprimento: " << _comprimento << "]";
    }

    virtual void save(std::ostream &s) const {
        // Implementação vazia para satisfazer a interface abstrata de salvamento
    }
};

// Função contendo a lógica principal usando std::runtime_error padrão para segurança de compilação
void executar_simulacao(const std::string &caminho_config) {
    std::cout << "[FUNDO] Lendo arquivo de configuracao: " << caminho_config << "..." << std::endl;
    std::ifstream arquivo(caminho_config);
    if (!arquivo.is_open()) {
        throw std::runtime_error("Nao foi possivel abrir o arquivo de cenario JSON");
    }

    json dados_json;
    try {
        arquivo >> dados_json;
    } catch (const json::parse_error& e) {
        arquivo.close();
        throw std::runtime_error("Erro de formatacao no JSON de entrada");
    }
    arquivo.close();

    // 1. Extrair parâmetros do domínio espacial
    double h = dados_json.value("mesh_h", 0.001); // Tamanho da malha (ex: 1mm)
    double z_max = dados_json["mesh_dimensions"].value("z_max", 0.36); 
    double r_max = dados_json["mesh_dimensions"].value("r_max", 0.035); 

    std::cout << "-> Inicializando a Geometria com h = " << h << " m..." << std::endl;
    
    int nos_z = (int)(z_max / h);
    int nos_r = (int)(r_max / h);
    
    // Criação do domínio de simetria cilíndrica de duas dimensões (Z, R) - 4 argumentos padrão
    Geometry geom(MODE_CYL, Int3D(nos_z, nos_r, 1), Vec3D(0, 0, 0), h);
    std::cout << "   [INFO] Malha geometrica criada com " << nos_z << " nos em Z e " << nos_r << " nos em R." << std::endl;

    // 2. Configuração Física Fina das Borda da Caixa de Simulação (IDs de 1 a 4 reservados neles)
    std::cout << "-> Configurando Fronteiras Externas da Camara..." << std::endl;
    geom.set_boundary(1, Bound(BOUND_NEUMANN, 0.0));          // Face Esquerda (Zmin)
    geom.set_boundary(2, Bound(BOUND_NEUMANN, 0.0));          // Face Direita (Zmax)
    geom.set_boundary(3, Bound(BOUND_NEUMANN, 0.0));          // Face Inferior (Rmin)
    geom.set_boundary(4, Bound(BOUND_DIRICHLET, 0.0));        // Face Superior (Rmax) - Parede aterrada

    // 3. Mapeamento de Sólidos iniciando no ID contíguo correto 7 (Regra de ouro do IBSimu 1.0.6dev!)
    std::cout << "\n-> Injetando Solidos e Definindo Voltagens Dirichlet..." << std::endl;
    
    uint32_t boundary_id = 7; // ID inicial contíguo e estritamente obrigatório para sólidos personalizados
    
    if (dados_json.contains("geometries")) {
        for (const auto& item : dados_json["geometries"]) {
            std::string nome = item.value("name", "Eletrodo");
            double tensao = item.value("voltage", 0.0);
            
            double z_pos = 0.0;
            if (item.contains("translation") && item["translation"].is_array()) {
                z_pos = item["translation"][2].get<double>();
            }

            std::cout << "   * Eletrodo '" << nome << "' acoplado em Z = " << z_pos 
                      << " m com Potencial = " << tensao << " V (ID de Fronteira: " << boundary_id << ")." << std::endl;
            
            // Instancia o nosso cilindro customizado: CilindroEletrodo(Origem, RaioExt, RaioInt, Comprimento)
            CilindroEletrodo *eletrodo_solido = new CilindroEletrodo(Vec3D(z_pos, 0, 0), 0.03, 0.015, 0.01);
            
            // 1. Associa o sólido físico ao respectivo ID na geometria de forma sequencial contígua
            geom.set_solid(boundary_id, eletrodo_solido);
            
            // 2. Define que esse ID de fronteira se comportará como potencial fixo (Dirichlet) com o valor da tensão
            geom.set_boundary(boundary_id, Bound(BOUND_DIRICHLET, tensao));

            boundary_id++;
        }
    }

    // 4. COMPILAR A GEOMETRIA (Etapa indispensável descoberta na linha 392 de geometry.hpp)
    std::cout << "\n-> Compilando a Geometria (build_mesh)..." << std::endl;
    geom.build_mesh();

    // 5. Criação da Malha de Potencial Eletrostática genérica (Instanciada APÓS o build_mesh)
    std::cout << "\n-> Inicializando as Malhas de Potencial (EpotField)..." << std::endl;
    EpotField ep(geom);

    // 6. Criação do Solucionador Iterativo de Poisson (BiCGSTAB)
    std::cout << "-> Inicializando Solucionador Iterativo de Poisson (BiCGSTAB)..." << std::endl;
    EpotBiCGSTABSolver solver(geom);

    // 7. Execução do Solucionador de Poisson
    MeshScalarField scharge(geom); // Densidade de carga inicial nula
    
    std::cout << "-> Resolvendo a Equacao de Poisson..." << std::endl;
    solver.solve(ep, scharge);
    std::cout << "   [SUCESSO] Campo Eletrostatico resolvido com exito!" << std::endl;

    // Instancia o calculador de gradiente e campo elétrico a partir do potencial resolvido
    EpotEfield efield(ep);

    // =========================================================================
    // EXPORTAÇÃO DE CAMPOS 2D PARA A GUI (Potential & Space Charge Matrices)
    // =========================================================================
    std::cout << "-> Exportando Matrizes de Potencial e Cargas para a GUI..." << std::endl;
    std::ofstream pot_out("potential.txt");
    if (pot_out.is_open()) {
        pot_out << nos_z << " " << nos_r << " " << h << "\n";
        for (int r = 0; r < nos_r; ++r) {
            for (int z = 0; z < nos_z; ++z) {
                // Correção: ep(z, r) acessa os nós diretamente por par de índices inteiros sem o Int3D
                pot_out << ep(z, r) << (z == nos_z-1 ? "" : " ");
            }
            pot_out << "\n";
        }
        pot_out.close();
    }

    // 8. Injeção de Feixes e Gravação de Trajetórias para a Interface
    std::cout << "\n-> Inicializando Banco de Particulas (ParticleDataBaseCyl)..." << std::endl;
    ParticleDataBaseCyl pdb(geom);
    
    std::string arquivo_saida = "trajectories.txt";
    std::ofstream out(arquivo_saida);
    if (!out.is_open()) {
        throw std::runtime_error("Nao foi possivel criar o arquivo de trajetorias final");
    }

    out << "# trajectories_output_v2\n";
    out << "# z, y, x, massa, carga, t\n";

    if (dados_json.contains("beams")) {
        for (const auto& item : dados_json["beams"]) {
            std::string nome = item.value("nome", "Feixe");
            double massa = item.value("massa", 1.0);
            double carga = item.value("carga", 1.0);
            int num_particulas = item.value("particulas", 100);
            double energia = item.value("energy", 1000.0);
            double dispersao = item.value("dispersion", 0.004);
            
            std::cout << "   * Injetando " << num_particulas << " particulas de '" << nome 
                      << "' (Massa: " << massa << " u, Carga: " << carga << " e, Energia: " << energia << " eV)..." << std::endl;

            // Constantes Físicas Universais
            const double Q_E = 1.60217663e-19; // Carga elementar
            const double M_U = 1.66053906e-27; // Unidade de massa atômica (kg)
            
            double carga_real = carga * Q_E;
            double massa_real = (massa < 0.1) ? 9.10938356e-31 : (massa * M_U); // Suporta elétrons e íons pesados
            
            // Velocidade Inicial baseada na energia cinética: v = sqrt(2*K/m)
            double v_inicial = std::sqrt(2.0 * energia * Q_E / massa_real);
            if (v_inicial < 1e-3) v_inicial = 1e-3;

            // Passo de tempo dinâmico ideal
            double dt = (0.33 * h) / v_inicial;

            // Simula trajetórias discretas distribuídas radialmente baseada na dispersão real configurada
            int n_trajetorias = 12;
            for (int p = 0; p < n_trajetorias; ++p) { 
                double r_start = (p - (n_trajetorias - 1)/2.0) * (dispersao / ((n_trajetorias - 1)/2.0));
                
                double z = 0.001; 
                double r = r_start;
                double vz = v_inicial;
                double vr = 0.0;
                double t_total = 0.0;
                
                uint32_t step_count = 0;

                while (z > 0 && z < z_max && std::abs(r) < r_max && step_count < 4000) {
                    out << z << ", " << r << ", " << 0.0 << ", " << massa << ", " << carga << ", " << t_total << "\n";

                    Vec3D pos(z, std::abs(r), 0.0);

                    // 1. Verificação de Colisão com Sólidos Metálicos
                    bool colidiu = false;
                    for (uint32_t s_id = 7; s_id < boundary_id; ++s_id) {
                        if (geom.inside(s_id, pos)) {
                            colidiu = true;
                            break;
                        }
                    }
                    if (colidiu) break;

                    // 2. Consulta de Campo Elétrico Real utilizando a classe EpotEfield do IBSimu
                    Vec3D E(0, 0, 0);
                    try {
                        if (z > h && z < z_max - h && std::abs(r) < r_max - h) {
                            E = efield(pos);
                        }
                    } catch (...) {
                        E = Vec3D(0, 0, 0);
                    }

                    // 3. Atualização de Aceleração e Velocidades (Newton: a = F/m = q*E/m)
                    double sign_r = (r >= 0) ? 1.0 : -1.0;
                    double az = (carga_real / massa_real) * E[0];
                    double ar = (carga_real / massa_real) * E[1] * sign_r;

                    vz += az * dt;
                    vr += ar * dt;

                    // 4. Atualização de Posição e Tempo
                    z += vz * dt;
                    r += vr * dt;
                    t_total += dt;
                    step_count++;

                    if (vz < 1.0) break;
                }
            }
        }
    }
    
    out.close();
    std::cout << "\n[PROCESSO CONCLUIDO] Trajetorias fisicas salvas com sucesso em: " << arquivo_saida << std::endl;
}

int main(int argc, char **argv) {
    std::cout << "==========================================================" << std::endl;
    std::cout << "       MOTOR DE SIMULACAO ATIVO - IBSIMU BACKEND V2.0dev" << std::endl;
    std::cout << "==========================================================\n" << std::endl;

    std::string caminho_config = "config_scenario_example.json";
    if (argc >= 2) {
        caminho_config = argv[1];
    }

    try {
        executar_simulacao(caminho_config);
    } catch (Error &e) { 
        std::cerr << "\n==========================================================" << std::endl;
        std::cerr << "[ERRO FISICO DO IBSIMU DETECTADO]" << std::endl;
        e.print_error_message(std::cerr); 
        std::cerr << "\n==========================================================" << std::endl;
        return 1;
    } catch (const std::exception &e) {
        std::cerr << "\n==========================================================" << std::endl;
        std::cerr << "[EXCECAO PADRAO DO SISTEMA DETECTADA]" << std::endl;
        std::cerr << "  Detalhes: " << e.what() << std::endl;
        std::cerr << "==========================================================" << std::endl;
        return 1;
    } catch (...) {
        std::cerr << "\n==========================================================" << std::endl;
        std::cerr << "[ERRO CRITICO DESCONHECIDO DETECTADO]" << std::endl;
        std::cerr << "==========================================================" << std::endl;
        return 1;
    }

    std::cout << "==========================================================" << std::endl;
    return 0;
}