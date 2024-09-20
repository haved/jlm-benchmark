#!/usr/bin/env python3

import sys
from os.path import dirname, basename, join
from os import listdir

BANNED_ARGS = [
    "",
    "-c",
    "-O0",
    "-O1",
    "-O2",
    "-O3",
    "-Os",
    "-Oz",
     "-JAAAndersenAgnostic",
     "-JAAAndersenRegionAware"
]

C_COMPILERS = [
    "jlc",
    "clang",
    "gcc",
    "/usr/local/lib/llvm18/bin/clang"
]

LINKERS = [
    "clang",
    "clang++",
    "/usr/local/lib/llvm18/bin/clang",
    "/usr/local/lib/llvm18/bin/clang++"
]

OTHER_COMPILERS = [
    "clang++",
    "/usr/local/lib/llvm18/bin/clang++",
    "gfortran",
    "/usr/bin/gfortran"
]

def is_cc_command(cmd):
    args = cmd.split()
    if args[0] in C_COMPILERS and "-c" in args:
        return args[1:]
    return None

def is_link_command(cmd):
    args = cmd.split()
    if args[0] in LINKERS and "-c" not in args:
        return args[1:]
    return None

def is_other_compiler(cmd):
    args = cmd.split()
    if args[0] in OTHER_COMPILERS and "-c" in args and "-o" in args:
        return args[0], args[args.index("-o")+1]
    return None, None

def print_from_make_out(make_out):
    build_dir = dirname(make_out)
    benchmark_dir = dirname(dirname(build_dir))
    source_dir = join(benchmark_dir, "src")
    full_name = basename(benchmark_dir).split("_")[0]
    name = full_name.split(".")[1]

    make_out_basename = basename(make_out)
    if make_out_basename not in ["make.out", f"make.{name}_r.out"]:
        full_name += "." + make_out_basename.split(".")[1]

    with open(make_out, 'r', encoding='utf-8') as make_out_file:
        print(f"WORKDIR {source_dir} NAME {full_name}")
        for line in make_out_file:
            line = line.strip()

            c_compiler_args = is_cc_command(line)
            linker_args = is_link_command(line)
            compiler, other_ofile = is_other_compiler(line)

            if c_compiler_args is not None:
                dashC, dashO, ofile, *args, cfile = c_compiler_args
                assert dashC == "-c"
                assert dashO == "-o"

                args = [arg for arg in args if arg not in BANNED_ARGS]

                print(f"COMPILE {cfile} INTO {ofile} WITHARGS {' '.join(args)}")

            elif linker_args is not None:
                # This is a linking command
                *args, dashO, ofile = linker_args
                assert dashO == "-o"
                flags = [arg for arg in args if arg.startswith("-")]
                objfiles = [arg for arg in args if not arg.startswith("-")]

                flags = [arg for arg in flags if arg not in BANNED_ARGS]

                print(f"LINK {' '.join(objfiles)} INTO {ofile} WITHARGS {' '.join(flags)}")

            elif other_ofile is not None:
                # If the benchmark uses other compilers, such as clang++ or gfortran,
                print(f"OFILE {other_ofile} COMPILER {compiler} FULLPATH {join(build_dir, other_ofile)}")

def print_from_last_make_out(bench, builddir):
    dirlist = listdir(builddir)
    dirlist = [f for f in dirlist if f.startswith("build")]
    last_build_dir = builddir + "/" + max(dirlist)

    _, bench_name = bench.split(".")
    valid_makeout_files = [
        "make.out",
        f"make.{bench_name}_r.out"
    ]

    makeout_list = listdir(last_build_dir)
    for makeout in makeout_list:
        if makeout in valid_makeout_files:
            print_from_make_out(last_build_dir + "/" + makeout)

args = sys.argv[1:]
if len(args) == 1:
    print_from_make_out(args[0])
else:
    SPEC_DIR = "spec2017/cpu2017/benchspec/CPU"
    BENCHMARKS = [
        "502.gcc",
        "505.mcf",
        "507.cactuBSSN",
        "525.x264",
        "526.blender",
        "538.imagick",
        "544.nab",
        "557.xz",
    ]
    for bench in BENCHMARKS:
        print_from_last_make_out(bench, f"{SPEC_DIR}/{bench}_r/build")
