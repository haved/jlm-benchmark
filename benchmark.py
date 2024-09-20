#!/usr/bin/env python3
import os
import os.path
import subprocess
import sys
import shutil
import hashlib
import pandas as pd
import datetime
import argparse
import re
import tempfile
import threading
import concurrent.futures

class Options:
    DEFAULT_LLVM_BINDIR = "/usr/local/lib/llvm18/bin/"
    DEFAULT_SOURCES = "sources/sources.txt"
    DEFAULT_BUILD_DIR = "build/default/"
    DEFAULT_STATS_DIR = "statistics/default/"
    DEFAULT_JLM_OPT = "../jlm/build-release/jlm-opt"

    def __init__(self, llvm_bindir, build_dir, stats_dir, jlm_opt):
        self.llvm_bindir = llvm_bindir
        self.clang = os.path.join(llvm_bindir, "clang")
        self.clang_link = os.path.join(llvm_bindir, "clang++")
        self.opt = os.path.join(llvm_bindir, "opt")
        self.llvm_link = os.path.join(llvm_bindir, "llvm-link")

        self.build_dir = build_dir
        self.stats_dir = stats_dir

        self.jlm_opt = jlm_opt

    def get_build_dir(self, filename=""):
        return os.path.abspath(os.path.join(self.build_dir, filename))

    def get_stats_dir(self, filename=""):
        return os.path.abspath(os.path.join(self.stats_dir, filename))


options: Options = None

