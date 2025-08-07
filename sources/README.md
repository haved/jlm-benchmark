# Benchmarking sources
This folder contains the sources used for benchmarking.

### Open source benchmarks
The open source benchmarks have been downloaded from
 - Emacs 29.4: `https://ftpmirror.gnu.org/emacs/emacs-29.4.tar.gz`
 - Ghostscript 10.04.0: `https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10040/ghostscript-10.04.0.tar.gz`
 - gdb 15.2: `https://ftp.gnu.org/gnu/gdb/gdb-15.2.tar.gz`
 - sendmail 8.18.1: `https://ftp.sendmail.org/sendmail.8.18.1.tar.gz`

They can all be found in the `programs/` folder

### SPEC 2017 benchmarks
While SPEC 2017 is propriatary, they include a folder called `redistributable_sources/`, containing both original and modified sources.
In `programs/redist2017/`, the relevant subset of this folder is included, using the modified version when available.
We also include the `Docs/licences` folder, as it contains licencing information about all the programs and SPEC2017 itself.

If you have a copy of `cpu2017.tar.xz`, place it in the folder 

### Extracting benchmarks
To extract all free
``` sh

```

### Build commands
The file `sources.json` contains all the compiler invocations used to build the programs,
created by tracing complete builds of the target programs.
The SPEC2017 traces were created from the `make.out` log files, while the open source programs were traced using the `bear` utility.
