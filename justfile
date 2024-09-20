set dotenv-load

# Get the JLM_PATH environment variable, or set it to the default
export JLM_PATH := env_var_or_default("JLM_PATH", "jlm")

jlm-commit := "bcfd810264fe03a39f6a903b9850026442f4d056"

default:
    @just --list

# Clone and hard reset to the correct revision of jlm
checkout-jlm-revision:
    #!/usr/bin/bash -eu
    if [[ ! -d {{JLM_PATH}} ]]; then
      echo "{{JLM_PATH}} not found, cloning from git!"
      mkdir {{JLM_PATH}}
      git clone https://github.com/haved/jlm.git {{JLM_PATH}}
    fi

    echo "Checking out revision of jlm: {{jlm-commit}}"
    git -C {{JLM_PATH}} reset --hard {{jlm-commit}}

# Build the release and release-anf targets of jlm-opt
build-jlm-opt:
    #!/usr/bin/bash -eu
    cd {{JLM_PATH}}

    echo "Building release target"
    ./configure.sh --target release
    make jlm-opt -j`nproc`

    echo "Building release-anf target"
    ./configure.sh --target release-anf
    make jlm-opt -j`nproc`

# Flags passed to both benchmarking invocations
common-flags := "--benchmarkIterations=1 --llvmbin " + `llvm-config-18 --bindir`

# Benchmark all C files with the release target of jlm-opt
benchmark-release flags="":
    mkdir -p build statistics
    ./benchmark.py {{common-flags}} --jlm-opt "{{JLM_PATH}}/build-release/jlm-opt" \
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


# Aggregate statistics from runs of both release and release-anf
aggregate-both:
    mkdir -p statistics-out
    ./aggregate.py --stats-in statistics/release --stats-out statistics-out/release
    ./aggregate.py --stats-in statistics/release-anf --stats-out statistics-out/release-anf

# Perform analysis and plotting on the aggregated statistics
analyze-all:
    [ -d statistics-out ] # This recipe only works if statistics-out exists
    mkdir -p results
    @echo "TODO"

# Clean statistics-out and plotted results, but not raw statistics
clean:
    rm -rf statistics-out
    rm -rf results

# Clean every run and result
purge: clean
    rm -rf build
    rm -rf statistics
