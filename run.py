import sys
import os
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

def run_benchmark(qemu_process, benchmark: SPEC.Variant, info_file, userspace):
    for command in benchmark.setup:
        qemu_process.sendline(command)
        expect_qemu_command_end(qemu_process)

    # TODO alternatively could put all commands in bash script and run that
    # (tracing each command individually seems unideal for timing purposes, if not other reasons)
    qtrace_prefix = "time qtrace{} exec -- ".format(" -u" if userspace else "")
    for command in benchmark.execution:
        qemu_process.sendline(qtrace_prefix + command)

        qemu_process.expect(re.compile(rb"[0-9]+\.[0-9]+ real\s+[0-9]+\.[0-9]+ user\s+[0-9]+\.[0-9]+ sys"), timeout=None)
        time_str = qemu_process.match.group(0).decode('utf-8')
        info_file.write(f"Time taken: {time_str}")
        print(f"Time taken: {time_str}")

        expect_qemu_command_end(qemu_process)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A tool for the automated running of SPEC2006 benchmarks in cheribsd.")

    parser.add_argument("benchmark_name", type=str, metavar="benchmark", help="Benchmark name")
    parser.add_argument("benchmark_variant", choices=["test", "train", "ref"],
        help="Benchmark variant (either test, train, or ref)")

    parser.add_argument("--logfile", type=str, metavar="PATH", dest="logfile_path", help="Path to the logfile")
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose", help="Forward qemu output to stdout (already present in log files)")
    parser.add_argument("--perthread", action="store_true", dest="perthread_enabled", help="Enable perthread tracing")
    parser.add_argument("-u", "--userspace", action="store_true", dest="userspace_enabled", help="Enable userspace tracing")

    args = parser.parse_args()

    if args.benchmark_name not in SPEC.all_benchmarks:
        raise RuntimeError(f"Benchmark name not found in: {SPEC.all_benchmarks.keys()}")

    selected_benchmark = SPEC.all_benchmarks[args.benchmark_name]
    selected_variant = getattr(selected_benchmark, args.benchmark_variant)

    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

    trace_output_dir = os.path.abspath(datetime.now().strftime("trace_%Y-%m-%d_%H-%M-%S_%f"))
    print(f"Writing to: {trace_output_dir}")
    os.mkdir(trace_output_dir) # NOTE will throw exception if folder already exists

    with open(os.path.join(trace_output_dir, "info.txt"), "w") as info_file:
        info_file.write(f"Benchmark Name: {args.benchmark_name}\n")
        info_file.write(f"Benchmark Variant: {args.benchmark_variant}\n")
        info_file.write(f"Perthread Tracing Enabled: {args.perthread_enabled}\n")
        info_file.write(f"Userspace Tracing Enabled: {args.userspace_enabled}\n")
        info_file.write("\n")
        info_file.flush()

        # TODO test running this in a directory with spaces in the absolute path

        traceconv_compress_process = start_process(
            f"{os.path.join(script_dir, 'cheri-trace-converter/build/traceconv')} convert "
            f"{os.path.join(script_dir, 'fifos/fifo_trace_raw')} {os.path.join(script_dir, 'fifos/fifo_trace_compressed.lz4')} "
            f"|& tee {os.path.join(trace_output_dir, 'traceconv_compress.log')}",
            info_file=info_file, cwd=trace_output_dir)

        split_process = start_process(
            f"<{os.path.join(script_dir, 'fifos/fifo_trace_compressed.lz4')} "
            f"tee {os.path.join(script_dir, 'fifos/fifo_trace_split_a.lz4')} "
            f"> {os.path.join(script_dir, 'fifos/fifo_trace_split_b.lz4')} "
            f"|& tee {os.path.join(trace_output_dir, 'split.log')}",
            info_file=info_file, cwd=trace_output_dir)

        traceconv_initial_state_process = start_process(
            f"{os.path.join(script_dir, 'cheri-trace-converter/build/traceconv')} get-initial-state "
            f"{os.path.join(script_dir, 'fifos/fifo_trace_split_b.lz4')} {os.path.join(trace_output_dir, 'trace_initial_state.bin')} "
            f"|& tee {os.path.join(trace_output_dir, 'traceconv_initial_state.log')}",
            info_file=info_file, cwd=trace_output_dir)

        traceconv_drcachesim_process = start_process(
            f"{os.path.join(script_dir, 'cheri-trace-converter/build/traceconv')} convert-drcachesim-paddr "
            f"{os.path.join(script_dir, 'fifos/fifo_trace_split_a.lz4')} {os.path.join(script_dir, 'fifos/fifo_trace_drcachesim.lz4')} "
            f"|& tee {os.path.join(trace_output_dir, 'traceconv_drcachesim.log')}",
            info_file=info_file, cwd=trace_output_dir)

        drcachesim_process = start_process(
            f"{os.path.join(script_dir, 'dynamorio_build/bin64/drrun')} -t drcachesim "
            f"-config_file {os.path.join(script_dir, 'drcachesim_config.txt')} "
            f"-infile {os.path.join(script_dir, 'fifos/fifo_trace_drcachesim.lz4')} "
            f"|& tee {os.path.join(trace_output_dir, 'drcachesim.log')}",
            info_file=info_file, cwd=trace_output_dir)

        qemu_process = start_process(
            f"{os.path.join(script_dir, 'cheribuild/cheribuild.py')} "
            f"--source-root {os.path.join(script_dir, 'cheri')} "
            "run-riscv64-purecap --run-riscv64-purecap/ephemeral "
            "--run-riscv64-purecap/extra-options=\""
            f"{'--icount shift=0,align=off ' if not args.userspace_enabled else ''}"
            "--cheri-trace-backend drcachesim "
            f"--cheri-trace-drcachesim-tracefile {os.path.join(script_dir, 'fifos/fifo_trace_raw')} "
            f"--cheri-trace-drcachesim-dbgfile {os.path.join(trace_output_dir, 'trace_qemu_dbg.txt')}\" "
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

        run_benchmark(qemu_process, selected_variant, info_file, args.userspace_enabled)

        qemu_process.sendcontrol('a')
        qemu_process.send('x')
        expect_process_end(qemu_process)

        expect_process_end(traceconv_compress_process)
        expect_process_end(split_process)
        expect_process_end(traceconv_initial_state_process)
        expect_process_end(traceconv_drcachesim_process)
        expect_process_end(drcachesim_process)
