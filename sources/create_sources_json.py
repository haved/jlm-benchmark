#!/usr/bin/env python3
import argparse
import os
import shlex
import json
import sys
import subprocess
import re

# The script should be run from the sources folder
SCRIPT_ROOT = os.getcwd()

IGNORED_ARGUMENTS = [
    "-O0",
    "-O1",
    "-O2",
    "-O3",
    "-Os",
    "-Oz",
    "-Ofast",
    "-c",
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
    "-gfull"
]

REPLACED_ARGUMENTS = {
    "-fstrict-flex-arrays": "-fstrict-flex-arrays=3"
}

IGNORED_LINKER_ARGUMENTS = []

C_COMPILERS = ["clang", "clang18", "gcc", "jlc", "cc"]
LINKERS = ["clang", "clang18", "clang++", "clang++18", "gcc", "jlc", "cc"]

SPEC_PROGRAMS = ["502.gcc", "505.mcf", "507.cactuBSSN", "525.x264", "526.blender", "538.imagick", "557.xz", "544.nab"]
OTHER_PROGRAMS = ["emacs-29.4", "ghostscript-10.04.0", "gdb-15.2", "wine-9.21", "sendmail-8.18.1"]

# Files whose absolute path end in the following are excluded.
# This can be due to use of inline assembly, computed goto or special intrinsics
SKIPPED_FILES = [
    "wine-9.21/server/queue.c",
    "wine-9.21/server/mapping.c",
    "wine-9.21/server/winstation.c",
    "emacs/lib/memset_explicit.c",
    "emacs/src/bytecode.c",
    "gdb-15.2/libiberty/sha1.c",
    "gdb-15.2/libbacktrace/mmap.c",
    "gdb-15.2/libbacktrace/dwarf.c",
    "gdb-15.2/libbacktrace/elf.c",
    "ghostscript-10.04.0/leptonica/src/bytearray.c",
    "ghostscript-10.04.0/leptonica/src/boxbasic.c",
    "ghostscript-10.04.0/leptonica/src/ccbord.c",
    "ghostscript-10.04.0/leptonica/src/compare.c",
    "ghostscript-10.04.0/leptonica/src/dnabasic.c",
    "ghostscript-10.04.0/leptonica/src/gplot.c",
    "ghostscript-10.04.0/leptonica/src/fpix1.c",
    "ghostscript-10.04.0/leptonica/src/numabasic.c",
    "ghostscript-10.04.0/leptonica/src/pix1.c",
    "ghostscript-10.04.0/leptonica/src/pixabasic.c",
    "ghostscript-10.04.0/leptonica/src/ptabasic.c",
    "ghostscript-10.04.0/leptonica/src/regutils.c",
    "ghostscript-10.04.0/leptonica/src/sarray1.c",
    "ghostscript-10.04.0/leptonica/src/writefile.c"
]

def make_relative_to(path, base):
    """
    Makes a path relative to base. Is must be an absolute path, or relative to the SCRIPT_ROOT.
    Asserts that base is a directory.
    """
    if not path.startswith("/"):
        path = os.path.abspath(path)

    base = os.path.abspath(base)
    if not os.path.isdir(base):
        raise ValueError(f"{base} is not a directory")

    prefix = ""
    while True:
        if path.startswith(base + "/"):
            result = prefix + path[len(base)+1:]
            return result
        prefix += "../"
        base = os.path.dirname(base)

class CFile:
    """
    Represents the compilation of a single .c file, in a given working directory, with a set of arguments.
    The working dir is stored relative to the script root.
    The c file is stored relative to the working dir.
    Also includes the path of the output file, mostly for indexing purposes. Stored relative to SCRIPT_ROOT.
    """
    def __init__(self, working_dir, cfile, ofile, arguments):
        """
        :param working_dir: the working directory for the compile command, relative to SCRIPT_ROOT
        :param cfile: the compiled C file, relative to working_dir
        :param ofile: the output O file, relative to working_dir
        """
        self.working_dir = make_relative_to(working_dir, SCRIPT_ROOT)
        self.cfile = make_relative_to(os.path.join(working_dir, cfile), working_dir)
        self.ofile = make_relative_to(os.path.join(working_dir, ofile), SCRIPT_ROOT)
        self.arguments = [REPLACED_ARGUMENTS.get(arg, arg) for arg in arguments if arg not in IGNORED_ARGUMENTS]

        assert os.path.isfile(os.path.join(self.working_dir, self.cfile))

    def to_dict(self):
        return {
            "working_dir": self.working_dir,
            "cfile": self.cfile,
            "ofile": self.ofile,
            "arguments": self.arguments
            }

    def get_cfile_path(self):
        """ Gets the path of the cfile relative to SCRIPT_ROOT """
        return os.path.normpath(os.path.join(self.working_dir, self.cfile))

    def get_loc(self):
        """
        Counts the number of lines of code in the C file
        """
        run = subprocess.run(["cloc", self.get_cfile_path(), "--json"], capture_output=True)
        if run.returncode != 0:
            raise ValueError(f"Counting lines of code for {self.get_cfile_path()} failed")
        data = json.loads(run.stdout)

        if "C" in data:
            return data["C"]["code"]
        else:
            # Cloc may mistakenly count C as C++ when stored as .cc files
            assert "C++" in data
            return data["C++"]["code"]


