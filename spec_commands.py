# SPEC2006

class Benchmark:
	def __init__(self, test, train, ref):
		self.test = test
		self.train = train
		self.ref = ref

class Variant:
	def __init__(self, setup, execution):
		# TODO strip each element in list or no?
		self.setup = setup.strip().split("\n")
		self.execution = execution.strip().split("\n")
		# TODO double check && will work with qtrace

# For actual tracing, will want to run it as:

## libquantum
all_benchmarks = \
{
	"libquantum": Benchmark(
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/462.libquantum/
""",
"""
./462.libquantum 33 5
"""
		),
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/462.libquantum/
""",
"""
./462.libquantum 143 25
"""
		),
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/462.libquantum/
""",
"""
./462.libquantum 1397 8
"""
		)
	),

	"xalancbmk": Benchmark(
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/483.xalancbmk/
""",
"""
./483.xalancbmk -v data/test/input/test.xml data/test/input/xalanc.xsl
"""
		),
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/483.xalancbmk/
""",
"""
./483.xalancbmk -v data/train/input/allbooks.xml data/train/input/xalanc.xsl
"""
		),
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/483.xalancbmk/
""",
"""
./483.xalancbmk -v data/ref/input/t5.xml data/ref/input/xalanc.xsl
"""
		)
	),

	"omnetpp": Benchmark(
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/471.omnetpp/
""",
"""
./471.omnetpp -f data/test/input/omnetpp.ini
"""
		),
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/471.omnetpp/
""",
"""
./471.omnetpp -f data/train/input/omnetpp.ini
"""
		),
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/471.omnetpp/
""",
"""
./471.omnetpp -f data/ref/input/omnetpp.ini
"""
		)
	),

	"bzip2": Benchmark(
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/401.bzip2/
""",
"""
./401.bzip2 data/all/input/input.program 5
./401.bzip2 data/test/input/dryer.jpg 2
"""
		),
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/401.bzip2/
""",
"""
./401.bzip2 data/all/input/input.program 10
./401.bzip2 data/train/input/byoudoin.jpg 5
./401.bzip2 data/all/input/input.combined 80
"""
		),
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/401.bzip2/
""",
"""
./401.bzip2 data/all/input/input.source 280
./401.bzip2 data/ref/input/chicken.jpg 30
./401.bzip2 data/ref/input/liberty.jpg 30
./401.bzip2 data/all/input/input.program 280
./401.bzip2 data/ref/input/text.html 280
./401.bzip2 data/all/input/input.combined 200
"""
		)
	),

	"hmmer": Benchmark(
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/456.hmmer/
""",
"""
./456.hmmer --fixed 0 --mean 325 --num 45000 --sd 200 --seed 0 data/test/input/bombesin.hmm
"""
		),
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/456.hmmer/
""",
"""
./456.hmmer --fixed 0 --mean 425 --num 85000 --sd 300 --seed 0 data/train/input/leng100.hmm
"""
		),
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/456.hmmer/
""",
"""
./456.hmmer data/ref/input/nph3.hmm data/ref/input/swiss41
./456.hmmer --fixed 0 --mean 500 --num 500000 --sd 350 --seed 0 data/ref/input/retro.hmm
"""
		)
	),

	"astar": Benchmark(
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/473.astar/
cd ./data/test/input/
""",
"""
../../../473.astar lake.cfg
"""
		),
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/473.astar/
cd ./data/train/input/
""",
"""
../../../473.astar BigLakes1024.cfg
../../../473.astar rivers1.cfg
"""
		),
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/473.astar/
cd ./data/ref/input/
""",
"""
../../../473.astar BigLakes2048.cfg
../../../473.astar rivers.cfg
"""
		)
	),

	"sjeng": Benchmark(
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/458.sjeng/
""",
"""
./458.sjeng data/test/input/test.txt
"""
		),
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/458.sjeng/
""",
"""
./458.sjeng data/train/input/train.txt
"""
		),
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/458.sjeng/
""",
"""
./458.sjeng data/ref/input/ref.txt
"""
		)
	),

	"h264ref": Benchmark(
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/464.h264ref/
cd ./data/test/input/
""",
"""
../../../464.h264ref -d foreman_test_encoder_baseline.cfg
"""
		),
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/464.h264ref/
cd ./data/train/input/
""",
"""
../../../464.h264ref -d foreman_test_encoder_baseline.cfg
"""
		),
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/464.h264ref/
cd ./data/ref/input/
""",
"""
../../../464.h264ref -d foreman_ref_encoder_baseline.cfg
../../../464.h264ref -d foreman_ref_encoder_main.cfg
../../../464.h264ref -d sss_encoder_main.cfg
"""
		)
	),

	"gobmk": Benchmark(
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/445.gobmk/
cd ./data/all/input
""",
"""
./445.gobmk --quiet --mode gtp < ../../test/input/capture.tst
./445.gobmk --quiet --mode gtp < ../../test/input/connect.tst
./445.gobmk --quiet --mode gtp < ../../test/input/connect_rot.tst
./445.gobmk --quiet --mode gtp < ../../test/input/connection.tst
./445.gobmk --quiet --mode gtp < ../../test/input/connection_rot.tst
./445.gobmk --quiet --mode gtp < ../../test/input/custone.tst
./445.gobmk --quiet --mode gtp < ../../test/input/dniwog.tst
"""
		),
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/445.gobmk/
cd ./data/all/input
""",
"""
./445.gobmk --quiet --mode gtp < ../../train/input/arb.tst
./445.gobmk --quiet --mode gtp < ../../train/input/arend.tst
./445.gobmk --quiet --mode gtp < ../../train/input/arion.tst
./445.gobmk --quiet --mode gtp < ../../train/input/atari_atari.tst
./445.gobmk --quiet --mode gtp < ../../train/input/blunder.tst
./445.gobmk --quiet --mode gtp < ../../train/input/bluzco.tst
./445.gobmk --quiet --mode gtp < ../../train/input/nicklas2.tst
./445.gobmk --quiet --mode gtp < ../../train/input/nicklas4.tst
"""
		),
		Variant(
"""
cd /opt/riscv64-purecap/spec2006/445.gobmk/
cd ./data/all/input
""",
"""
./445.gobmk --quiet --mode gtp < ../../ref/input/13x13.tst
./445.gobmk --quiet --mode gtp < ../../ref/input/nngs.tst
./445.gobmk --quiet --mode gtp < ../../ref/input/score2.tst
./445.gobmk --quiet --mode gtp < ../../ref/input/trevorc.tst
./445.gobmk --quiet --mode gtp < ../../ref/input/trevord.tst
"""
		)
	)
}
