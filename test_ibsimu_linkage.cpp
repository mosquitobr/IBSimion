/* * IBSimion 2.0 - Teste de Linkagem e Integracao da Biblioteca IBSimu
 * Este programa realiza um teste mínimo para garantir que o compilador GCC
 * consegue encontrar as definicoes de cabecalho e os binarios compilados do IBSimu.
 */

#include <iostream>
// Importa o cabecalho de vetores tridimensionais nativo do IBSimu
#include "vec3d.hpp"

int main() {
    std::cout << "==========================================================" << std::endl;
    std::cout << "      TESTE DE LINKAGEM FISICA - IBSIMU 1.0.6" << std::endl;
    std::cout << "==========================================================\n" << std::endl;

    try {
        // Tenta instanciar um vetor de forca/posicao tridimensional do IBSimu
        std::cout << "[IBSIMU] Tentando instanciar objeto geometrico Vec3D..." << std::endl;
        
        Vec3D vetor_teste(1.23, 4.56, -7.89);
        
        std::cout << "  -> [SUCESSO] Objeto Vec3D criado fisicamente na memoria!" << std::endl;
        std::cout << "  -> Coordenadas registradas: " 
                  << "Z = " << vetor_teste[0] << " m | "
                  << "Y = " << vetor_teste[1] << " m | "
                  << "X = " << vetor_teste[2] << " m" << std::endl;

    } catch (const std::exception& e) {
        std::cerr << "[ERRO] Falha catastrofica ao processar dados do IBSimu: " << e.what() << std::endl;
        return 1;
    }

    std::cout << "\n==========================================================" << std::endl;
    std::cout << "STATUS: O ambiente C++ esta pronto para simular campos reais!" << std::endl;
    std::cout << "==========================================================" << std::endl;
    
    return 0;
}