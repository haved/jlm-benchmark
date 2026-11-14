#!/usr/bin/env python3
import sys
import os
import subprocess
import tempfile
from pathlib import Path

"""
Drop-in replacement for a compiler driver like clang.
For compilation of single C files (-c), the command is converted into a clang + opt + jlm-opt pipeline.
It matches 1:1 with the pipeline defined in ./benchmark.py for sroa-raw with all techniques enabled.

The script finds jlm-opt using the environment variable JLM_OPT = <path/to/jlm-opt>.
If it does not exist, "${JLM_PATH}/build-release/jlm-opt" is tried instead.

clang and opt and llc are found using "${CLANG}", "${OPT}" and "${LLC}",
defaulting to "clang-18", "opt-18" and "llc-18".
"""

def get_paths():
    clang = os.environ.get("CLANG", "clang-18")
    opt = os.environ.get("OPT", "opt-18")
    llc = os.environ.get("LLC", "llc-18")
    jlm_opt = os.environ.get("JLM_OPT", None)

    if jlm_opt is None:
        jlm_path = os.environ.get("JLM_PATH", None)
        if jlm_path is None:
            raise ValueError("Neither JLM_OPT nor JLM_PATH are defined")

        jlm_opt = os.path.join(jlm_path, "build-release/jlm-opt")

    def check_absolute(path):
        if "/" in path and not path.startswith("/"):
            raise ValueError(f"Binaries need to be on aboslute paths. Got: {jlm_opt}")

    check_absolute(clang)
    check_absolute(opt)
    check_absolute(llc)
    check_absolute(jlm_opt)

    return clang, opt, llc, jlm_opt

CLANG, OPT, LLC, JLM_OPT = get_paths()

CLANG_FLAGS = ["-Os", "-Xclang", "-disable-llvm-passes", "-fno-vectorize", "-fno-slp-vectorize", "-fno-inline"]
OPT_FLAGS = ["-passes=sroa<modify-cfg>"]
JLM_OPT_FLAGS = ["--CommonNodeElimination", "--InvariantValueRedirection", "--DeadNodeElimination", "--NodeReduction", "--DeadNodeElimination", "--RvsdgTreePrinter", "--AAAndersenRegionAware", "--DeadNodeElimination", "--NodeReduction", "--StoreValueForwarding"]
for _ in range(3):
    JLM_OPT_FLAGS.extend(["--NodePushOut", "--CommonNodeElimination", "--IOBarrierElimination", "--StoreValueForwarding"])
JLM_OPT_FLAGS.extend(["--CommonNodeElimination", "--InvariantValueRedirection", "--NodeReduction", "--DeadNodeElimination"])
# The clang invocation used to link
LLC_FLAGS = ["--relocation-model=static", "-filetype=obj", "-O2"]
# When clang is used for linking, which extra flags should be added
CLANG_LINK_FLAGS = ["-no-pie"]

# Print all commands before executing
VERBOSE=True

# Flags skipped for C compilation
SKIP_CFLAGS = [
    "-O",
    "-O0",
    "-O1",
    "-O2",
    "-O3",
    "-Os",
    "-Oz",
    "-Ofast",
    "-g",
    "-g1",
    "-g2",
    "-g3",
    "-ggdb0",
    "-ggdb1",
    "-ggdb2",
    "-ggdb3",
    "--debug",
    "-gdwarf",
    "-gdwarf-1",
    "-gdwarf-2",
    "-gdwarf-3",
    "-gdwarf-4",
    "-gdwarf-5",
    "-gdwarf32",
    "-gdwarf64",
    "-gfull",
    ]

# When standalone, the next argument belongs to it
CFLAGS_WITH_ARGUMENTS = [
    "-I",
    "-include",
    "-D",
    "-o",
    "-x",
    "-MF",
    "-MT",
]

def extract_flags_and_positional(args):
    """
    Extracts positional arguments and flags, placing them in two lists

    For single options, returns them as a string.
    Options with arguments, like -o file and -o=file, are extracted to tuples ("-o", "file")
    """
    flags = []
    positional = []
    flag_in_progress = None
    for arg in args:
        if arg.startswith("-"):
            if arg in CFLAGS_WITH_ARGUMENTS:
                flag_in_progress = arg
                continue

            if "=" in arg:
                pos = arg.find("=")
                flags.append((arg[:pos], arg[pos+1:]))
                continue

            # Just a regular flag
            flags.append(arg)
        elif flag_in_progress is not None:
            flags.append((flag_in_progress, arg))
            flag_in_progress = None
        else:
            positional.append(arg)

    if flag_in_progress is not None:
        raise ValueError(f"command ended with option that takes an argument: {args}")

    return flags, positional

