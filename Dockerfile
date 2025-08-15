FROM ubuntu:24.04

# Install packages needed to build jlm-opt, and packages needed for the benchmarks
RUN apt update && \
    apt install -y \
    git wget pipx python3-psutil python3-pandas python3-matplotlib python3-seaborn \
    lmod locales doxygen make ninja-build just g++ gfortran bear autoconf texinfo \
    \
    build-essential gcc-multilib gcc-mingw-w64 libasound2-dev libpulse-dev libdbus-1-dev \
    libfontconfig-dev libfreetype-dev libgnutls28-dev libgl-dev libunwind-dev \
    libx11-dev libxcomposite-dev libxcursor-dev libxfixes-dev libxi-dev libxrandr-dev \
    libxrender-dev libxext-dev libwayland-bin libwayland-dev libegl-dev \
    libxkbcommon-dev libxkbregistry-dev \
    libxaw7-dev xaw3dg-dev libgtk-3-dev libglib2.0-dev libtree-sitter-dev \
    libgif-dev libxpm-dev libjpeg-dev libtiff-dev libgnutls28-dev \
    libmpfr-dev libxxhash-dev gawk flex bison && \
    \
    apt-get clean && \
    locale-gen en_US.UTF-8 && \
    update-locale

# Install LLVM 18
RUN wget -qO- https://apt.llvm.org/llvm-snapshot.gpg.key | tee /etc/apt/trusted.gpg.d/apt.llvm.org.asc && \
    apt install -y software-properties-common && \
    add-apt-repository deb http://apt.llvm.org/jammy/ llvm-toolchain-jammy-18 main && \
    apt update && \
    apt install -y llvm-18-dev clang-18 clang-format-18 && \
    pipx install "lit~=18.0"

RUN mkdir /mnt
WORKDIR /mnt
