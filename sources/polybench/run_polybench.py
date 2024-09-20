#!/usr/bin/env python3
import os
import os.path
import subprocess
import sys
import hashlib
import pandas as pd


LLVM_BINDIR = "/usr/bin/"
CLANG = os.path.join(LLVM_BINDIR, "clang")
OPT = os.path.join(LLVM_BINDIR, "opt")
LLC = os.path.join(LLVM_BINDIR, "llc")

JLM_BINDIR = "../jlm/bin/"
JLM_OPT = os.path.join(JLM_BINDIR, "jlm-opt")

JLM_OPT_O3_FLAGS = """\
--FunctionInlining --InvariantValueRedirection --NodeReduction --DeadNodeElimination \
--ThetaGammaInversion --InvariantValueRedirection --DeadNodeElimination --NodePushOut \
--InvariantValueRedirection --DeadNodeElimination --NodeReduction --CommonNodeElimination \
--DeadNodeElimination --NodePullIn --InvariantValueRedirection --DeadNodeElimination \
--LoopUnrolling --InvariantValueRedirection""".split(" ")

JLM_OPT_STEENSGAARD_FLAGS = ["--AASteensgaardRegionAware"] + JLM_OPT_O3_FLAGS

JLM_OPT_ANDERSEN_FLAGS = ["--AAAndersenRegionAware"] + JLM_OPT_O3_FLAGS

POLYBENCH_FOLDER = "polybench-c-4.2.1-beta/"
BUILD_FOLDER = "build/"

if not os.path.exists(BUILD_FOLDER):
    os.mkdir(BUILD_FOLDER)


