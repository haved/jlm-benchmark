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
    "-g3"
]

REPLACED_ARGUMENTS = {
    "-fstrict-flex-arrays": "-fstrict-flex-arrays=3"
}

IGNORED_LINKER_ARGUMENTS = []

C_COMPILERS = ["clang", "clang18", "gcc", "jlc"]
LINKERS = ["clang", "clang18", "clang++", "clang++18", "gcc", "jlc"]

def make_relative_to(path, base):
    """
    Makes a path relative to base. Is must be an absolute path, or relative to the SCRIPT_ROOT.
    Asserts that path exists.
    Asserts that base is a directory, and a superfolder of path.
    """
    if not path.startswith("/"):
        path = os.path.abspath(path)
    assert os.path.exists(path)

    base = os.path.abspath(base)
    if not os.path.isdir(base):
        raise ValueError(f"{base} is not a directory")

    base = base + "/"
    if not path.startswith(base):
        raise ValueError(f"Can not make path {path} relative to {base}")

    return path[len(base):]

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

    def get_loc(self):
        """
        Counts the number of lines of C and header files.
        Returns the pair (LOC, num C files)
        """
        run = subprocess.run(["cloc", self.folder, '--include-lang=C,C/C++ Header', "--json"], capture_output=True)
        if run.returncode != 0:
            raise ValueError(f"Counting lines of code for {self.folder} failed")
        data = json.loads(run.stdout)

        nCFiles = data["C"]["nFiles"]
        if nCFiles != len(self.cfiles):
            print(f"Warning: The folder {self.folder} contains {nCFiles}, but only {len(self.cfiles)} are included")

        return data["SUM"]["code"], nCFiles


# ================================================================================
#                Functions for extracting build steps from SPEC2017
# ================================================================================

def extract_o(args):
    assert "-o" in args
    output_index = args.index("-o")
    ofile = args[output_index + 1]
    # Remove the ofile part of args
    return ofile, args[:output_index] + args[output_index+2:]

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

    ofile, args = extract_o(args)

    flags = [arg for arg in args if arg.startswith("-")]
    positional = [arg for arg in args if not arg.startswith("-")]

    if len(positional) != 1:
        raise ValueError(f"Multiple positional args: {positional}")
    cfile = positional[0]

    # Skip C++ files
    if cfile.endswith(".cpp"):
        return None

    return CFile(working_dir, cfile, ofile, flags)

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

    elffile, args = extract_o(args)

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
def program_from_folder(folder, make_clean):
    if make_clean:
        run = subprocess.run(["make", "clean"], cwd=folder)
        if run.returncode != 0:
            raise ValueError(f"Running 'make clean' in {folder} failed with status code {run.returncode}")

    compile_commands_file = os.path.join(folder, "compile_commands.json")
    if make_clean or not os.path.isfile(compile_commands_file):
        print(f"The folder {folder} is missing compile_commands.json, running configure and make")

        run = subprocess.run(["./configure"], cwd=folder)
        if run.returncode != 0:
            raise ValueError(f"Running configure in {folder} exited with status code {run.returncode}")

        run = subprocess.run(["bear", "--", "make"], cwd=folder)
        if run.returncode != 0:
            raise ValueError(f"Running make in {folder} exited with status code {run.returncode}")

    with open(compile_commands_file, 'r') as compile_commands_fd:
        commands = json.load(compile_commands_fd)

    cfiles = []
    for command in commands:
        compiler, *arguments = command["arguments"]
        working_dir = command["directory"]
        cfile = command["file"]

        # Skip C++
        if cfile.endswith(".cpp"):
            continue

        cfile_basename = os.path.basename(cfile)
        if "output" in command:
            ofile = command["output"]
        else:
            assert cfile.endswith(".c")
            ofile = cfile[:-1] + "o"

        # If there is a -o, remove it and the output file
        if "-o" in arguments:
            _, arguments = extract_o(arguments)

        # Remove the input file as well
        arguments = [arg for arg in arguments if not arg.endswith(cfile_basename)]

        cfiles.append(CFile(working_dir=working_dir, cfile=cfile, ofile=ofile, arguments=arguments))

    program = Program(folder=folder, cfiles=cfiles, linker_workdir=folder,
                      ofiles=[], elffile="", linker_arguments=[])
    program.remove_duplicate_cfiles()
    return program

SPEC_PROGRAMS = ["502.gcc", "505.mcf", "507.cactuBSSN", "525.x264", "526.blender", "538.imagick", "557.xz", "544.nab"]
OTHER_PROGRAMS = ["emacs", "ghostscript-10.04.0"]

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
    parser.add_argument('--make_clean', dest='make_clean', action='store_true',
                        help="For programs built from this script, runs 'make clean' before making")
    args = parser.parse_args()

    if args.list:
        print("Available programs in SPEC (must be built separately, see spec2017/README.md):")
        for p in SPEC_PROGRAMS:
            print(f" - {p}")
        print("Available other programs (will be built from this script using 'bear'):")
        for p in OTHER_PROGRAMS:
            print(f" - {p}")
        exit(0)

    def should_skip(program):
        return args.filter is not None and not re.search(args.filter, program)

    programs = {}

    for program in SPEC_PROGRAMS:
        if should_skip(program):
            continue
        print(f"Doing program {program}")
        programs[program] = program_from_spec(program)

    for program in OTHER_PROGRAMS:
        if should_skip(program):
            continue
        print(f"Doing program {program}")
        programs[program] = program_from_folder(program, make_clean=args.make_clean)

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
