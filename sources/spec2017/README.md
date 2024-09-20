## Setup
First you need the file `cpu2017.tar.xz`. It should contain files like `install.sh`, `tools/`, `bin/`, `benchspec/`.

I have seen several versions of this file, one with an `install_archives/` folder, and one without.
If your file has the `install_archives` folder, there will be a new `cpi2017.tar.xz` inside of it, which is the one I have been using.

**Dependencies:**
 - libcrypt.so (`pacman -S libxcrypt-compat`)

To create a folder `cpu2017/` with a SPEC installation, use 
```sh
just install-cpu2017 <path/to/cpu2017.tar.xz>
```

## Running
Before running, you should set your CPU scheduler to a reasonable clock speed to avoid unpredictable boosting.
The config name is one of the files in `config`, e.g. `jlc-andersen-config`
``` sh
just run-cpu2017 [config-name]
```

