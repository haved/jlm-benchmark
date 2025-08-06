## Extracting
First you need the file `cpu2017.tar.xz`. It should contain files like `install.sh`, `tools/`, `bin/`, `benchspec/`.

I have seen several versions of this file, one with an `install_archives/` folder, and one without.
If your file has the `install_archives` folder, there will be a new `cpu2017.tar.xz` inside of it, which is the one I have been using.

**Dependencies:**
 - libcrypt.so (`pacman -S libxcrypt-compat`)
 - `clang` / `clang++` v. 18.1.8

To create a folder `cpu2017/` with a SPEC installation, use 
```sh
just install-cpu2017 <path/to/cpu2017.tar.xz>
```

## Running
We want to run SPEC once, such that it compiles all its files and logs the compile commands,
as well as compiling the C++ files we can not compile ourselves using jlm.

In order to make object files compatible, the default run command uses `llvm-config-18` to find C/C++ compiler.
Execute using:
``` sh
just run-cpu2017 
```

If you wish to abort it, Ctrl-C might not work. Try using
``` sh
just terminate-cpu2017
```

If you have started a run before and want to clean up before executing again, do
``` sh
just clean
```