def run_command(args, cwd=None, env_vars=None, silent=True):
    if not silent:
        print(f"# {' '.join(args)}")

    result = subprocess.run(args, cwd=cwd, env=env_vars, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode != 0:
        print(f"Command failed: {args}")
        print(f"Stdout:\n{result.stdout.decode('utf-8')}")
        print(f"Stderr:\n{result.stderr.decode('utf-8')}")
        raise RuntimeError("subprocess failed")

    return (result.stdout, result.stderr)


def move_stats_file(temp_dir, stats_output):
    # Move statisitcs to actual stats_dir, and change filename
    stats_files = os.listdir(temp_dir)
    stats_file, = stats_files # There should be exactly one file
    shutil.move(os.path.join(temp_dir, stats_file), stats_output)


def ensure_folder_exists(path):
    if os.path.exists(path):
        return
    try:
        os.mkdir(path)
    except FileExistsError as e:
        pass # Someone else made the folder, no biggie


class Task:
    def __init__(self, *, name, input_files, output_files, action):
        self.name = name
        self.input_files = input_files
        self.output_files = output_files
        self.action = action

    def run(self):
        self.action()

def any_output_matches(task, regex):
    """Returns true if any one of the output files of the given task contains a match for the given regex"""
    return any(regex.search(of) is not None for of in task.output_files)

def all_outputs_exist(task):
    """Returns true if all outputs of the given task already exist"""
    return all(os.path.exists(of) for of in task.output_files)


def compile_file(tasks, full_name, workdir, cfile, extra_clang_flags, stats_output,
                 env_vars=None, opt_flags=None, jlm_opt_flags=None):
    """
    Compiles the given file with the given arguments to clang.
    :param tasks: the list of tasks to append commands to
    :param full_name: should be a valid filename, unique to the program and source file
    :param workdir: the dir from which clang is invoked
    :param cfile: the name of the c file, relative to workdir
    :param stats_output: the file name and path to use for the statistics file
    :param env_vars: environment variables passed to the executed commands
    :param extra_clang_flags: the flags to pass to clang when making the .ll file
    :param opt_flags: if not None, opt is run with the given flags
    :param jlm_opt_flags: if not None, jlm-opt is run with the given flags
    :return: a tuple with paths to (clang's output, opt's output, jlm-opt's output)
    """
    assert "/" not in full_name

    clang_out = options.get_build_dir(f"{full_name}-clang-out.ll")
    opt_out = options.get_build_dir(f"{full_name}-opt-out.ll")
    jlm_opt_out = options.get_build_dir(f"{full_name}-jlm-opt-out.ll")

    combined_env_vars = os.environ.copy()
    if env_vars is not None:
        combined_env_vars.update(env_vars)

    clang_command = [options.clang, "-Xclang", "-disable-O0-optnone",
                     "-c", cfile,
                     "-S", "-emit-llvm",
                     "-o", clang_out,
                     *extra_clang_flags]
    tasks.append(Task(name=f"Compile {full_name} to LLVM IR",
                      input_files=[cfile],
                      output_files=[clang_out],
                      action=lambda: run_command(clang_command, cwd=workdir, env_vars=combined_env_vars)))

    if opt_flags is not None:
        # use --debug-pass-manager to print more pass info
        opt_command = [options.opt, clang_out, "-S", "-o", opt_out, *opt_flags]
        tasks.append(Task(name=f"opt {full_name}",
                          input_files=[clang_out],
                          output_files=[opt_out],
                          action=lambda: run_command(opt_command, env_vars=combined_env_vars)))
    else:
        opt_out = clang_out

    if jlm_opt_flags is not None:

        def jlm_opt_action():
            with tempfile.TemporaryDirectory(suffix="jlm-bench") as tmpdir:
                jlm_opt_command = [options.jlm_opt, opt_out, "-o", jlm_opt_out, "-s", tmpdir, *jlm_opt_flags]
                run_command(jlm_opt_command, env_vars=combined_env_vars)
                move_stats_file(tmpdir, stats_output)

        tasks.append(Task(name=f"jlm-opt {full_name}",
                          input_files=[opt_out],
                          output_files=[jlm_opt_out, stats_output],
                          action=jlm_opt_action))
    else:
        jlm_opt_out = opt_out

    return (clang_out, opt_out, jlm_opt_out)


def link_and_optimize(tasks, full_name, compiled_cfiles, compiled_non_cfiles, stats_output, env_vars=None,
                      llvm_link_flags=None, opt_flags=None, jlm_opt_flags=None, clang_link_flags=None):
    """
    Links together the given files. The files can be LLVM IR files or object files.
    opt and jlm-opt can only be used if llvm-link is enabled.
    If llvm-link is not enabled, the final clang command will be given all the input files.

    :param tasks: the list of tasks to append commands to
    :param full_name: should be a valid filename, unique to the program
    :param compiled_cfiles: a list of LLVM IR/bitcode files
    :param compiled_non_cfiles: a list of object files
    :param stats_output: the file name and path to use for the statistics file
    :param env_vars: environment variables passed to the executed commands
    :param llvm_link_flags: if not None, llvm-link is run with the given flags
    :param opt_flags: if not None, opt is run with the given flags
    :param jlm_opt_flags: if not None, jlm-opt is run with the given flags
    :param clang_link_flags: if not None, clang is used to create a binary
    """
    assert "/" not in full_name

    llvm_link_out = options.get_build_dir(f"{full_name}-llvm-link-out.ll")
    opt_out = options.get_build_dir(f"{full_name}-opt-out.ll")
    jlm_opt_out = options.get_build_dir(f"{full_name}-jlm-opt-out.ll")
    clang_link_out = options.get_build_dir(f"{full_name}-clang-link-out")

    combined_env_vars = os.environ.copy()
    if env_vars is not None:
        combined_env_vars.update(env_vars)

    if llvm_link_flags is not None:
        llvm_link_command = [options.llvm_link, "-S",
                             *compiled_cfiles, "-o", llvm_link_out, *llvm_link_flags]
        tasks.append(Task(name=f"llvm-link {full_name}",
                          input_files=compiled_cfiles,
                          output_files=llvm_link_out,
                          action=lambda: run_command(llvm_link_command, env_vars=combined_env_vars)))

        if opt_flags is not None:
            # use --debug-pass-manager to print more pass info
            opt_command = [options.opt, llvm_link_out, "-S", "-o", opt_out, *opt_flags]
            tasks.append(Task(name=f"opt {full_name}",
                              input_files=[llvm_link_out],
                              output_files=[opt_out],
                              action=lambda: run_command(opt_command, env_vars=combined_env_vars)))
        else:
            opt_out = llvm_link_out

        if jlm_opt_flags is not None:
            assert llvm_link_flags is not None

            def jlm_opt_action():
                with tempfile.TemporaryDirectory(suffix="jlm-bench") as tmpdir:
                    jlm_opt_command = [options.jlm_opt, opt_out, "-o", jlm_opt_out, "-s", tmpdir, *jlm_opt_flags]
                    run_command(jlm_opt_command, env_vars=combined_env_vars)
                    move_stats_file(tmpdir, stats_output)

            tasks.append(Task(name=f"jlm_opt {full_name}",
                              input_files=[opt_out],
                              output_files=[jlm_opt_out],
                              action=jlm_opt_action))

        else:
            jlm_opt_out = opt_out

        compiled_cfiles = [jlm_opt_out]
    else:
        # Without llvm-link, opt and jlm-opt can not be used
        assert opt_flags is None and jlm_opt_flags is None

    if clang_link_flags is not None:
        clang_command = [CLANG_LINK, *compiled_cfiles, *compiled_non_cfiles, "-o", clang_link_out, *clang_link_flags]
        tasks.append(Task(name=f"clang (link) {full_name}",
                          input_files=compiled_cfiles,
                          output_files=clang_link_out,
                          action=lambda: run_command(clang_command, env_vars=combined_env_vars)))

    return (llvm_link_out, opt_out, jlm_opt_out, clang_link_out)


class Benchmark:
    def __init__(self, name, workdir, cfiles, non_cfiles, linkfiles, linkflags):
        """
        Constructs a benchmark representing a single program.
        The input passed to this constructor represents the "standard" compile+link pipeline.
        This can be customized by modifying the fields on the constructed class.

        :param name: the name of the program
        :param workdir: the directory to compile C files from
        :param cfiles: a list of C files, described as tuples:
         - c file path relative to workdir
         - name of output object file
         - list of flags passed to the compiler for this C file
        :param non_cfiles: a mapping from ofile name, to the full path of a ready .o file on disk
        :param linkfiles: list of object files that were linked
        :param linkflags: list of linker flags, or none to disable linking
        """
        self.name = name
        self.workdir = workdir
        self.cfiles = cfiles
        self.non_cfiles = non_cfiles
        self.linkfiles = linkfiles

        self.extra_clang_flags = []
        self.opt_flags = None
        self.jlm_opt_flags = None
        self.llvm_link_flags = None
        self.linked_opt_flags = None
        self.linked_jlm_opt_flags = None
        self.clang_link_flags = linkflags

    def get_full_cfile_name(self, cfile):
        return f"{self.name}+{cfile}".replace("/", "_")

    def get_tasks(self, stats_dir, env_vars):
        tasks = []

        # Maps from the ofile name used in sources, to the ofile path we use
        cfile_ofile_mapping = {}

        for cfile, ofile, args in self.cfiles:
            full_name = self.get_full_cfile_name(cfile)
            stats_output = os.path.join(stats_dir, f"{full_name}.log")
            _, _, outfile = compile_file(tasks, full_name=full_name, workdir=self.workdir, cfile=cfile,
                                         extra_clang_flags=[*self.extra_clang_flags, *args],
                                         opt_flags=self.opt_flags,
                                         jlm_opt_flags=self.jlm_opt_flags,
                                         env_vars=env_vars,
                                         stats_output=stats_output)
            cfile_ofile_mapping[ofile] = outfile

        compiled_cfiles = []
        compiled_non_cfiles = []

        for ofile in self.linkfiles:
            if ofile in cfile_ofile_mapping:
                compiled_cfiles.append(cfile_ofile_mapping[ofile])
            elif ofile in self.non_cfiles:
                compiled_non_cfiles.append(self.non_cfiles[ofile])
            else:
                raise ValueError(f"No object file found for ofile '{ofile}'")
        stats_output = os.path.join(stats_dir, f"{self.name}.log")
        link_and_optimize(tasks, self.name, compiled_cfiles, compiled_non_cfiles,
                          llvm_link_flags=self.llvm_link_flags,
                          opt_flags=self.linked_opt_flags,
                          jlm_opt_flags=self.linked_jlm_opt_flags,
                          clang_link_flags=self.clang_link_flags,
                          env_vars=env_vars, stats_output=stats_output)

        return tasks


def get_benchmarks(sources_txt):
    """Returns a list of c files to compile"""

    benchmarks = []

    name = None
    workdir = None
    cfiles = None
    ofiles = None

    with open(sources_txt, 'r', encoding='utf-8') as sources_file:
        for line in sources_file:
            line = line.strip()
            if line.startswith("WORKDIR"):
                _, workdir, NAME, name = line.split(" ")
                assert NAME == "NAME"
                workdir = os.path.join(os.path.dirname(sources_txt), workdir)

                assert cfiles is None
                cfiles = []
                ofiles = {}

            elif line.startswith("COMPILE"):
                _, cfile, INTO, ofile, WITHARGS, *args = line.split(" ")
                assert INTO == "INTO"
                assert WITHARGS == "WITHARGS"
                cfiles.append((cfile, ofile, args))

            elif line.startswith("OFILE"):
                _, ofile, COMPILER, _, FULLPATH, fullpath = line.split(" ")
                assert COMPILER == "COMPILER"
                assert FULLPATH == "FULLPATH"
                ofiles[ofile] = fullpath

            elif line.startswith("LINK"):
                assert cfiles is not None
                line_split = line.split(" ")
                into = line_split.index("INTO")
                withargs = line_split.index("WITHARGS")
                assert into + 2 == withargs
                linkfiles = line_split[1:into]
                # target_binary = line_split[into+1]
                ldflags = line_split[withargs+1:]
                benchmarks.append(Benchmark(name, workdir, cfiles, ofiles, linkfiles, ldflags))

                # This makes the program crash if the next line sources.txt is not a WORKDIR
                cfiles = None
                ofiles = None

            else:
                raise ValueError("Unknown line type in sources.txt")

    # Sort benchmarks in order of ascending number of C files
    benchmarks.sort(key=lambda bench: len(bench.cfiles))

    return benchmarks


def run_benchmarks(benchmarks,
                   env_vars,
                   offset=0,
                   limit=float('inf'),
                   stride=1,
                   eager=False,
                   workers=1,
                   dryrun=False):
    start_time = datetime.datetime.now()

    tasks = [task for bench in benchmarks for task in bench.get_tasks(options.get_stats_dir(), env_vars)]
    for i, task in enumerate(tasks):
        task.total_index = i

    if offset != 0:
        tasks = tasks[offset:]
        print(f"Skipping first {offset} tasks, leaving {len(tasks)}")
    if stride != 1:
        tasks = tasks[::stride]
        print(f"Skipping {stride-1} tasks between each task, leaving {len(tasks)}")
    if limit < len(tasks):
        print(f"Limited to {limit} tasks, skipping last {len(tasks)-limit}")
        tasks = tasks[:limit]

    if not eager:
        pre_skip_len = len(tasks)
        tasks = [task for task in tasks if not all_outputs_exist(task)]
        if len(tasks) != pre_skip_len:
            print(f"Skipping {pre_skip_len - len(tasks)} tasks due to laziness, leaving {len(tasks)}")


    executor = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
    # Indices of tasks that have been submitted
    submitted_tasks = set()
    # Output files of some task that has not finished
    files_not_ready = set()

    # First make a pass across all tasks, marking all output files as not ready
    for task in tasks:
        # Mark all outputs as not ready
        for output_file in task.output_files:
            if output_file in files_not_ready:
                print(f"error: Multiple tasks produce the output file {output_file}")
                exit(1)
            files_not_ready.add(output_file)

    def run_task(i, task):
        prefix = f"[{i+1}/{len(tasks)}] ({task.total_index}) {task.name}"
        if dryrun:
            print(f"{prefix} (dry-run)")
        else:
            print(f"{prefix} starting...", flush=True)
            task_start_time = datetime.datetime.now()
            task.run()
            task_duration = (datetime.datetime.now() - task_start_time)
            print(f"{prefix} took {task_duration}", flush=True)

        # Remove all output files from not_ready
        for output_file in task.output_files:
            files_not_ready.remove(output_file)

    running_futures = set()

    # All tasks where none of the input files are in files_not_ready can be submitted
    while len(submitted_tasks) < len(tasks):
        for i, task in enumerate(tasks):
            if i in submitted_tasks:
                continue
            if any(input_file in files_not_ready for input_file in task.input_files):
                continue

            # submit it!
            submitted_tasks.add(i)
            running_futures.add(executor.submit(run_task, i, task))

        wait = concurrent.futures.wait(running_futures, return_when=concurrent.futures.FIRST_COMPLETED)
        running_futures = wait.not_done

        # Check if any of the finished futures raised an exception, and abort
        for d in wait.done:
            if d.exception() is not None:
                raise d.exception()

    # Wait for all tasks to finish
    executor.shutdown(wait=True)

    end_time = datetime.datetime.now()
    print(f"Done in {end_time - start_time}")


def main():
    parser = argparse.ArgumentParser(description='Compile benchmarks using jlm-opt')
    parser.add_argument('--llvmbin', dest='llvm_bindir', action='store', default=Options.DEFAULT_LLVM_BINDIR,
                        help='Specify bindir of LLVM tools and clang')
    parser.add_argument('--sources', dest='sources_file', action='store', default=Options.DEFAULT_SOURCES,
                    help=f'Specify the sources.txt file to scan for benchmarks in [{Options.DEFAULT_SOURCES}]')
    parser.add_argument('--builddir', dest='build_dir', action='store', default=Options.DEFAULT_BUILD_DIR,
                    help=f'Specify the build folder to build benchmarks in. [{Options.DEFAULT_BUILD_DIR}]')
    parser.add_argument('--statsdir', dest='stats_dir', action='store', default=Options.DEFAULT_STATS_DIR,
                    help=f'Specify the folder to put jlm-opt statistics in. [{Options.DEFAULT_STATS_DIR}]')
    parser.add_argument('--jlm-opt', dest='jlm_opt', action='store', default=Options.DEFAULT_JLM_OPT,
                    help=f'Override the jlm-opt binary used. [{Options.DEFAULT_JLM_OPT}]')

    parser.add_argument('--filter', metavar='FILTER', dest='benchmark_filter', action='store', default=None,
                    help='Only include benchmarks whose name includes the given regex')
    parser.add_argument('--list', dest='list_benchmarks', action='store_true',
                    help='List (filtered) benchmarks and exit')

    parser.add_argument('--offset', metavar='O', dest='offset', action='store', default="0",
                    help='Skip the first O tasks. [0]')
    parser.add_argument('--limit', metavar='L', dest='limit', action='store', default=None,
                    help='Execute at most L tasks. [infinity]')
    parser.add_argument('--stride', metavar='S', dest='stride', action='store', default="1",
                    help='Executes every S task, starting at offset [1]')
    parser.add_argument('--eager', dest='eager', action='store_true',
                    help='Makes tasks run even if all their outputs exist')
    parser.add_argument('--dry-run', dest='dryrun', action='store_true',
                    help='Prints the name of each task that would run, but does not run it')

    parser.add_argument('-j', metavar='N', dest='workers', action='store', default='1',
                    help='Run up to N tasks in parallel when possible')

    parser.add_argument('--benchmarkIterations', metavar='N', dest='benchmarkIterations', action='store', default="1",
                    help='The number of times each Andersen solver config should be tested. [1]')

    parser.add_argument('--clean', dest='clean', action='store_true',
                    help='Remove the build and stats folders before running')
    args = parser.parse_args()

    global options
    options = Options(llvm_bindir=args.llvm_bindir,
                      build_dir=args.build_dir,
                      stats_dir=args.stats_dir,
                      jlm_opt=args.jlm_opt)

    dryrun = args.dryrun
    if not dryrun:
        if args.clean:
            shutil.rmtree(options.get_build_dir(), ignore_errors=True)
            shutil.rmtree(options.get_stats_dir(), ignore_errors=True)

        ensure_folder_exists(options.get_build_dir())
        ensure_folder_exists(options.get_stats_dir())

    benchmarks = get_benchmarks(args.sources_file)

    if args.benchmark_filter is not None:
        regex = re.compile(args.benchmark_filter)
        benchmarks = [bench for bench in benchmarks if regex.search(bench.name)]
    
    if args.list_benchmarks:
        print(f"{len(benchmarks)} benchmarks:")
        for bench in benchmarks:
            print(f"  {bench.name:<20} {len(bench.cfiles):4d} C files, {len(bench.non_cfiles):4d} non-C files")
        sys.exit(0)

    offset = int(args.offset)
    stride = int(args.stride)
    limit = float("inf")
    if args.limit is not None:
        limit = int(args.limit)
    eager = args.eager
    workers = int(args.workers)
    if dryrun: # There is no point in multithreading the dryruns
        workers = 1

    env_vars = {
        "JLM_ANDERSEN_TEST_ALL_CONFIGS": args.benchmarkIterations,
        "JLM_ANDERSEN_DOUBLE_CHECK": "YES",
        "LD_LIBRARY_PATH": "/usr/local/lib/llvm18/lib",
    }

    for bench in benchmarks:
        # bench.opt_flags = ["--passes=mem2reg"]
        bench.jlm_opt_flags = ["--AAAndersenAgnostic", "--print-andersen-analysis"]
        # bench.llvm_link_flags = [] #["-internalize"]
        # bench.linked_jlm_opt_flags = ["--AAAndersenAgnostic", "--print-andersen-analysis"]
        # Disable linking with clang
        bench.clang_link_flags = None

    run_benchmarks(benchmarks,
                   env_vars=env_vars,
                   offset=offset,
                   limit=limit,
                   stride=stride,
                   eager=eager,
                   workers=workers,
                   dryrun=dryrun)

if __name__ == "__main__":
    main()
