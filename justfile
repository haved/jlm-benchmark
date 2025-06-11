set dotenv-load

# Get the JLM_PATH environment variable, or set it to the default
export JLM_PATH := env_var_or_default("JLM_PATH", "jlm")

jlm-commit := "TODO"

llvm-bin := `llvm-config-18 --bindir`

default:
    @just --list

# Clone and hard reset to the correct revision of jlm
checkout-jlm-revision:
    #!/usr/bin/bash -eu
    if [[ ! -d {{JLM_PATH}} ]]; then
      echo "{{JLM_PATH}} not found, cloning from git!"
      git clone https://github.com/phate/jlm.git {{JLM_PATH}}
    fi

    echo "Checking out revision of jlm: {{jlm-commit}}"
    git fetch origin
    git -C {{JLM_PATH}} checkout {{jlm-commit}}

# Build the release and target of jlm-opt
build-release:
    #!/usr/bin/bash -eu
    cd {{JLM_PATH}}

    echo "Building release target"
    ./configure.sh --target release
    make jlm-opt -j`nproc`

build-release-anf:
    #!/usr/bin/bash -eu
    cd {{JLM_PATH}}

    echo "Building release-anf target"
    ./configure.sh --target release-anf
    make jlm-opt -j`nproc`

build-both: build-release build-release-anf

# Flags passed to both benchmarking invocations
common-flags := "--llvmbin " + llvm-bin

# Benchmark all C files with the debug target of jlm-opt
benchmark-debug flags="":
    mkdir -p build statistics
    ./benchmark.py {{common-flags}} --jlm-opt "{{JLM_PATH}}/build-debug/jlm-opt" \
                   --builddir build/debug \
                   --statsdir statistics/debug \
                   {{flags}}

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

    # TODO: Remove precision-only once all results are merged
    rm -rf precision-only
    mkdir -p precision-only
    tar -xzf archives/statistics-out-precision-only-may23.tar.gz -C precision-only

# Perform analysis and plotting on the aggregated statistics
analyze-all:
    [ -d statistics-out ] # This recipe only works if statistics-out exists
    mkdir -p results
    # ./analysis/plot-file-sizes.py --stats statistics-out --out results
    # ./analysis/compare-anf.py --stats statistics-out --out results
    ./analysis/calculate-precision.py --stats statistics-out --out results
    # ./analysis/calculate-precision-selected-llvms.py --stats statistics-out --out results
    ./analysis/calculate-precision-mayalias-reduction.py --stats statistics-out --out results

# Clean statistics-out and plotted results, but not raw statistics
clean:
    rm -rf statistics-out
    rm -rf results

# Clean every run and result
purge: clean
    rm -rf build
    rm -rf statistics
