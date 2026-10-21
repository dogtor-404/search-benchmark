# search-benchmark：给搭建测试的 agent 看

方案在 [README.md](../README.md)：要回答的问题、分组、题目、每组怎么跑、指标、统计、步骤。[已有项目调研.md](../已有项目调研.md) 是别人的评测项目，判分、统计的写法可以参考 Exa 的 Scout，但不要改用它（README 的决定记录里写了为什么）。

照 README 做。要改设计（分组、题目组合、提示词、搜索次数上限、判分方法），先问用户。

## 规矩

- **先试跑，再全量**：先做 README “步骤”里的 1–3（建题库，写工具和脚本，每组试跑 10 道题），把试跑结果和量出来的花费给用户看，用户点头了再跑全量。Claude 那几组扣用户 Max 订阅的周额度，跑之前请用户确认额度够。
- **DeepSeek 的 key**：只从 macOS 钥匙串里读（`security find-generic-password -s DEEPSEEK_API_KEY -w`），只放进那一条命令的环境变量。不要写进任何文件（包括 `.env`、脚本、日志、`tmp/` 里的原始输出），也不要打印出来。原始输出存盘前查一遍，确认里面没有 key。
- **Claude 那几组**：用用户的订阅登录跑 `claude -p`，不要设 `ANTHROPIC_API_KEY`（设了就会改成按 API 付钱）。
- **在哪跑**：在本目录里跑，不要在 `[PRIVATE_SOURCE_DIR]` 里跑；加 `--setting-sources project,local`，不加载用户级的 hook。
- **我们自己的题**：从 `[PRIVATE_SOURCE_DIR]` 里挑。不要读、也不要搜 `[PRIVATE_SOURCE_DIR]`，用 `grep -r` 时加 `--exclude-dir=[PRIVATE_SOURCE_DIR]`。
- **公开题集**：Chinese SimpleQA 是 CC BY-NC-SA 4.0 授权，题目原文不要发到网上。
- **判分**：判分模型不能知道答案出自哪一组。
- **结果存放**：正式运行的原始输出和判分结果都写进 `tmp/archive/jsonl/`，复现信息写进 `tmp/archive/manifest.json`；试跑的放 `tmp/pilot/`。十组全部跑完、判完以后，才把 `tmp/archive/` 移到 `results/<跑的日期>/`；跑到一半的不要先移。原始输出不删，要留着做开源前检查（README 的“结果怎么存”和“开源前检查”）。`tmp/` 不进 git。
- **不要自己公开**：开源前检查由用户确认，不要自己推送到 GitHub 或发到别处。
- **记日志**：每一步做了什么、踩了什么坑，记进 `日志.md`。
- **语言**：文档和回复都用中文。
- **沙箱**：要放行网络（DeepSeek API、Claude Code）和钥匙串读取（`security`），不然跑不起来。
