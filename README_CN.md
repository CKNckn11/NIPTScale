# NIPTScale 0.2.0

[English](README.md) | **简体中文**

`NIPTScale` 是面向大规模单端、短读长、低深度 WGS-NIPT 数据的任务生成与调度框架。它自动发现 `硬盘/Run/Lane/FASTQ` 层级，建立可审计的 FASTQ 清单，并生成从比对到 [BaseVar2](https://github.com/ShujiaHuang/BaseVar2) 变异检测的独立 Shell 任务。

框架借鉴 [ilus](https://github.com/ShujiaHuang/ilus) 的设计思想：Python 负责检查配置、整理输入并生成任务；BWA、SAMtools、BCFtools 和 BaseVar2 仍以透明、可独立执行的 Shell 命令运行。

> **适用边界：** 当前版本针对本项目的孕妇外周血浆 cfDNA、单端 35 bp、超低深度 WGS-NIPT 数据。它是科研流程生成器，不是临床诊断软件，也不包含基因型填充、GWAS、母胎基因型分离或疾病风险解释。

## 主要功能

- 自动扫描 NIPT 硬盘并识别 `L01/L02/...` Lane；
- 生成 Lane、FASTQ、文件大小、纳入状态和排除原因清单；
- 默认排除小于 100,000,000 字节及名称含 `undecoded` 的 FASTQ；
- 多 Lane 并行，每个 Lane 内多样本并行；
- 使用 `bwa aln + samse` 处理当前单端 35 bp 数据；
- 比对、区域测试和正式 WGS 分开运行，互不覆盖；
- 合格 BAM 自动复用，并用 `.done/.failed` 标记任务状态；
- 调用 BaseVar2 分区检测并生成 Lane 级压缩、索引 VCF。

## 安装

```bash
git clone https://github.com/CKNckn11/NIPTScale.git
cd NIPTScale
python -m pip install -e .

niptscale --version
niptscale --help
```

旧命令 `niptflow` 仅作为兼容别名保留，新项目请使用 `niptscale`。

## 配置

```bash
cp examples/niptscale.example.yaml my.node.yaml
cp -r examples/site_pipeline /opt/niptscale-pipeline
# 正式运行前修改 /opt/niptscale-pipeline/00_config.sh
```

```yaml
paths:
  scan_root: /data/NIPT
  result_root: /results/BaseVar2
  pipeline_dir: /opt/niptscale-pipeline

rules:
  min_fastq_bytes: 100000000
  lane_pattern: '^L\d{2}$'

parallel:
  alignment_lane_jobs: 4
  samples_per_lane: 8
  alignment_threads_per_sample: 3
  samtools_threads_per_sample: 2
  sort_memory_per_thread: 1G
  test_lane_jobs: 4
  wgs_lane_jobs: 4
```

`alignment_lane_jobs × samples_per_lane` 是同时运行的最大样本数。实际设置还要考虑 CPU、内存、磁盘吞吐和共享存储压力。

`pipeline_dir` 是当前 0.2.0 版本的站点适配层，必须包含：

```text
00_config.sh
03_make_bam_list.sh
04_basevar_test_only.sh
05_wgs_generate_commands.sh
06_wgs_run_regions.sh
07_wgs_concat.sh
```

其中 `00_config.sh` 定义 BaseVar2、参考基因组、结果目录和运行环境。详见[配置说明](docs/configuration.md)。

## 完整流程

### 1. 扫描数据

```bash
niptscale scan \
  -C my.node.yaml \
  -O /results/NIPTScale/path_manifest
```

扫描只读，不复制或修改 FASTQ。输出包括 Lane 路径表、全部 FASTQ 路径表、Lane 汇总表，以及记录大小、状态和排除原因的 FASTQ 清单。

### 2. 生成项目任务

```bash
PROJECT=/results/NIPTScale/projects/V350298010

niptscale generate \
  -C my.node.yaml \
  -L /data/NIPT/Disk10/V350298010/L01 \
  -L /data/NIPT/Disk10/V350298010/L02 \
  -L /data/NIPT/Disk10/V350298010/L03 \
  -L /data/NIPT/Disk10/V350298010/L04 \
  -O "${PROJECT}"
```

也可以使用 `-I nipt_lane_paths.txt` 一次读入全部 Lane。

### 3. FASTQ 到 BAM

```bash
nohup bash "${PROJECT}/00.shell/01.alignment.commands.sh" \
  > "${PROJECT}/00.shell/alignment.master.log" \
  2>&1 < /dev/null &

echo $! > "${PROJECT}/00.shell/alignment.pid"
```

该命令会同时启动多个 Lane，并在每个 Lane 内并行处理通过筛选的 FASTQ。真正参加分析的样本以各 Lane 的 `manifest/fastq_manifest.tsv` 为准，不以旧的 `samples/` 目录数量为准。

### 4. 区域测试（推荐但可选）

```bash
nohup bash "${PROJECT}/00.shell/02.test.commands.sh" \
  > "${PROJECT}/00.shell/test.master.log" \
  2>&1 < /dev/null &
```

### 5. 全基因组 BaseVar2

```bash
nohup bash "${PROJECT}/00.shell/03.wgs.commands.sh" \
  > "${PROJECT}/00.shell/wgs.master.log" \
  2>&1 < /dev/null &
```

测试与 WGS 使用独立目录；WGS 不依赖测试 VCF，但两者都要求比对完成并已生成 `bam.list`。

### 6. 检查状态

```bash
niptscale check-jobs \
  -P "${PROJECT}" \
  -O "${PROJECT}/job_status.tsv"
```

状态包括 `done`、`failed` 和 `pending_or_running`。完整结果目录见[输出结构](docs/output-layout.md)。

## BaseVar2 VCF 能否直接做 GWAS？

不能把它直接等同于最终的 GWAS dosage VCF。进入表型 GWAS 前，通常还需要样本与表型对应检查、参考版本和等位基因统一、跨 Lane 整合、样本和位点 QC、低深度基因型填充、群体结构与亲缘关系处理，以及对混合 cfDNA 信号近似母体基因型的研究设计论证。这些步骤尚未包含在 0.2.0 中。

## 与 BaseVar2、ilus 的关系

- [BaseVar2](https://github.com/ShujiaHuang/BaseVar2) 是外部变异检测软件，NIPTScale 不重新实现或打包其算法。
- [ilus](https://github.com/ShujiaHuang/ilus) 提供“配置文件 + 任务生成 + 独立 Shell + 状态检查”的框架参考。NIPTScale 不是 ilus 的分支，重点是本项目的 NIPT 目录结构、单端短读长、FASTQ 清单及 BaseVar2 编排。

## 测试与引用

```bash
python -m unittest discover -s tests -v
```

使用 BaseVar2 变异检测时请引用：

> Liu S. et al. Utilizing non-invasive prenatal test sequencing data for human genetic investigation. *Cell Genomics* 4, 100669 (2024). https://doi.org/10.1016/j.xgen.2024.100669

## 数据安全

NIPT 属于敏感的母体与胎儿基因组数据。FASTQ、BAM、VCF、样本清单和表型表应保存在受控环境中，并遵循知情同意、伦理审批和数据传输要求。请勿向本仓库提交个体级基因组数据或可识别信息。

## 许可证

NIPTScale 使用 [MIT License](LICENSE)。所有外部软件遵循各自许可证。
