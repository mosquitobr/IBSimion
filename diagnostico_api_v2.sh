#!/bin/bash
# ==============================================================================
# IBSimion 2.0 - Script de Diagnóstico de API V2 (IBSimu 1.0.6dev)
# Procura todas as ocorrências de métodos de contorno e sólidos sem filtros rígidos.
# ==============================================================================

echo "=================================================================="
echo "    PROCURANDO TODOS OS MÉTODOS DE FRONTEIRA (BOUNDARIES)"
echo "=================================================================="
# Lista qualquer linha que declare métodos ou variáveis com 'bound' ou 'ngb'
grep -rnEi "boundaries|boundary|ngb" /usr/local/include/ibsimu-1.0.6dev/geometry.hpp /usr/local/include/ibsimu-1.0.6dev/mesh.hpp

echo -e "\n=================================================================="
echo "    PROCURANDO COMO OS SÓLIDOS SÃO ADICIONADOS NA GEOMETRIA"
echo "=================================================================="
# Lista métodos que lidam com sólidos na Geometria
grep -rnEi "solid" /usr/local/include/ibsimu-1.0.6dev/geometry.hpp

echo "=================================================================="