def run_command(args, silent=False):
    if not silent:
        print(f"# {' '.join(args)}")

    result = subprocess.run(args, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        print(f"Command failed: {args}")
        print(f"Stdout:\n{result.stdout.decode('utf-8')}")
        print(f"Stderr:\n{result.stderr.decode('utf-8')}")
        sys.exit(1)

    return (result.stdout, result.stderr)

edgecounts = pd.DataFrame()

class Benchmark:
    def __init__(self, configuration, benchmark, skip_opt=False, skip_jlm=False,
                 clang_flags=None, opt_flags=None, jlm_opt_flags=None, llc_flags=None, link_flags=None):
        self.configuration = configuration
        self.benchmark_name, self.benchmark_cpath = benchmark
        self.name = f"{self.benchmark_name}_{self.configuration}"
        self.skip_opt = skip_opt
        self.skip_jlm = skip_jlm
        self.clang_flags = ["-O0"] if clang_flags is None else clang_flags
        self.opt_flags = [] if opt_flags is None else opt_flags
        self.jlm_opt_flags = [] if jlm_opt_flags is None else jlm_opt_flags
        self.llc_flags = ["-O3"] if llc_flags is None else llc_flags
        self.link_flags = ["-no-pie"] if link_flags is None else link_flags

    def _compile_benchmark(self, polybench_mode=None):

        if polybench_mode is None:
            polybench_mode = "-DPOLYBENCH_TIME -DNDEBUG"
        if not isinstance(polybench_mode, list):
            polybench_mode = polybench_mode.split(" ")

        # Calculate paths to polybench related files
        cpath = os.path.join(POLYBENCH_FOLDER, self.benchmark_cpath)
        cfolder = os.path.dirname(cpath)
        utilities = os.path.join(POLYBENCH_FOLDER, "utilities")
        polybench_c = os.path.join(utilities, "polybench.c")

        clang_out = os.path.join(BUILD_FOLDER, f"{self.name}-clang-out.ll")
        opt_out = os.path.join(BUILD_FOLDER, f"{self.name}-opt-out.ll")
        jlm_opt_out = os.path.join(BUILD_FOLDER, f"{self.name}-jlm-opt-out.ll")
        llc_out = os.path.join(BUILD_FOLDER, f"{self.name}-llc-out.o")
        binary_out = os.path.join(BUILD_FOLDER, self.name)
        polybench_o = os.path.join(BUILD_FOLDER, "polybench.o")

        clang_command = [CLANG, *polybench_mode, "-c", cpath,
                         "-I", cfolder, "-I", utilities, "-S", "-emit-llvm",
                         "-o", clang_out, *self.clang_flags]
        run_command(clang_command)

        # Remove any optnone attributes from the .ll
        run_command(["sed", "-i", "-E", "s/optnone//", clang_out])

        if self.skip_opt:
            opt_out = clang_out
        else:
            # use --debug-pass-manager to print more pass info
            opt_command = [OPT, clang_out, "-S", "-o", opt_out, *self.opt_flags]
            run_command(opt_command)

        if self.skip_jlm:
            jlm_opt_out = opt_out
        else:
            jlm_opt_command = [JLM_OPT, opt_out, "-o", jlm_opt_out, *self.jlm_opt_flags]
            cmpout, _ = run_command(jlm_opt_command)
            edgecounts.loc[self.benchmark_name, self.configuration] = cmpout.decode('utf-8')

        llc_command = [LLC, jlm_opt_out, "-filetype=obj", "-o", llc_out, *self.llc_flags]
        run_command(llc_command)

        # Now link with the rest of polybench to get the final binary
        clang_polybench_c = [CLANG, *polybench_mode, "-O3", "-c", polybench_c, "-o", polybench_o]
        run_command(clang_polybench_c)

        link_command = [CLANG, polybench_o, llc_out, "-lm", "-o", binary_out, *self.link_flags]
        run_command(link_command)

        return binary_out

    def validate_result(self, expected=None):
        """Compiles the benchmark binary with -DPOLYBENCH_DUMP_ARRAYS and prints/returns a hash of the output"""

        binary = self._compile_benchmark(polybench_mode="-DPOLYBENCH_DUMP_ARRAYS")
        _, output = run_command([binary], silent=False)

        md5 = hashlib.md5()
        md5.update(output)
        checksum = md5.hexdigest()

        if expected is not None and expected != checksum:
            print("Validation output did not match expected for test {self.name}!")
            sys.exit(1)

        return checksum

    def run(self, repetitions=10, discard=2, df=None):
        """Compiles the benchmark binary with -DPOLYBENCH_TIME and prints the runtime"""
        binary = self._compile_benchmark()
        return

        runtimes = []
        for _ in range(repetitions):
            stdout, _ = run_command([binary], silent=False)
            runtimes.append(float(stdout.decode('utf-8')))

        runtimes.sort()
        kept_runtimes = runtimes[discard:len(runtimes)-discard]
        deviation = kept_runtimes[-1]/kept_runtimes[0]
        if deviation > 1.04:
            print(f"WARNING: Largest deviation of benchmark {self.name} was {deviation}, after discarding {2*discard} extremums")
            print(f"Full list of runtimes: {runtimes}")

        average = sum(kept_runtimes) / len(kept_runtimes)
        print(f"RESULT: {self.name}: {average:.5f}")

        if df is not None:
            df.loc[self.benchmark_name, self.configuration] = average

        return average


def get_benchmark_list():
    """Returns a list of paths to .c files, one per benchmark"""
    list_file = os.path.join(POLYBENCH_FOLDER, "utilities/benchmark_list")
    with open(list_file, "r", encoding="utf-8") as listfd:
        return [bench.strip() for bench in listfd.readlines()]


def main():
    benchmark_files = get_benchmark_list()
    runtimes = pd.DataFrame()

    for benchmark_file in benchmark_files:
        benchmark_name = os.path.basename(benchmark_file).split(".")[0]

        # Skip slowest
        if benchmark_name == "floyd-warshall":
            continue

        benchmark = (benchmark_name, benchmark_file)

        clang_O3 = Benchmark("clang_O3", benchmark,
                          clang_flags=["-O3"], skip_opt=True, skip_jlm=True)
        #clang_O3.run(df=runtimes)
        #ground_truth = clang_O3.validate_result()

        clang_O0 = Benchmark("clang_O0", benchmark,
                          clang_flags=["-O0"], skip_opt=True, skip_jlm=True)
        #clang_O0.run(df=runtimes)

        jlm_opt_O3 = Benchmark("jlm_opt_O3", benchmark,
                               clang_flags=["-O0"], jlm_opt_flags=JLM_OPT_O3_FLAGS)
        #jlm_opt_O3.run(df=runtimes)

        mem2reg_jlm_opt_O3 = Benchmark("mem2reg_jlm_opt_O3", benchmark,
                                       clang_flags=["-O0"], opt_flags=["--passes=mem2reg"], jlm_opt_flags=JLM_OPT_O3_FLAGS)
        #mem2reg_jlm_opt_O3.run(df=runtimes)

        jlm_opt_andersen_O3 = Benchmark("jlm_opt_andersen_O3", benchmark,
                                       clang_flags=["-O0"], skip_opt=True, jlm_opt_flags=JLM_OPT_ANDERSEN_FLAGS)
        jlm_opt_andersen_O3.run(df=runtimes)
        #jlm_opt_andersen_O3.validate_result(df=runtimes)

        mem2reg_jlm_opt_andersen_O3 = Benchmark("mem2reg_jlm_opt_andersen_O3", benchmark,
                                       clang_flags=["-O0"], opt_flags=["--passes=mem2reg"], jlm_opt_flags=JLM_OPT_ANDERSEN_FLAGS)
        #mem2reg_jlm_opt_andersen_O3.run(df=runtimes)

        jlm_opt_steensgaard_O3 = Benchmark("jlm_opt_steensgaard_O3", benchmark,
                                       clang_flags=["-O0"], skip_opt=True, jlm_opt_flags=JLM_OPT_STEENSGAARD_FLAGS)
        jlm_opt_steensgaard_O3.run(df=runtimes)
        #jlm_opt_steensgaard_O3.validate_result(df=runtimes)

        mem2reg_jlm_opt_steensgaard_O3 = Benchmark("mem2reg_jlm_opt_steensgaard_O3", benchmark,
                                       clang_flags=["-O0"], opt_flags=["--passes=mem2reg"], jlm_opt_flags=JLM_OPT_STEENSGAARD_FLAGS)
        #mem2reg_jlm_opt_steensgaard_O3.run(df=runtimes)

        mem2reg_only = Benchmark("mem2reg_only", benchmark,
                                       clang_flags=["-O0"], opt_flags=["--passes=mem2reg"], skip_jlm=True)
        #mem2reg_only.run(df=runtimes)

    #runtimes.to_csv("edgecounts.csv")
    edgecounts.to_csv("edgecounts.csv")


if __name__ == "__main__":
    main()
