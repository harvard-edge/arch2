# nano-kpu(中文版)

本仓库包含一颗由 Kimi-K3 完全自主设计与实现的 nano 规模混合架构推理芯片的
RTL 设计,以及配套的功能仿真与性能(时序/面积)测试流程。模型为
hybrid-attention MoE transformer:**KDA(Kimi Delta Attention)线性注意力**、
**NoPE 多头潜在注意力(MLA)**、**sigmoid 路由 MoE(top-2 路由专家 +
一个共享专家)**,以及 **attention-residual mixing**;int4 group-128 权重,
teacher-forced 逐 token decode。

*声明:本仓库是 Kimi K3 的能力演示(demonstration),并非 Moonshot AI 官方项目。*

## 目录结构

```
rtl/            芯片 RTL(顶层模块 msh_chip_top;filelist.f 为编译清单)
  ├── roms/     LUT 初始化 hex(sigmoid/alpha/expneg/rsqrt/recip)+ 生成器说明
  └── selfmodel/  bit-exact Python 定点模型(仿真辅助)
reference/      float32 黄金参考模型(正确性判定的基准;golden 在评测时现算)
harness/        功能仿真 + 性能评测流程
  ├── evaluate.py   主入口:正确性(cos/argmax)+ cycles/token + 吞吐
  ├── tb/           Verilator C++ testbench(16 B/cycle DRAM 端口模型)
  ├── macros/       msh_sram / msh_rom 宏模型(仿真注入 + 综合 blackbox)
  ├── synth_area.ys / synth_tech.ys / synth_netlist.ys
  │                 性能脚本:yosys 面积/NE、Nangate45 映射时序、门级网表
  ├── lib/          工艺库(setup 时下载,不随仓库分发)
  └── scoring.py / audit.py / memmap.py / check_integrity.py ...
                    scoring.py = 正确性判定 + 综合度量助手
                    (NE/latch/lint 阈值,无计分)
docs/           规格文档(architecture / interface / memory_map /
                quantization / TASK_SPEC)
weights/        权重格式说明
Makefile        统一入口
```

## 环境搭建(Setup)

克隆后先执行一次:

```bash
bash scripts/setup_env.sh      # 或:make setup
source scripts/kpu-env.sh      # 把工具链 env 加进 PATH
```

脚本以 conda 为中心,幂等:

1. **Conda**——有现成的用现成的,没有则自动装 Miniconda 到
   `~/miniconda3`(免 root)。
2. **独立 env `nano-kpu`**——从 conda-forge 创建,含 **Verilator 5.x**
   (基线 5.050)、**yosys >= 0.64**、**python 3.12 + numpy**;
   绝不动任何既有 base 环境。
3. **`scripts/kpu-env.sh`**——脚本生成的 PATH 文件;source 一下(或开新
   shell),`verilator` / `yosys` / `python3` 即指向该 env。
4. **Nangate45 工艺库**——从 OpenROAD-flow-scripts 下载
   `NangateOpenCellLibrary_typical.lib`(pin commit + SHA-256 校验)到
   `harness/lib/`。该库刻意不随仓库分发;只有综合(timing/area)需要它,
   纯仿真不需要。

前置要求:bash、`curl` 或 `wget`、可访问 repo.anaconda.com(或镜像)与
raw.githubusercontent.com。任一步失败,脚本会给出具体错误并以非零退出
——解决问题后重跑即可。

## 快速开始

依赖:Verilator 5、yosys(综合用)、python3 + numpy。

```bash
bash scripts/setup_env.sh                  # 仅首次:装工具链 + 下载工艺库
source scripts/kpu-env.sh                  # 把工具链 env 加进 PATH
python3 harness/evaluate.py --quick        # 功能仿真(短序列,分钟级)
python3 harness/evaluate.py                # 完整评测(仿真 + 时序/面积综合,小时级)
python3 harness/evaluate.py --skip-synth   # 功能 + randreset + latency,不跑综合
make synth                                 # 只跑面积/时序流程
make lint / audit / selftest               # 单项检查
```

注意:`rtl/selfmodel/run.sh` 契约使用 PATH 中的 `python3`,需带 numpy。

## 协议与测量要点(详见 docs/)

- 接口:命令流(`RUN 0x1` -> `DONE 0xD0DE`)+ 128-bit DRAM 口(读保序、
  >=24 cycle 延迟、写 posted)+ 自描述内存镜像(header + descriptor 表)。
- 正确性:对照 float32 参考,每行 logits cos >= 0.98,pooled argmax >= 0.99。
- 吞吐:`cycles_per_token = 长序列仿真拍数 / seq_len`,
  `tokens/s = 时钟 / cpt`。
- 存储规则:触发器以外的存储一律走 `msh_sram`/`msh_rom` 宏;宏 bit 按
  ~1 Mbit/mm2 计入面积预算。

**测量方法说明**:为保证测试速度,area 与 timing 在**综合(synthesis)阶段**
测得——即 yosys/abc 映射与静态时序的 pre-layout 估计,**未经过后端布局布线
(P&R)验证**。为保证不同设计之间的可比性,测量使用一套**固定、冻结的综合
参数**,刻意不为单个设计搜索最优参数;因此报告数字是保守、可复现的基线,
而非最优 QoR,也非签核(sign-off)值。

## 许可证与第三方资产

本仓库以 Apache License 2.0 发布(见 `LICENSE`)。

**Nangate45 标准单元库**(`NangateOpenCellLibrary_typical.lib`)**不随
仓库分发**,由 `scripts/setup_env.sh` 在 setup 时从
[The-OpenROAD-Project/OpenROAD-flow-scripts](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts)
(`flow/platforms/nangate45/lib/`)获取。
