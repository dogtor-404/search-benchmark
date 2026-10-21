# 题库与本地恢复

第一轮原100题库中25道Chinese SimpleQA题干不公开。先运行 `python3 tools/restore_first_round.py` 从固定revision下载并校验SHA256，再本地恢复questions.jsonl；可用 `--cache /path/to/chinese_simpleqa.jsonl` 离线恢复。该文件不提交。答案、别名、原始作答和复核理由仍可能透露答案或题意。

原100题和120题题库不因后续筛题改变；当前92/95题由[固定排除清单](../results/2026-10-21-revised-92-95/policy.json)确定。许可及上游署名见[LICENSE](LICENSE)、[NOTICE](NOTICE)与[MSQA上游说明](upstream/msqa-README.md)。恢复不意味着重新纳入被排除题。
