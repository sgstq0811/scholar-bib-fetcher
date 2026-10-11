# Google Scholar BibTeX Fetcher

从 UTF-8 文本文件读取论文标题（每行一个），通过独立的 Chrome profile 搜索 Google Scholar，并把严格匹配的 BibTeX 合并到一个文件中。

标题会先统一小写，并归一化 Unicode、标点和多余空格；归一化后的相似度超过 `0.99` 即视为同一篇论文并自动写入 BibTeX。搜索时先使用普通标题查询，再以带引号的精确短语作为回退；每次查询扫描前 10 条结果并选择相似度最高的标题，而不是只看第一条。

## 安装

本机需要安装 Python 3.11+ 和 Google Chrome。工具只使用项目自己的 profile，不读取或关闭日常 Chrome。

```bash
git clone https://github.com/sgstq0811/scholar-bib-fetcher.git
cd scholar-bib-fetcher
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

## 输入

创建一个文本文件，例如 `papers.txt`：

```text
Attention Is All You Need
BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding
```

空行会被忽略；归一化后重复的标题只处理第一次出现的位置。

汇总说明行 `Qwen-related / Omni-related references above account for the remaining unique merged entries after title normalization.` 会被直接忽略，不进入搜索或未匹配报告。

## 运行

```bash
scholar-bib papers.txt --output references.bib
```

默认配置：

- 独立浏览器 profile：`work/browser-profile`
- 网络连接：默认直接访问；可通过 `--proxy` 或 `SCHOLAR_BIB_PROXY` 配置代理
- 随机等待：每篇论文之间 3–7 秒
- 未匹配报告：`unmatched.tsv`
- 断点文件：`progress.jsonl`

例如使用 SOCKS5 代理：

```bash
export SCHOLAR_BIB_PROXY='socks5h://127.0.0.1:12377'
scholar-bib papers.txt --output references.bib
```

也可以只对单次运行传入代理：

```bash
scholar-bib papers.txt --proxy 'socks5h://127.0.0.1:12377'
```

完全后台运行：

```bash
scholar-bib papers.txt --headless
```

如果后台运行时 Google Scholar 要求人工验证，工具会停止且不把当前标题写入 checkpoint。然后去掉 `--headless`，使用相同参数继续：

```bash
scholar-bib papers.txt
```

可见模式下若出现验证页面，请在独立 Chrome 窗口内完成验证，再回到终端按回车。工具不会自动绕过验证码。

如果 Scholar 返回“unusual traffic”，或显示 “We're sorry / may be sending automated queries / can't process your request right now”，工具会以退出码 4 停止，不会把当前标题误记为“无结果”。这种情况需要等待限流解除或通过 `--proxy` 更换代理出口。

断点续跑默认开启：checkpoint 已存在时会自动跳过已完成条目，并自动重试之前的普通错误和 `no_result`。旧 checkpoint 中相似度超过 `0.99`、但按旧规则记为 `unmatched` 的条目也会重新抓取。输出文件只使用当前输入列表中的有效标题，因此旧 checkpoint 内已经忽略或删除的条目不会继续出现在 `unmatched.tsv`。`--resume` 仍可使用，但不再需要显式填写；`--no-resume` 可关闭自动恢复，此时若 checkpoint 已存在，工具会要求改用新的 checkpoint 文件。

## 输出

- `references.bib`：所有成功获取的 BibTeX，重复条目只保留一次。
- `unmatched.tsv`：输入标题、Scholar 首条标题、相似度和失败原因。
- `progress.jsonl`：增量写入的断点记录；中断后可以恢复。

每个不一致项都会立即打印到终端。单篇论文出错不会阻止后续论文，并会在下次运行时自动重试；验证码除外，因为它需要用户决定是否切换到可见模式。

## 常用选项

```bash
scholar-bib --help
scholar-bib papers.txt \
  --output my-library.bib \
  --unmatched my-unmatched.tsv \
  --checkpoint work/my-progress.jsonl \
  --profile-dir work/my-scholar-profile \
  --delay-min 5 \
  --delay-max 12
```

## 测试

纯逻辑测试：

```bash
python -m pytest -m 'not browser' -v
```

包括本地 Chrome DOM 测试：

```bash
python -m pytest -v
```

Google Scholar 可能限流或调整页面结构，因此大量任务无法保证完全无人值守。如果页面结构变化，浏览器选择器集中在 `scholar_bib/scholar.py` 中。

## 负责任地使用

本工具面向个人研究资料整理。请控制查询频率，并遵守 Google Scholar、网络运营方及所在地区的适用规则。工具不会绕过验证码；检测到验证页面或 unusual-traffic 限流时会停止，并保留断点供稍后恢复。不要用它规避访问限制或进行大规模抓取。

## License

[MIT](LICENSE)
