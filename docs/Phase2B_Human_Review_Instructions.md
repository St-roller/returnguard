# ReturnGuard Phase 2B — 人工审核操作

## 当前状态

180 次 DeepSeek 调用已经完成，dev/test 各 90。当前所有案例都是 pending；尚未建立 frozen gold，也没有正式评估或 acceptance threshold。

## 文件

- `data/returnguard_synth_v1/construction/human_review.html`：可离线打开的人工审核页面，内含全部蓝图、中文消息、英文注释、建议证据和审计结果。
- `construction/raw_dev.jsonl.gz` / `raw_test.jsonl.gz`：完整原始请求/响应，gzip 无损压缩。
- `construction/provenance_dev.json` / `provenance_test.json`：实际生成设置与来源哈希。
- `construction/draft_audit_report.json`：当前草稿审计，状态为 pending_human_review。

## 操作顺序

1. 下载 HTML，用本地浏览器打开，输入实际审核人姓名。
2. 逐例阅读蓝图和中文消息，检查 13 项。English annotation 只帮助阅读，不能代替中文。
3. 修订表达或证据时，保持该蓝图 intended facts、订单事实、reason family、difficulty、length、tone、features 与 composition。证据每行一个，必须是原文连续子串。消息缺失某个明确事实时，需要补充消息，不能凭蓝图直接把不支持的事实当作 gold。
4. `unknown + []` 表示遗漏；明确不确定需要相应中文证据；`conflicting` 需要两条尚未解决的真实矛盾，不是已纠正的旧说法。
5. 6 条截断响应需要按原蓝图人工补全，页面展示截断的原始 content 供参考；原始失败记录仍保留。无需重新调用模型来获得更好案例。
6. 完成一例后点击“批准当前案例”。未读完不得批准；不能批量代替人工审核。
7. 定期“导出审核 JSON”备份。浏览器本地保存仅是便利功能，导出的 JSON 才是交回 Work 的审核凭证。
8. 消息有修改时，先将 JSON 交回 Work 重新生成审计页；重新打开页面，审查更新后的相似对、输入疑似词、英文注释与按 route 分组的格式特征。
9. 相似案例如果确实独立，填写具体理由并确认 distinct；如果重复则修订并重新审计。不同消息的旧 pair_id 不能沿用。
10. 180 例 individually approved、当前相似对已解决、当前审计已人工确认后，再由 Work 验证证据和 Policy v1，并生成最终数据与冻结记录。

## 当前需要注意

- 6 个未解析案例：`dev_008`, `dev_014`, `dev_053`, `test_015`, `test_033`, `test_054`。
- 56 例有自动预检查问题（dev 23 / test 33，包含上面 6 例）。其余案例也需要人工检查语义和设计实现，自动通过不等于人工通过。
- 174 条非空可解析消息：精确重复 0；相似对 11，其中 dev 内 5、test 内 1、跨 split 5。
- 4 个中文“标签”词警示：`test_023`, `test_036`, `test_047`, `test_081`。需要判断是普通商品标签表达还是生成器痕迹。
- 这些是当前草稿结果，修订后重新计算；不能当作最终冻结审计结论。

## 返还给 Work

上传页面导出的 `returnguard_human_reviews.json`。仅口头“同意”不会替代 180 例实际阅读、证据修订和个人审核记录。
