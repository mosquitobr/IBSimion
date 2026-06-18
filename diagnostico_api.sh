#!/bin/bash
# ==============================================================================
# IBSimion 2.0 - Script de Diagnostico de API (IBSimu 1.0.6dev)
# Este script busca nos cabecalhos do seu sistema as assinaturas corretas
# para tratar o numero de fronteiras e os metodos de erro.
# ==============================================================================

echo "=================================================================="
echo "    PROCURANDO ASSINATURAS DE FRONTEIRAS (BOUNDARY) NO IBSIMU"
echo "=================================================================="
# Procura metodos na classe Geometry e Mesh contendo a palavra 'boundary' ou 'ngb'
grep -rnEi "boundary|ngb" /usr/local/include/ibsimu-1.0.6dev/geometry.hpp /usr/local/include/ibsimu-1.0.6dev/mesh.hpp | grep -E "void|int|uint"

echo -e "\n=================================================================="
echo "    PROCURANDO ESTRUTURA DA CLASSE 'ERROR' NO IBSIMU"
echo "=================================================================="
# Exibe a definicao completa da classe Error para vermos seus metodos publicos
cat /usr/local/include/ibsimu-1.0.6dev/error.hpp

echo -e "\n=================================================================="