class Program:
    """
    Represents a single program linked together from a set of object files.
    When the object file is the result of compiling a C file, the compilation command is included.
    All ofile paths, and the elffile path, are stored relative to SCRIPT_ROOT
    """
    def __init__(self, folder, cfiles, linker_workdir, ofiles, elffile, linker_arguments):
        """
        :param folder: the folder in which the program is, relative to SCRIPT_ROOT
        :param cfiles: a list of CFile objects representing compiling C files into object files
        :param linker_wordir: the working dir of the linking command
        :param ofiles: a list of linked of object file paths, all relative to linker_workdir
        :param elffile: the name of the elf output, relative to linker_workdir
        :param linker_arguments: extra arguments given to the linker
        """

        self.folder = folder
        self.cfiles = cfiles.copy()
        self.linker_workdir = linker_workdir
        self.ofiles = [make_relative_to(os.path.join(linker_workdir, ofile), SCRIPT_ROOT) for ofile in ofiles]
        self.elffile = make_relative_to(os.path.join(linker_workdir, elffile), SCRIPT_ROOT)
        self.linker_arguments = [arg for arg in linker_arguments if arg not in IGNORED_LINKER_ARGUMENTS]

        self.remove_skipped_cfiles()
        self.remove_duplicate_cfiles()

    def to_dict(self):
        return {
            "cfiles": [cfile.to_dict() for cfile in self.cfiles],
            "linker_workdir": self.linker_workdir,
            "ofiles": self.ofiles,
            "elffile": self.elffile,
            "linker_arguments": self.linker_arguments
            }

    def remove_duplicate_cfiles(self):
        seen = set()
        def false_if_seen(cfile):
            abspath = cfile.get_cfile_path()
            if abspath in seen:
                return False
            seen.add(abspath)
            return True
        self.cfiles = [cfile for cfile in self.cfiles if false_if_seen(cfile)]

    def remove_skipped_cfiles(self):
        def should_skip(cfile):
            abspath = cfile.get_cfile_path()
            return any(abspath.endswith(path) for path in SKIPPED_FILES)

        self.cfiles = [cfile for cfile in self.cfiles if not should_skip(cfile)]

    def get_loc(self):
        return sum(cfile.get_loc() for cfile in self.cfiles), len(self.cfiles)


# ================================================================================
#                Functions for extracting build steps from SPEC2017
# ================================================================================

def extract(flag, args):
    assert flag in args
    output_index = args.index(flag)
    value = args[output_index + 1]
    # Remove the flag and value part of args
    return value, args[:output_index] + args[output_index+2:]

def parse_cc_command(line, working_dir):
    args = shlex.split(line)
    if len(args) == 0:
        return None

    compiler_name = args[0].split("/")[-1]
    if compiler_name not in C_COMPILERS:
        return None

    args = args[1:] # Skip compiler name

    if "-c" not in args:
        return None

    ofile, args = extract("-o", args)

    flags = [arg for arg in args if arg.startswith("-")]
    positional = [arg for arg in args if not arg.startswith("-")]

    if len(positional) != 1:
        raise ValueError(f"Multiple positional args: {positional}")
    cfile = positional[0]

    # Skip C++ files
    if cfile.endswith(".cpp"):
        return None

    # Replace build/-path with src/ to avoid relying on the build folder existsing
    working_dir_src = re.sub(r'/build/build_base_[^/]*', '/src', working_dir)

    return CFile(working_dir_src, cfile, ofile, flags)

def parse_link_command(line, working_dir, cfiles):
    args = shlex.split(line)
    if len(args) == 0:
        return None

    linker_name = args[0].split("/")[-1]
    if linker_name not in LINKERS:
        return None

    args = args[1:] # Skip linker name

    # This might actually be a compile command of a C++ file. If so, abort!
    if "-c" in args:
        return None

    elffile, args = extract("-o", args)

    flags = [arg for arg in args if arg.startswith("-")]
    ofiles = [arg for arg in args if not arg.startswith("-")]

    return Program(folder=working_dir, cfiles=cfiles, linker_workdir=working_dir,
                   ofiles=ofiles, elffile=elffile, linker_arguments=flags)

