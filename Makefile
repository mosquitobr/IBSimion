# Makefile de Automacao para o Motor de Fisica IBSimion 2.0
# Atualizado para utilizar a versao "dev" (ibsimu-1.0.6dev) identificada com sucesso.

CXX = g++
CXXFLAGS = -Wall -g -std=c++11 `pkg-config --cflags ibsimu-1.0.6dev`
LDFLAGS = `pkg-config --libs ibsimu-1.0.6dev`

# Alvo principal (compila tudo)
all: test_ibsimu_linkage parser_real_de_json ibsimion_backend_v2

# Compila o teste de linkagem fisica
test_ibsimu_linkage: test_ibsimu_linkage.cpp
	@echo "[COMPILANDO] Gerando binario de teste com linkagem IBSimu..."
	$(CXX) $(CXXFLAGS) test_ibsimu_linkage.cpp -o test_ibsimu_linkage $(LDFLAGS)
	@echo "[PRONTO] Executavel 'test_ibsimu_linkage' gerado com sucesso!"

# Compila o parser simples de JSON
parser_real_de_json: parser_real_de_json_em_c.cpp
	@echo "[COMPILANDO] Gerando binario do Parser de Cenarios JSON..."
	$(CXX) -std=c++11 parser_real_de_json_em_c.cpp -o parser_real_de_json
	@echo "[PRONTO] Executavel 'parser_real_de_json' gerado com sucesso!"

# Compila o motor fisico real integrado
ibsimion_backend_v2: ibsimion_backend_v2.cpp
	@echo "[COMPILANDO] Gerando o Motor Fisico Real (IBSimion Backend V2)..."
	$(CXX) $(CXXFLAGS) ibsimion_backend_v2.cpp -o ibsimion_backend_v2 $(LDFLAGS)
	@echo "[PRONTO] Executavel 'ibsimion_backend_v2' gerado com sucesso!"

# Limpa os executaveis gerados na pasta
clean:
	@echo "[LIMPEZA] Removendo executaveis temporarios..."
	rm -f test_ibsimu_linkage parser_real_de_json teste_parser ibsimion_backend_v2
	@echo "[LIMPEZA] Concluida!"