#!/usr/bin/env python3

import sys
import os
import stat
import re
import argparse
import pexpect
import spec_commands as SPEC
from datetime import datetime

def start_process(command, info_file=None, **kwargs):
    if info_file:
        info_file.write(f"RUNNING COMMAND:\n{command}\n\n")

    child = pexpect.spawn("/bin/bash", ['-c', command], **kwargs)
    return child

def expect_process_end(child):
    child.expect(pexpect.EOF, timeout=None)
    if child.wait() != 0:
        raise RuntimeError(f"Failed to execute command: '{command}'")

def expect_qemu_command_end(qemu_process):
    qemu_process.expect(re.compile(rb"toor@cheribsd-riscv64-purecap:.* #"), timeout=None)

def run_benchmark(qemu_process, name: str, variant: str, userspace: bool):
    # NOTE all necessary commands for each benchmark are in scripts placed within cheribsd by the build process
    qtrace_prefix = "time qtrace{} exec -- ".format(" -u" if userspace else "")
    benchmark_command = f"/opt/spec2006_scripts/{name}.{variant}.sh"

    qemu_process.sendline(qtrace_prefix + benchmark_command)

    qemu_process.expect(re.compile(rb"[0-9]+\.[0-9]+ real\s+[0-9]+\.[0-9]+ user\s+[0-9]+\.[0-9]+ sys"), timeout=None)
    time_match = qemu_process.match

    expect_qemu_command_end(qemu_process)

    return time_match