def extract_flag_with_argument(flags, flag_to_find):
    """
    Finds a flag if it exists, removes it, and extracts its value.
    For flags without arguments, the value is True for found.
    Flags not found yield None.
    Multiple different values for the same flag raises a ValueError

    :param flag_to_find: the flag (or a list of flags) to extract.

    Returns (value/True/None, flags left)
    """
    if not isinstance(flag_to_find, list):
        flag_to_find = [flag_to_find]

    flags_left = []
    value_found = []

    for flag in flags:
        if isinstance(flag, tuple):
            key, value = flag
            if key in flag_to_find:
                value_found.append(value)
                continue
        else:
            if flag in flag_to_find:
                value_found.append(true)
                continue

        flags_left.append(flag)

    if len(value_found) > 1:
        # This is fine if they all have the same value
        if any(x != value_found[0] for x in value_found):
            raise ValueError(f"Multiple different values provided for flag(s) {flag_to_find}: {value_found}")
    if value_found:
        return value_found[0], flags_left

    return None, flags_left

def extract_cflags(flags):
    cflags = []
    for flag in flags:
        if isinstance(flag, tuple):
            key, value = flag
            if key not in SKIP_CFLAGS:
                cflags.append(f"{key}={value}")
        elif flag not in SKIP_CFLAGS:
            cflags.append(flag)
    return cflags

def execute_command(command):
    """
    Runs the given command in the current working directory
    """

    # Convert all parts to strings
    command = [str(part) for part in command]

    textual = ' '.join(f'"{part}"' if ' ' in part else part for part in command)
    if VERBOSE:
        print(textual)

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"{sys.argv[0]}: subcommand failed with return code {e.returncode}: {textual}")
        raise

def execute_intercepted_command(input_file, flags):
    """
    Convert the input_file to an .o file optimized by jlm-opt
    """

    stem = Path(input_file).stem

    output_file, flags = extract_flag_with_argument(flags, ["-o", "--output"])
    # When no output file is specified, create one in the cwd using the stem of the input file
    # This is the behavior of clang as well
    if output_file is None:
        output_file = stem + ".o"

    # Extract the flags to keep from the original clang invocation, as a list of strings
    cflags = extract_cflags(flags)

    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        clang_out = tmpdir / (stem + "-clang.ll")
        opt_out = tmpdir / (stem + "-opt.ll")
        jlm_opt_out = tmpdir / (stem + "-jlm-opt.ll")

        commands = []

        clang_command = [CLANG, "-c", "-S", "-emit-llvm", *cflags, *CLANG_FLAGS, input_file, "-o", clang_out]
        commands.append(clang_command)

        if OPT_FLAGS is not None:
            opt_command = [OPT, "-S", *OPT_FLAGS, clang_out, "-o", opt_out]
            commands.append(opt_command)
        else:
            opt_out = clang_out

        if JLM_OPT_FLAGS is not None:
            jlm_opt_command = [JLM_OPT, *JLM_OPT_FLAGS, opt_out, "-o", jlm_opt_out]
            commands.append(jlm_opt_command)
        else:
            jlm_opt_out = opt_out

        llc_command = [LLC, *LLC_FLAGS, jlm_opt_out, "-o", output_file]
        commands.append(llc_command)

        for command in commands:
            execute_command(command)

def execute_link_command(args):
    """
    Pass the linking command to clang to link
    """
    command = [CLANG, *args, *CLANG_LINK_FLAGS]
    execute_command(command)

def main():
    args = sys.argv[1:]
    if "-c" not in args:
        return execute_link_command(args)

    flags, positional = extract_flags_and_positional(args)

    if len(positional) > 1:
        extracted, _ = extract_flag_with_argument(flags, ["-o", "--output"])
        if extracted is not None:
            raise ValueError("Multiple input files is not supported when -o is supplied")

    for input_file in positional:
        execute_intercepted_command(input_file, flags)

if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