def program_from_spec_make(make_out_file):
    make_out_file = os.path.abspath(make_out_file)
    working_dir = os.path.dirname(make_out_file)

    cfiles = []
    programs = []

    with open(make_out_file, 'r', encoding='utf-8') as make_out_fd:
        for line in make_out_fd:
            cfile = parse_cc_command(line, working_dir)
            if cfile is not None:
                cfiles.append(cfile)
                continue

            program = parse_link_command(line, working_dir, cfiles)
            if program is not None:
                programs.append(program)

    if len(programs) == 0:
        raise ValueError(f"The file {make_out_file} contained no linking command")
    if len(programs) > 1:
        raise ValueError(f"The file {make_out_file} contained multiple linking commands")
    return programs[0]

def program_from_spec(spec_program):
    build_dir = f"spec2017/cpu2017/benchspec/CPU/{spec_program}_r/build/"
    if not os.path.isdir(build_dir):
        raise ValueError(f"The spec benchmark {spec_program} has not been built before, see spec2017/README.md")

    dirlist = os.listdir(build_dir)
    dirlist = [f for f in dirlist if f.startswith("build")]
    if len(dirlist) == 0:
        raise ValueError(f"The spec benchmark {spec_program} has not been built before, see spec2017/README.md")

    latest_build_dir = os.path.join(build_dir, max(dirlist))

    for make_out_name in ["make.out", f"make.{spec_program.split('.')[1]}_r.out"]:
        make_out_file = os.path.join(latest_build_dir, make_out_name)
        if os.path.exists(make_out_file):
            break
    else:
        raise ValueError(f"No make.out or similar file found in {latest_build_dir}")

    return program_from_spec_make(make_out_file)

# =====================================================================
#      Creates a program using compile_commands.json
# =====================================================================
def program_from_folder(folder):

    compile_commands_file = os.path.join(folder, "compile_commands.json")
    if not os.path.isfile(compile_commands_file):
        print(f"The folder {folder} is missing compile_commands.json, skipping")
        return None

    with open(compile_commands_file, 'r') as compile_commands_fd:
        commands = json.load(compile_commands_fd)

    cfiles = []
    for command in commands:
        compiler, *arguments = command["arguments"]
        working_dir = command["directory"]
        cfile = command["file"]

        # Skip files compiled with e.g. g++
        if not any(compiler.endswith(c) for c in C_COMPILERS):
            continue

        # Also skip files with the C++ type
        if cfile.endswith(".cpp"):
            continue

        # Skip -x c++
        if "-x" in arguments:
            lang, argument = extract("-x", arguments)
            if lang not in ["c", "C"]:
                continue

        cfile_basename = os.path.basename(cfile)
        if "output" in command:
            ofile = command["output"]
        else:
            assert cfile.endswith(".c")
            ofile = cfile[:-1] + "o"

        # If there is a -o, remove it and the output file
        if "-o" in arguments:
            _, arguments = extract("-o", arguments)

        # Remove the input file as well
        arguments = [arg for arg in arguments if not arg.endswith(cfile_basename)]

        cfiles.append(CFile(working_dir=working_dir, cfile=cfile, ofile=ofile, arguments=arguments))

    program = Program(folder=folder, cfiles=cfiles, linker_workdir=folder,
                      ofiles=[], elffile="", linker_arguments=[])

    return program


def main():
    parser = argparse.ArgumentParser(description='Turn programs into a sources.json file')
    parser.add_argument('--list', dest='list', action='store_true',
                        help="Print a list of possible programs and exit")
    parser.add_argument('--filter', dest='filter', action='store', default=None,
                        help="Optional regex filter that program names must include")
    parser.add_argument('--output', dest='output', action='store', default='sources.json',
                        help="The name of the destination json file [sources.json]")
    parser.add_argument('--cloc', dest='cloc', action='store_true',
                        help="Print the number of lines of C code in each program")
    args = parser.parse_args()

    if args.list:
        print("Known programs in SPEC:")
        for p in SPEC_PROGRAMS:
            print(f" - {p}")
        print("Known other programs:")
        for p in OTHER_PROGRAMS:
            print(f" - {p}")
        exit(0)

    def should_skip(program):
        return args.filter is not None and not re.search(args.filter, program)

    programs = {}

    for program in SPEC_PROGRAMS:
        if should_skip(program):
            continue
        print(f"Trying to index program {program}")
        program_object = program_from_spec(program)
        if program_object is not None:
            programs[program] = program_object

    for program in OTHER_PROGRAMS:
        if should_skip(program):
            continue
        print(f"Trying to index program {program}")
        program_object = program_from_folder(program)
        if program_object is not None:
            programs[program] = program_object

    if args.cloc:
        print(f"{'Program':<20} | {'#Files':>20} | {'KLOC':>20}")
        for name, program in programs.items():
            loc, filecount = program.get_loc()
            print(f"{name:<20} | {filecount:>20} | {loc/1000:>20}")

    # We can not place the sources.json file anywhere else, as that messes with relative paths
    assert "/" not in args.output
    with open(args.output, 'w', encoding='utf-8') as output_file:
        json.dump({k: v.to_dict() for k, v in programs.items()}, output_file, indent=2)

if __name__ == "__main__":
    main()
