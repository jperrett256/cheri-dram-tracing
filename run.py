import sys
import os
import re
import argparse
import pexpect
import spec_commands as SPEC
from datetime import datetime

def start_process(command, **kwargs):
    print("COMMAND START: {}".format(command))
    print("")

    child = pexpect.spawn("/bin/bash", ['-c', command], **kwargs)
    child.logfile = sys.stdout.buffer # TODO make argument
    return child

def expect_process_end(child):
    child.expect(pexpect.EOF, timeout=None)
    print("")
    if child.wait() != 0:
        raise RuntimeError("Failed to execute command: '{}'".format(command))

def expect_qemu_command_end(qemu_process):
    qemu_process.expect(re.compile(rb"toor@cheribsd-riscv64-purecap:.* #"), timeout=None)

def run_benchmark(qemu_process, benchmark: SPEC.Variant, userspace=True):
    for command in benchmark.setup:
        qemu_process.sendline(command)
        expect_qemu_command_end(qemu_process)

    # TODO alternatively could put all commands in bash script and run that
    # (tracing each command individually seems unideal for timing purposes, if not other reasons)
    qtrace_prefix = "time qtrace{} exec -- ".format(" -u" if userspace else "")
    for command in benchmark.execution:
        qemu_process.sendline(qtrace_prefix + command)

        qemu_process.expect(re.compile(rb"[0-9]+\.[0-9]+ real\s+[0-9]+\.[0-9]+ user\s+[0-9]+\.[0-9]+ sys"), timeout=None)
        print(f"Time taken: {qemu_process.match.group(0).decode('utf-8')}")

        expect_qemu_command_end(qemu_process)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A tool for the automated running of SPEC2006 benchmarks in cheribsd.")

    parser.add_argument("benchmark_name", type=str, metavar="benchmark", help="Benchmark name")
    parser.add_argument("benchmark_variant", choices=["test", "train", "ref"], # metavar="variant",
        help="Benchmark variant (either test, train, or ref)")

    parser.add_argument("--logfile", type=str, metavar="PATH", dest="logfile_path", help="Path to the logfile")
    parser.add_argument("--perthread", action="store_true", dest="perthread_enabled", help="Enable perthread tracing")
    parser.add_argument("--userspace", action="store_true", dest="userspace_enabled", help="Enable userspace tracing")

    args = parser.parse_args()

    print("Benchmark Name:", args.benchmark_name)
    print("Benchmark Variant:", args.benchmark_variant)
    print("Logfile:", args.logfile_path) # TODO
    print("Perthread Tracing Enabled:", args.perthread_enabled)
    print("Userspace Tracing Enabled:", args.userspace_enabled)


    if args.benchmark_name not in SPEC.all_benchmarks:
        raise RuntimeError("Benchmark name not found in: {}".format(SPEC.all_benchmarks.keys()))

    selected_benchmark = SPEC.all_benchmarks[args.benchmark_name]
    selected_variant = getattr(selected_benchmark, args.benchmark_variant)

    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

    trace_output_dir = os.path.abspath(datetime.now().strftime("trace_%Y-%m-%d_%H-%M-%S_%f"))
    print(trace_output_dir)
    os.mkdir(trace_output_dir) # NOTE will throw exception if folder already exists

    # TODO test running this in a directory with spaces in the absolute path

    traceconv_compress_process = start_process(
        f"{os.path.join(script_dir, 'cheri-trace-converter/build/traceconv')} convert "
        f"{os.path.join(script_dir, 'fifos/fifo_trace_raw')} {os.path.join(script_dir, 'fifos/fifo_trace_compressed.lz4')}",
        cwd=trace_output_dir)

    split_process = start_process(
        f"<{os.path.join(script_dir, 'fifos/fifo_trace_compressed.lz4')} "
        f"tee {os.path.join(script_dir, 'fifos/fifo_trace_split_a.lz4')} "
        f"> {os.path.join(script_dir, 'fifos/fifo_trace_split_b.lz4')}",
        cwd=trace_output_dir)

    traceconv_initial_state_process = start_process(
        f"{os.path.join(script_dir, 'cheri-trace-converter/build/traceconv')} get-initial-state "
        f"{os.path.join(script_dir, 'fifos/fifo_trace_split_b.lz4')} {os.path.join(trace_output_dir, 'trace_initial_state.bin')}",
        cwd=trace_output_dir)

    traceconv_drcachesim_process = start_process(
        f"{os.path.join(script_dir, 'cheri-trace-converter/build/traceconv')} convert-drcachesim-paddr "
        f"{os.path.join(script_dir, 'fifos/fifo_trace_split_a.lz4')} {os.path.join(script_dir, 'fifos/fifo_trace_drcachesim.lz4')}",
        cwd=trace_output_dir)

    drcachesim_process = start_process(
        f"{os.path.join(script_dir, 'dynamorio_build/bin64/drrun')} -t drcachesim "
        f"-config_file {os.path.join(script_dir, 'drcachesim_config.txt')} "
        f"-infile {os.path.join(script_dir, 'fifos/fifo_trace_drcachesim.lz4')}",
        cwd=trace_output_dir)

    qemu_process = start_process(
      f"{os.path.join(script_dir, 'cheribuild/cheribuild.py')} "
      "--source-root cheri run-riscv64-purecap --run-riscv64-purecap/ephemeral "
      "--run-riscv64-purecap/extra-options=\"--icount shift=0,align=off --cheri-trace-backend drcachesim "
      f"--cheri-trace-drcachesim-tracefile {os.path.join(script_dir, 'fifos/fifo_trace_raw')} "
      f"--cheri-trace-drcachesim-dbgfile {os.path.join(trace_output_dir, 'trace_qemu_dbg.txt')}\"")

    # TODO would subprocess allow us to see the output of multiple child processes at once?
    # traceconv_compress_process.expect(pexpect.EOF) # DEBUG
    # traceconv_initial_state_process.expect(pexpect.EOF) # DEBUG
    # split_process.expect(pexpect.EOF) # DEBUG
    # traceconv_drcachesim_process.expect(pexpect.EOF) # DEBUG
    # drcachesim_process.expect(pexpect.EOF) # DEBUG

    qemu_process.expect("login:", timeout=None)
    qemu_process.sendline("toor")

    expect_qemu_command_end(qemu_process)

    # TODO support for options:
    #     - logfile path

    if args.perthread_enabled:
        qemu_process.sendline("sysctl hw.qemu_trace_perthread=1")
        expect_qemu_command_end(qemu_process)

    assert(traceconv_compress_process.isalive())
    assert(traceconv_drcachesim_process.isalive())
    assert(drcachesim_process.isalive())
    assert(traceconv_initial_state_process.isalive())
    assert(split_process.isalive())

    run_benchmark(qemu_process, selected_variant, userspace=args.userspace_enabled)

    qemu_process.sendcontrol('a')
    qemu_process.send('x')
    expect_process_end(qemu_process)

    expect_process_end(traceconv_compress_process)
    expect_process_end(traceconv_drcachesim_process)
    expect_process_end(drcachesim_process)
