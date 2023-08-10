import sys
# import subprocess
import pexpect
import spec_commands as SPEC

def start_process(command):
	print("COMMAND START: {}".format(command))
	print("")

	child = pexpect.spawn("/bin/bash", ['-c', command])
	child.logfile = sys.stdout.buffer
	return child

def expect_process_end(child):
	child.expect(pexpect.EOF, timeout=None)
	print("")
	if child.wait() != 0:
		raise RuntimeError("Failed to execute command: '{}'".format(command))

def expect_qemu_command_end(qemu_process):
	qemu_process.expect("toor@cheribsd-riscv64-purecap", timeout=None)
	qemu_process.expect("#")

def run_benchmark(qemu_process, benchmark: SPEC.Variant, userspace=True):
	for command in benchmark.setup:
		qemu_process.sendline(command)
		expect_qemu_command_end(qemu_process)

	# alternatively could put all commands in bash script and run that
	qtrace_prefix = "time qtrace{} exec -- ".format(" -u" if userspace else "")
	for command in benchmark.execution:
		qemu_process.sendline(qtrace_prefix + command)
		expect_qemu_command_end(qemu_process)


qemu_process = start_process(
	"./cheribuild/cheribuild.py --source-root cheri run-riscv64-purecap --run-riscv64-purecap/ephemeral " \
	"--run-riscv64-purecap/extra-options=\"--icount shift=0,align=off --cheri-trace-backend drcachesim " \
	"--cheri-trace-drcachesim-tracefile /dev/null --cheri-trace-drcachesim-dbgfile /dev/null\"")

qemu_process.expect("login:", timeout=None)

qemu_process.sendline("toor")

expect_qemu_command_end(qemu_process)

# qemu_process.sendline("time ls")
# qemu_process.expect("real", timeout=None)
# qemu_process.expect("user", timeout=None)
# qemu_process.expect("sys", timeout=None)

# TODO start other programs as well

# TODO support for options:
# 	- logfile path
#	- perthread tracing, userspace tracing
#	- benchmark name and variant

# TODO option to add sysctl hw.qemu_trace_perthread=1
# TODO option for userspace tracing
run_benchmark(qemu_process, SPEC.libquantum.test)


qemu_process.sendcontrol('a')
qemu_process.send('x')


expect_process_end(qemu_process)