def log_and_print(info_file, message):
    info_file.write(message + '\n')
    print(message)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A tool for the automated running of SPEC2006 benchmarks in cheribsd.")

    parser.add_argument("benchmark_name", type=str, metavar="benchmark",
        help="Benchmark name")
    parser.add_argument("benchmark_variant", choices=["test", "train", "ref"],
        help="Benchmark variant (either test, train, or ref)")

    parser.add_argument("-p", "--ssh-port", type=str, metavar="PORT", dest="ssh_port",
        help="SSH port to use with qemu/cheribsd")
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose",
        help="Forward qemu output to stdout (already present in log files)")
    parser.add_argument("--perthread", action="store_true", dest="perthread_enabled",
        help="Enable perthread tracing")
    parser.add_argument("-u", "--userspace", action="store_true", dest="userspace_enabled",
        help="Enable userspace tracing")
    args = parser.parse_args()

    if args.benchmark_name not in SPEC.all_benchmarks:
        raise RuntimeError(f"Benchmark name not found in: {SPEC.all_benchmarks.keys()}")

    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

    trace_output_dir = os.path.abspath(datetime.now().strftime("trace_%Y-%m-%d_%H-%M-%S_%f"))
    print(f"Writing to: {trace_output_dir}")
    os.mkdir(trace_output_dir) # NOTE will throw exception if directory already exists

    with open(os.path.join(trace_output_dir, "info.txt"), "w") as info_file:
        info_file.write(f"Benchmark Name: {args.benchmark_name}\n")
        info_file.write(f"Benchmark Variant: {args.benchmark_variant}\n")
        info_file.write(f"Perthread Tracing Enabled: {args.perthread_enabled}\n")
        info_file.write(f"Userspace Tracing Enabled: {args.userspace_enabled}\n")
        info_file.write("\n")
        info_file.flush()

        # create fifos for piping trace data between components
        fifo_dir = os.path.join(trace_output_dir, 'fifos')
        os.mkdir(fifo_dir) # NOTE will throw exception if directory already exists

        fifo_raw = os.path.join(fifo_dir, 'fifo_trace_raw')
        fifo_compressed = os.path.join(fifo_dir, 'fifo_trace_compressed.lz4')
        fifo_split_a = os.path.join(fifo_dir, 'fifo_trace_split_a.lz4')
        fifo_split_b = os.path.join(fifo_dir, 'fifo_trace_split_b.lz4')
        fifo_drcachesim = os.path.join(fifo_dir, 'fifo_trace_drcachesim.lz4')

        os.mkfifo(fifo_raw)
        os.mkfifo(fifo_compressed)
        os.mkfifo(fifo_split_a)
        os.mkfifo(fifo_split_b)
        os.mkfifo(fifo_drcachesim)

        info_file.write("All fifos created.\n\n")
        info_file.flush()

        # TODO may need quoting to make these commands work if there are spaces in the absolute path

        # start running all components needed for filtered tracing
        traceconv_compress_process = start_process(
            f"{os.path.join(script_dir, 'cheri-trace-converter/build/traceconv')} convert "
            f"{fifo_raw} {fifo_compressed} "
            f"|& tee {os.path.join(trace_output_dir, 'traceconv_compress.log')}",
            info_file=info_file, cwd=trace_output_dir)

        split_process = start_process(
            f"<{fifo_compressed} tee {fifo_split_a} > {fifo_split_b} "
            f"|& tee {os.path.join(trace_output_dir, 'split.log')}",
            info_file=info_file, cwd=trace_output_dir)

        traceconv_initial_state_process = start_process(
            f"{os.path.join(script_dir, 'cheri-trace-converter/build/traceconv')} get-initial-state "
            f"{fifo_split_b} {os.path.join(trace_output_dir, 'trace_initial_state.bin')} "
            f"|& tee {os.path.join(trace_output_dir, 'traceconv_initial_state.log')}",
            info_file=info_file, cwd=trace_output_dir)

        traceconv_drcachesim_process = start_process(
            f"{os.path.join(script_dir, 'cheri-trace-converter/build/traceconv')} convert-drcachesim-paddr "
            f"{fifo_split_a} {fifo_drcachesim} "
            f"|& tee {os.path.join(trace_output_dir, 'traceconv_drcachesim.log')}",
            info_file=info_file, cwd=trace_output_dir)

        drcachesim_process = start_process(
            f"{os.path.join(script_dir, 'dynamorio_build/bin64/drrun')} -t drcachesim "
            f"-config_file {os.path.join(script_dir, 'drcachesim_config.txt')} "
            f"-infile {fifo_drcachesim} "
            f"|& tee {os.path.join(trace_output_dir, 'drcachesim.log')}",
            info_file=info_file, cwd=trace_output_dir)

        qemu_process = start_process(
            f"{os.path.join(script_dir, 'cheribuild/cheribuild.py')} "
            f"--source-root {os.path.join(script_dir, 'cheri')} "
            "run-riscv64-purecap --run-riscv64-purecap/ephemeral "
            "--run-riscv64-purecap/extra-options=\""
            f"{'--icount shift=0,align=off ' if not args.userspace_enabled else ''}"
            "--cheri-trace-backend drcachesim "
            f"--cheri-trace-drcachesim-tracefile {fifo_raw} "
            f"--cheri-trace-drcachesim-dbgfile {os.path.join(trace_output_dir, 'trace_qemu_dbg.txt')}\" "
            f"{'--run-riscv64-purecap/ssh-forwarding-port={} '.format(args.ssh_port) if args.ssh_port else ''}"
            f"|& tee {os.path.join(trace_output_dir, 'qemu.log')}",
            info_file=info_file, cwd=trace_output_dir)

        info_file.flush()

        if args.verbose:
            qemu_process.logfile = sys.stdout.buffer
            drcachesim_process.logfile = sys.stdout.buffer

        qemu_process.expect("login:", timeout=None)
        qemu_process.sendline("toor")

        expect_qemu_command_end(qemu_process)

        if args.perthread_enabled:
            qemu_process.sendline("sysctl hw.qemu_trace_perthread=1")
            expect_qemu_command_end(qemu_process)

        assert(traceconv_compress_process.isalive())
        assert(traceconv_drcachesim_process.isalive())
        assert(drcachesim_process.isalive())
        assert(traceconv_initial_state_process.isalive())
        assert(split_process.isalive())

        time_match = run_benchmark(qemu_process,
            args.benchmark_name, args.benchmark_variant, args.userspace_enabled)

        time_str = time_match.group(0).decode('utf-8')
        info_file.write(f"Time taken: {time_str}\n\n")
        if not args.verbose:
            print(f"Time taken: {time_str}")
        info_file.flush()

        qemu_process.sendcontrol('a')
        qemu_process.send('x')
        expect_process_end(qemu_process)

        for fifo_file in os.listdir(fifo_dir):
            fifo_file_path = os.path.join(fifo_dir, fifo_file)
            is_fifo = stat.S_ISFIFO(os.stat(fifo_file_path).st_mode)
            if is_fifo:
                os.remove(fifo_file_path)
        try:
            os.rmdir(fifo_dir)
        except OSError as e:
            log_and_print(info_file, f"WARNING: failed to remove fifo directory at '{fifo_dir}'")
            log_and_print(info_file, str(e))
            info_file.write('\n')
            info_file.flush()

        expect_process_end(traceconv_compress_process)
        expect_process_end(split_process)
        expect_process_end(traceconv_initial_state_process)
        expect_process_end(traceconv_drcachesim_process)
        expect_process_end(drcachesim_process)

        info_file.write("Done.\n\n")
