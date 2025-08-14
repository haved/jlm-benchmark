set dotenv-load

# Set the default JLM_PATH environment variable, unless specified in .env
export JLM_PATH := env_var_or_default("JLM_PATH", "jlm")

# This is the commit used for artifact evaluation.
# It is already included in the artifact download.
jlm-commit := "7b9dad19d429b88b47363e61fb9f8d8d7c0b0f41"

# Use LLVM18 for processing benchmarks
llvm-bin := `llvm-config-18 --bindir`

# Compile jlm-opt using the system C++ compiler, unless specified in .env
JLM_CXX := env_var_or_default("JLM_CXX", "c++")

default:
    @just --list

# Clone and checkout the artifact revision of jlm
checkout-jlm-revision:
    #!/usr/bin/bash -eu
    if [[ ! -d {{JLM_PATH}} ]]; then
      echo "{{JLM_PATH}} not found, cloning from git!"
      git clone https://github.com/phate/jlm.git {{JLM_PATH}}
    fi

    echo "Checking out revision of jlm: {{jlm-commit}}"
    git -C {{JLM_PATH}} checkout {{jlm-commit}}

# Build the release and target of jlm-opt
build-release:
    #!/usr/bin/bash -eu
    cd {{JLM_PATH}}

    echo "Building release target"
    ./configure.sh --target release CXX={{JLM_CXX}}
    make jlm-opt -j`nproc`

build-release-anf:
    #!/usr/bin/bash -eu
    cd {{JLM_PATH}}

    echo "Building release-anf target"
    ./configure.sh --target release-anf CXX={{JLM_CXX}}
    make jlm-opt -j`nproc`

# Remove builds of jlm-opt
clean-jlm-builds:
    rm -rf {{JLM_PATH}}/build-release
    rm -rf {{JLM_PATH}}/build-release-anf

# Flags passed to both benchmarking invocations
common-flags := "--llvmbin " + llvm-bin

# Benchmark all C files with the release target of jlm-opt
benchmark-release flags="":
    mkdir -p build statistics
    ./benchmark.py {{common-flags}} \
                   --jlm-opt "{{JLM_PATH}}/build-release/jlm-opt" \
                   --builddir build/release \
                   --statsdir statistics/release \
                   {{flags}}

# Benchmark all C files with the release-anf target of jlm-opt
benchmark-release-anf flags="":
    mkdir -p build statistics
    ./benchmark.py {{common-flags}} --jlm-opt "{{JLM_PATH}}/build-release-anf/jlm-opt" \
                   --builddir build/release-anf \
                   --statsdir statistics/release-anf \
                   {{flags}}

# Benchmark all C files with both the release and release-anf targets
benchmark-both flags="": (benchmark-release flags) (benchmark-release-anf flags)

# Aggregate statistics from runs of both release and release-anf
aggregate:
    mkdir -p statistics-out
    ./analysis/aggregate.py --clean --stats-in statistics --stats-out statistics-out

# Extract aggregated statistics from an archived run instead of aggregating statistics from the statistics folder
extract-aggregated:
    rm -rf statistics-out
    tar -xzf archives/statistics-out-may21.tar.gz -C .

# Perform analysis and plotting on the aggregated statistics
analyze-all:
    [ -d statistics-out ] # This recipe only works if statistics-out exists
    mkdir -p results
    ./analysis/plot-file-sizes.py --stats statistics-out --out results
    ./analysis/compare-anf.py --stats statistics-out --out results
    ./analysis/calculate-precision.py --stats statistics-out --out results

# Clean statistics-out and plotted results, but not raw statistics
clean:
    rm -rf statistics-out
    rm -rf results

# Clean every run and result
purge: clean
    rm -rf build
    rm -rf statistics
