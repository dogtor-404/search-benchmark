# 运行与核查工具

工具使用Python 3.10+标准库；实际模型调用还需要Claude Code、订阅登录、网络及macOS钥匙串中的 `DEEPSEEK_API_KEY`。在项目根目录执行命令。模型版本、路由与价格是本次实验的冻结配置，复跑前需重新核实。

## 离线核查现有结果

```sh
python3 tools/verify_release.py
python3 tools/restore_first_round.py --cache /path/to/chinese_simpleqa.jsonl
python3 -m unittest discover -s tests -v
```

第一条校验公开文件哈希、2200份作答覆盖，从原评分票复算首页的原100/120题正确率，并重算当前1870份逐题计分及各组汇总，不读私人凭据或联网。第二条恢复本地题库；不指定缓存时从固定上游版本下载并核验SHA256。未恢复时4项依赖完整第一轮题库的测试会跳过。

现有第一轮公开归档在 `results/2026-10-20/`，第二轮在 `results/2026-10-21-multilingual/`。运行器的新输出写入 `tmp/`；历史manifest和receipt的哈希对应脱敏前原件，不能直接用于验证公开文件，也不能把公开归档冒充可原地续跑的原始目录。公开哈希以根目录 `PUBLIC-SHA256.json` 为准。

## 新实验入口

```sh
python3 tools/bench.py check
python3 tools/bench.py plan --phase pilot
python3 tools/bench.py preflight
python3 tools/multilingual.py plan
```

`plan` 只显示计划。新闻窗口、模型配置、版本与预算应按新实验条件检查；本次实验的历史授权不适用于其他人的账号。

第一轮试跑示例：

```sh
python3 tools/bench.py run --phase pilot --execute --quota-confirmed
python3 tools/grade.py prepare --phase pilot
python3 tools/grade.py run --phase pilot --judge claude --execute --quota-confirmed
python3 tools/grade.py run --phase pilot --judge deepseek --execute --quota-confirmed
python3 tools/grade.py resolve --phase pilot
python3 tools/analyze.py --phase pilot
```

`--execute` 启用真实调用；`--quota-confirmed` 表示执行者已确认预算；全量运行还要求 `--pilot-approved`。这些选项不会自动取得任何账号授权。不要把未决项、失败调用或缺失结果当作错题。有效记录续跑前校验冻结配置与原文哈希，失败原文需保留，禁止静默覆盖。

所有组每题最多五次实际搜索，DeepSeek参数固定为 `count=10, need_content=false`，不开放Fetch。预算拒绝与实际搜索分别计数。各被测进程清理模型路由、凭据和IDE上下文环境；密钥仅在调用时由钥匙串读入子进程，不写文件。

## 本次实验与历史工具

| 用途 | 入口或材料 | 口径 |
|---|---|---|
| 第一轮不搜索诊断、正式搜索 | `baseline.py`、`search_run.py`、`report.py` | 原100题，三票多数；诊断双判快照见根目录baseline.md |
| 第二轮作答 | `multilingual.py` | 原六语种120题 |
| 第二轮正式评分 | `multilingual_live_blind.py publish/merge`、`multilingual_single_report.py` | 一位独立AI单票；不是三票多数 |
| 早期第二轮评分方案 | `multilingual_pipeline.py`、`multilingual_grade_parallel.py`、`multilingual_independent_pipeline.py`、`multilingual_report.py` | 历史API/多票方案，未用于第二轮最终评分 |
| 历史搜索效率 | `first_round_supplement.py`、`multilingual_search_efficiency.py`、`revise_first_round.py` | 保留原100分制及额外搜索扣5分等历史行为，不代表当前得分 |
| 402份错答分类 | `results/2026-10-21-response-review/no-search-double-blind/` | 双盲分类与第三票裁决 |
| 最终提交状态与统一计分 | `results/2026-10-21-unified-score/` | 原2200份，正确+5、错误提交−3、弃答/撤回0，第二次起每次搜索−1 |
| 当前删题及分歧结案 | `results/2026-10-21-revised-92-95/` | 第一轮92题、第二轮95题，1870份；事后补充分析 |
| 累计token估算 | `results/2026-10-21-token-usage/` | 含私人会话汇总；会话源未公开，无法独立重算该部分 |

结果目录中的 `ops/` 保存生成当时材料的历史脚本；会重写报告或依赖未公开源文件，不要直接在归档上运行。核查现有公开结果使用 `verify_release.py`。`search-efficiency-template.html` 是历史搜索图表生成器的必需模板。

`prepare_public.py` 从本机完整项目生成独立脱敏副本，拒绝覆盖已有目录；本地私有词表位于 `tmp/public-redactions.json`。公开目录不包含该词表或完整私人输入，不能代替原项目重新导出。原始作答、评分票、失败重试、来源与修订凭据保留；运行计数文件、进度快照和私人日志不导出。
