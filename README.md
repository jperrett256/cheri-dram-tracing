# LLC Trace Generation

This is to produce memory traces containing only the outgoing requests from the LLC. This is achieved by sending trace data from QEMU directly through a cache simulator.

The following sections describe how to build and run this system of tools. Some sections have footnotes\*, which provide additional details.

\* Like this one!

## Building

The following dependencies are required for cheribuild, qemu and cheribsd:
```
apt install autoconf automake libtool pkg-config clang bison cmake mercurial ninja-build samba flex texinfo time libglib2.0-dev libpixman-1-dev libarchive-dev libarchive-tools libbz2-dev libattr1-dev libcap-ng-dev libexpat1-dev libgmp-dev libexpat-dev mercurial libboost-all-dev
```
Note that the last few are not listed in the cheribuild README, but were found to be necessary to build this project.

Also, while cheribuild does not claim to support Ubuntu 22.04, it appears to work fine on it.

Building dynamorio requires `apt install libipt-dev zlib1g-dev liblz4-dev` at a minimum. If it fails to build, see [this page](https://dynamorio.org/page_building.html) for more information about dependencies.

See the sections below about version issues with dependencies installed with apt, and how to resolve them.

A build script has been prepared to make the process easier. While this build script should just work, provided all dependencies are provided (and are the appropriate versions - see below), I recommend **starting this process long before you need to use these tools**. Both cheribuild and g++ have flags for producing verbose output, which may be helpful if they complain.

### Configuration

Note that many of the dependencies installed by cheribuild have a configuration stage, and re-building does not necessarily reconfigure them. This means that attempting to build them after an initial failed attempt may fail yet again, even if the original problem was fixed.

This can be resolved by passing the `--reconfigure` flag to cheribuild\*, or deleting the build _and source_ directories for the dependency that cheribuild was trying to install when it failed.

\* I have only ever used this while making modifications to qemu, but it _looks_ like it should work for anything cheribuild installs.

### Version Issues - Ubuntu 18.04

The version of `liblz4-dev` found on Ubuntu 18.04 is too old for dynamorio and cheri-trace-converter. A more up-to-date release can be downloaded from the [lz4 GitHub page](https://github.com/lz4/lz4/releases) or the [Ubuntu packages archive](https://packages.ubuntu.com/focal/liblz4-dev). A local installation may be performed with:
```
make
PREFIX=$HOME/.local make install
```
Make sure that your `CPATH` and `LD_LIBRARY_PATH` environment variables are updated to include your local `lib/` and `include/` directories (e.g. by updating your `~/.bashrc` appropriately, though be sure to take note of the guidance below on setting these environment variables). You may also need to set `CMAKE_LIBRARY_PATH` when building dynamorio.

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

### Trailing/Leading Colons in Environment Variables

**Be careful not to have trailing or leading colons in your environment variables** (particularly `CPATH`), as this can be interpreted in some cases as having the current directory included in the list. This will interfere when building cheribuild (at the very least).
So instead of having, for example:
```bash
export CPATH=~/.local/include:$CPATH # NOTE do not do this
```
Consider instead using:
```bash
export CPATH=~/.local/include${CPATH:+:$CPATH}
```
This will only append `:$CPATH` to `~/.local/include` if `CPATH` is set and non-empty.

## Running

### Data Flow Overview

Producing a filtered trace involves the following stages:
1. qemu, emulating cheribsd, which will produce a raw trace of memory accesses
2. traceconv, which will compress the trace\*
3. `tee`, which splits the compressed trace into two streams, which are processed simultaneously
4. The first stream from `tee` is passed to a second instance of traceconv, which produces an "initial state file"
5. The second stream from `tee` is passed to a third instance of traceconv, which converts the trace into the trace format drcachesim expects
6. The generated drcachesim-format trace is passed to dynamorio as an "offline trace" for the drcachesim component to use, which will output all outgoing requests from the LLC to the "miss file" specified in the drcachesim configuration

\* While this compression step does not affect correctness, it has been found to substantially improve the performance of this entire tracing process.

### Components
The following components are used.

#### CHERI-QEMU

CHERI-QEMU is used to boot cheribsd on an emulated CHERI-extended RISC-V machine. (In principle it supports other architectures but I haven't needed to use them.) This has a tracing framework developed by Alfredo Mazzinghi, which supports multiple "tracing backends". I developed a [backend](https://github.com/jperrett256/qemu/tree/tag-tracing-backend) for just outputting memory accesses, containing the physical address, virtual address, and the type of memory access, and tag bit (if known).\*

These types of memory access are: non-capability load, non-capability store, capability load, capability store. The important thing is that tag bits are only known for capability loads (the tag of the capability being read), capability stores (the tag of the capability that is currently being written), and non-capability stores (tag is always cleared, since these clear the tag bits corresponding to any overlapping capability-aligned addresses).

Note that qemu emulates a system with 2 GiB of memory by default.

To boot cheribsd in qemu, use the following:
```bash
./cheribuild/cheribuild.py run-riscv64-purecap --source-root cheri --run-riscv64-purecap/ephemeral
```
The `--source-root` specifies the directory where all your build and source files were placed by cheribuild during the build process. The `--run-riscv64-purecap/ephemeral` option means that any changes you make to the emulated filesystem will not be seen on the next boot\*\*. Options can also be passed directly to qemu using `--run-riscv64-purecap/extra-options` (see run script for examples).

After running the command, it should immediately boot cheribsd. Enter "toor" for your username, no password should be required. Use `ctrl+a` followed by `x` to exit (`ctrl+c` will not work). ([Source](https://www.cl.cam.ac.uk/research/security/ctsrd/cheri/cheri-qemu.html))

\* The backend I created is called the "drcachesim" backend, despite not actually producing traces in the drcachesim format directly. The conversion between tehe formats is handled by traceconv (see **traceconv** section below).

\*\* This is not required, feel free to remove this option if you wish to make changes to the disk image.

#### drcachesim

An [extended version](https://github.com/jperrett256/dynamorio/tree/drcachesim-cheri) of the [drcachesim](https://dynamorio.org/page_drcachesim.html) component of DynamoRIO is used to simulate the generated memory traces through a cache hierarchy. All misses and write backs from the LLC (i.e. outgoing requests to DRAM) are written to a "miss file".

The specific extensions were:
- Bug fixes (in particular, fixing their FIFO and LRU cache replacement policy implementations to handle invalidations correctly)
- Explicit handling of write backs, and the inclusion of write backs in miss files
- Tag information in miss files (each entry contains the tag bits corresponding to the memory address range read/written back to DRAM; note they are likely written to another memory location, as determined/handled by the tag controller)
- Support for LZ4 trace files (LZ4 has a lower decompression ratio than GZIP, but is much faster)

When a LLC trace entry is emitted, not all tag bits will necessarily be known. Since a cache line corresponds to multiple capabilities and therefore multiple tag bits, not all of the capabilities in a cache line will necessarily have been read from or written to. (Or, in the case of non-capability loads, a capability may have been read from, but the tag remains unchanged and unknown, which means the situation is the same.) For example, on the first read of a cache line-sized unit from memory, none of the tag bits will be known\*. To handle this, a bitmask is also included along with the tag data bits, indicating which tag bits are known. For more information on the output trace format, see the **Output Trace Format** section below.

The method chosen for ensuring that the correct tag bits are written back **relies on the assumption that the caches are inclusive**. The tag data received from qemu reflects of the state of tags in memory _from the perspective of the CPU_, which may be more up-to-date than the tags in actual DRAM (due to CPU caching). The tag state as seen in actual DRAM depends on what is actually written back from the CPU caches. The way (my extended version of) drcachesim ensures that the tags written back from the caches are correct relies on the fact that: for inclusive caches, when a cache line is written back from the LLC, it is the most up-to-date version of that cache line. (This means the drcachesim implementation can simply create a table of tag data as the data from qemu comes in, and read from it when handling write-backs from the LLC to produce the output trace entry.) For non-inclusive caches, it is possible for write-backs to write back stale data (with there being more up-to-date version in one of the child caches), violating this assumption.

\* If the first read happens to be a capability load, then one of the tags bits is known. However, as handling this specific case introduces some complexity for no significant benefit (especially with the initial state file, described below), this is not handled. Also, it is worth clarifying that if the initial read from memory is due to a capability/non-capability store, while we have the tag that _will_ be written, we do not have the tag value that was read from memory (the tag that _was_ there).

#### traceconv

traceconv is a versatile tool, that I created, for the purpose of manipulating trace data. Most of traceconv works directly with the format that the drcachesim backend of qemu produces.

The tool is really a collection of smaller programs rolled into one. It is used like this:
```bash
./build/traceconv <command> [<arguments>]
```
Where the `arguments` depend on the `command` being run.

The most relevant commands for this overall system are:
- `convert`: Takes an uncompressed/GZIP/LZ4 input trace and produces an identical uncompressed/GZIP/LZ4 output trace. Input and output formats are deduced from file name extensions. This is used to compress the raw trace from qemu with LZ4, which improves performance.
- `get-initial-state`: This takes in trace data from qemu and produces an "initial state file", which records the initial access type (and corresponding tag data, if available) for every capability-aligned address in memory\*. The purpose is to help with making educated guesses about the initial tag values in memory, at the start of tracing. While better than nothing, as it allows for making educated guesses after the fact, it is not an entirely ideal solution (see **TODOs** section below).
- `convert-drcachesim-paddr`: Takes an uncompressed/GZIP/LZ4 input trace and outputs a trace compatible with drcachesim. drcachesim expects virtual addresses (and will simulate with them directly), but it is possible to simulate with physical addresses if they are provided in the place of virtual ones\*\*. That is exactly what this command does.

\* Note that the original tag is only known for capability loads. For capability stores and non-capability stores, we record the tag _written_, though it may not match what was there before. For non-capability loads, we can't say anything about the tag value at all, as it doesn't modify it. In the case where an address has only had non-capability load accesses, but is later followed by a capability load, we instead record the capability load (with associated tag) as the "initial" access to that address, since it has the true tag information. In general, it is probably reasonable to expect that non-capability loads and stores are associated with untagged capabilities.

\*\* The way you are _supposed_ to pass physical addresses into drcachesim is to pass a `use_physical` option in the drcachesim configuration file, and add virtual-to-physical mapping entries in the output trace (so both virtual and physical addresses are available). This works, and traceconv can even produce traces of this format using the `convert-drcachesim-vaddr` command, but simulating with the `use_physical` option in drcachesim is substantially slower, for no difference in final trace output. The primary reason that drcachesim was designed this way appears to be so that it can report the (virtual) instruction addresses responsible for cache misses, even when simulating with physical addresses. As this is not needed for trace generation, it is safe to bypass this and simply provide physical addresses, where drcachesim expects virtual ones.

### Running SPEC2006

Once built, the SPEC2006 binaries can be found within cheribsd at `/opt/riscv64-purecap/spec2006/`. A helper script `run.py` is provided to make it easier to run benchmarks. The benchmark variants are, in order of ascending intensity: test, train, and ref.

The build process described above runs `generate_spec_scripts.py`, which generates individual `.sh` script files that can be used within cheribsd to run each benchmark. Using these shell scripts make tracing more convenient, especially since some SPEC2006 benchmarks require running the benchmark program multiple times.

The specific commands needed for each benchmark can be seen in `spec_commands.py`. This is used by `generate_spec_scripts.py` to generate the SPEC2006 `.sh` files, and is used by `run.py` to check that the benchmark you're trying to run exists.

Note that the benchmarks gcc, perlbench, and mcf fail with `In-address security exception (core dumped)`. There may be a patch somewhere to make one of them (mcf IIRC) work with CHERI. They are not currently included in `spec_commands.py`.

### Tracing Options

NOTE: Many of the details described here are handled for you by the run script. However, knowing these details and what the relevant options are will help you decide what command line options to pass to the run script.

The tool used within cheribsd to perform tracing is `qtrace`. Using `qtrace [-u] exec -- <command>` will enable tracing, execute the command, and disable tracing.

The optional `-u` option filters the trace such that it only contains userspace instructions. Without it, "full" tracing is enabled, which will include both kernel and userspace instructions.

Note that since some portion of kernel activity involves servicing timing interrupts, the rate at which the emulated processor executes can affect the proportion of time spent in the kernel. By enabling tracing, and thereby further slowing the rate of execution, the amount of time spent in the kernel is increased to ridiculous levels. This doesn't matter when capturing userspace-only traces, as all kernel instructions are filtered out anyway, but it can substantially inflate trace size when capturing full traces. To avoid the kernel being "over-represented" in the trace, an additional `--icount shift=0,align=off` option is passed to qemu, which tells qemu to use a virtual timer that will increment by 1 ns\* every time an instruction is executed. This means "time" within qemu passes in accordance with the progress made by the emulated processor, and is unaffected by how long instructions actually take to execute, ensuring that memory accesses due to kernel instructions take up a more reasonable/plausible fraction of the trace produced by qemu. (This also explains why the timings provided in the trace output files may not match real-world time, as they are measured within qemu and instead reflect emulated time.)

There is also a "per-thread" tracing option, which will pause tracing whenever the traced thread is pre-empted. This avoids capturing memory accesses resulting from other threads. It can be set within qemu by executing:
```bash
sysctl hw.qemu_trace_perthread=1
```
In theory, this flag is inherited across forks and joins. (There is remarkably little documentation on this feature. [This](https://github.com/CTSRD-CHERI/cheriplot) is the only place I have seen it mentioned.)

To configure cache parameters, modify the drcachesim config file, `drcachesim_config.txt`. As mentioned before, the way that dynamorio handles tag values relies on the caches being inclusive, so the `use_physical` option should be left disabled. The LLC should have the `miss_file` option set (the value is the output trace filename).

\* Note that the `shift=N` component of the option configures how much time each instruction takes (in virtual cpu time). Specifically, each instruction is set to take $2^N$ nanoseconds. I chose `shift=0` as modern CPUs already greatly surpass an average execution speed of 1 instruction per nanosecond, and this seems to be the minimum value of `N` that can be provided. This means even in this case, we traces produced will likely have a higher proportion of memory accesses resulting from kernel activity than would be seen in real life. However, at least when running SPEC2006 benchmarks in this configuration, the vast majority of time is spent executing userspace instructions, which is what we expect.

### Using `run.py`

An example execution of the run script:
```bash
./run.py libquantum test -u -t -s 9999
````
Which will run the test variant of libquantum, with userspace instruction-only tracing (`-u`), perthread tracing enabled (`-t`), and the qemu SSH forwarding port set to 9999.

Note that the `-s` (`--ssh-port`) option is only needed if running multiple instances of the run script simultaneously. (Each instance needs its own port in order for qemu not to complain.)

There is also an `-m` option for setting the amount of memory used by qemu to something other than 2 GiB. (I created this for the purpose of trying to get some of the problematic benchmarks to run again, without success. See the **TODOs** section below).

This run script will produce a directory to contain all data relating to the trace. This includes:
- An `info.txt` file, containing the command line parameters provided to the run script, as well as the specific commands that were run. On completion, it outputs the time taken as reported by qemu (which may not match real-world time, see the **Tracing Options** section), and finally prints `Done.`.
- Several `.log` files, containing the stderr/stdout for each for each component. These are worth checking, to ensure that the benchmark ran successfully and that tracing was performed without error.
- The trace file and initial state file, which are described more in the **Output Trace Format** section.

## Output Trace Format

The output trace, once uncompressed, consists of an array of `tag_cache_request_t` structs. The `type` field of each struct is set to one of the constants in the `tag_cache_request_type_t` enum.

The initial state file consists of an array of `initial_access_t` structs (each a single byte), one for every tag in memory. Given 128-bit/16-byte capabilities, and 2 GiB of memory, this means the file requires 128 MiB of storage space. The `type` field on each struct is set to one of the constants in the `custom_trace_type_t` enum. (See the **traceconv** section for a description of why we need this file.)

All of these types are defined in [`inc/trace.h` of cheri-trace-converter](https://github.com/jperrett256/cheri-trace-converter/blob/master/inc/trace.h).

## TODOs

There are some remaining issues with this system. As I have little or no time to continue working on this, and assume that a person reading this is likely to take over this project, it seems fair to introduce what I see as some of the current limitations.

- There are benchmarks with working test variants but failing ref variants. These benchmarks are: hmmer, astar, and h264ref.
	- They fail with the message: `In-address space security exception (core dumped)`
	- astar fails almost immediately, hmmer fails at about an 1hr52min in on taramax, h264ref fails (at what seems like) near the start of the second command (`../../../464.h264ref -d foreman_ref_encoder_main.cfg`)
	- Testing with 4 GiB of memory with qemu did not appear to fix the issue.\*
- Not knowing all the tags in the final trace is an issue, and the initial state file only partially solves this problem. In the ideal case, the initial tags for all of memory would be output directly from qemu when tracing starts. This information should be available somewhere in qemu (as it is needed for correct emulation), and having the information would also greatly simplify simulation of the data through caches.
	- It would be worth looking at `target/cheri-common/cheri_tagmem.c` in the qemu source directory, as it may be a possible place to pull this information out
	- It would also be worth looking at the recent commits for [qemu-tag-tracing branch of my fork of qemu here](https://github.com/jperrett256/qemu/commits/qemu-tag-tracing). This was my initial approach for getting tag data out of qemu, and it may give some idea as to how it could be done.

\* Now I think about it, even if the benchmark did run successfully, cheri-trace-converter may not have been written to handle memory sizes other than the default of 2 GiB, so the trace file and initial state file could be incorrect. That said, this should not have been the reason the benchmark itself failed.
