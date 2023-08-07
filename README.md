# LLC Trace Generation

This is to produce memory traces containing only the outgoing requests from the LLC. This is achieved by sending trace data from QEMU directly through a cache simulator.

## Building

The following dependencies are required for cheribuild, qemu and cheribsd:
```
apt install autoconf automake libtool pkg-config clang bison cmake mercurial ninja-build samba flex texinfo time libglib2.0-dev libpixman-1-dev libarchive-dev libarchive-tools libbz2-dev libattr1-dev libcap-ng-dev libexpat1-dev libgmp-dev libexpat-dev mercurial libboost-all-dev
```
Note that the last few are not listed in the cheribuild README, but were found to be necessary to build this project.

Also, while cheribuild does not claim to support Ubuntu 22.04, it appears to work fine on it.

Building dynamorio requires `apt install libipt-dev zlib1g-dev liblz4-dev` at a minimum. If it fails to build, see [this page](https://dynamorio.org/page_building.html) for more information about dependencies.

See the sections below about version issues with dependencies installed with apt, and how to resolve them.

A build script has been prepared to make the process easier. It should boot into cheribsd during the build process, use `ctrl+A` followed by `x` to exit.
While this build script should just work, provided all dependencies are provided (and are the appropriate versions - see below), I recommend **starting this process long before you need to use these tools**. Both cheribuild and g++ have flags for producing verbose output, which may be helpful if they complain.

### Version Issues - Ubuntu 18.04

The version of `liblz4-dev` found on Ubuntu 18.04 is too old for dynamorio and cheri-trace-converter. A more up-to-date release can be downloaded from the [lz4 GitHub page](https://github.com/lz4/lz4/releases) or the [Ubuntu packages archive](https://packages.ubuntu.com/focal/liblz4-dev). A local installation may be performed with:
```
make
PREFIX=$HOME/.local make install
```
Make sure that your `CPATH` and `LD_LIBRARY_PATH` environment variables are updated to include your local `lib/` and `include/` directories (e.g. by updating your `~/.bashrc` appropriately). You may also need to set `CMAKE_LIBRARY_PATH` when building dynamorio.

Older versions of gcc/g++ (such as version 7.5.0, which is what is available via `apt` for Ubuntu 18.04) appear not to perform partial linking correctly, which is needed for building cheri-trace-converter. (It results in linker errors, due to these older versions implicitly adding `-l<library name>` flags to the end of your command, even when partial linking is enabled. This can be seen by running gcc/g++ in verbose mode, with the `-v` flag.) A newer version (e.g. 11.4.0, which is what you find on Ubuntu 20.04) can be installed locally, using the instructions [here](https://gcc.gnu.org/wiki/InstallingGCC) and the releases [here](https://gcc.gnu.org/releases.html).

Note that a more up-to-date cmake installation may also be needed, depending on your Ubuntu version. This can also be installed locally. The [CMake download page](https://cmake.org/download/) provides install scripts that support a `--prefix` option, which makes it easy to install locally.

### Version Issues - Ubuntu 20.04

cheribuild has issues with the version 3.4.0 of the `libarchive` package (which includes `bsdtar`), though lower and higher versions work fine. Unfortunately, 3.4.0 is currently the default version on Ubuntu 20.04 (Focal Fossa), and therefore a different version (e.g. 3.5.0) needs to be locally installed:
```
wget https://www.libarchive.org/downloads/libarchive-3.5.0.tar.gz
tar -xzf libarchive-3.5.0.tar.gz
cd libarchive-3.5.0
./configure --prefix=$HOME/.local
make
make install
```
Make sure that your `PATH` is updated to include the `bin/` directory of your local install location (e.g. by updating your `~/.bashrc` appropriately).
