# 1. Usa uma imagem oficial estável do Ubuntu como base
FROM ubuntu:22.04

# 2. Evita travamentos de prompt durante a instalação de pacotes
ENV DEBIAN_FRONTEND=noninteractive

# 3. Instala as ferramentas exigidas no manual (incluindo a biblioteca JSON)
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    pkg-config \
    libgsl-dev \
    libfontconfig1-dev \
    libfreetype6-dev \
    libcairo2-dev \
    libpng-dev \
    zlib1g-dev \
    automake \
    autoconf \
    libtool \
    nlohmann-json3-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. Baixa, reconfigura e instala o IBSimu usando o passo a passo oficial do Git do manual
WORKDIR /src
RUN git clone https://git.code.sf.net/p/ibsimu/code ibsimu && \
    cd ibsimu && \
    ./reconf && \
    ./configure --prefix=/usr --without-opengl --without-gtk3 && \
    make -j$(nproc) && \
    make install

# 5. Define o diretório de trabalho interno para o seu projeto
WORKDIR /app

# 6. Copia o código-fonte, o Makefile e o arquivo de configuração para o container
COPY ibsimion_backend_v2.cpp /app/
COPY Makefile /app/
COPY config_scenario_example.json /app/

# 7. Compila o seu backend C++
RUN make ibsimion_backend_v2

# 8. Define o comando padrão que será executado ao iniciar o container
CMD ["./ibsimion_backend_v2"]