# ReturnGuard Phase 2B — 数据集级批准前交付包

**状态：READY_FOR_DATASET_LEVEL_APPROVAL**。等待项目作者/设计权威对本快照作 go/no-go 决定；数据集尚未冻结。

执行依据为本轮附件交接文档第 24–25 节。从现有 PR #3 的 `phase2b-generation-review-v1` 分支、head `1c9555a59a30265c223241e970a0f9bccae22aed` 继续，保留原始生成响应、来源记录、原草稿审计及已批准蓝图。当前病例数、策略、schema、目标与配额未改变。

## 1. 审查汇总

| 项目 | 数量 |
|---|---:|
| 逐案审查 | 180 |
| 案例级批准 | 180 |
| 至少一项文本/证据/注释修改 | 160 |
| 无修改 | 20 |
| 截断补全 | 6 |
| 证据更新 | 151 |
| 语义/事实实现修复 | 116 |
| 长度等语言实现修复 | 93 |
| 英文注释更新 | 160 |
| 原注释不一致 | 2 |
| 近重复相关改写案例 | 13 |
| 最终 accepted_distinct 对 | 1 |
| 拒绝案例 | 0 |

各修复类别重叠，不能相加作为修复总数。英文更新包括跟随中文修复更新译文；原注释本身过度解读为 2 例。56 个原预检问题案例和 124 个未报警案例均逐案检查；160 个修复案例中 104 个来自未报警组。审查涵盖全部 13 项，自动通过未被当作语义批准。

审查方法为 `structured_case_review_v1.1`。每案记录具体说明、问题、修复、精确证据、时区时间戳与内容哈希；没有虚构个人审核人，也没有声称作者亲自检查了全部案例。源生成器为 **DeepSeek V4 Pro 0813 / `deepseek/deepseek-v4-pro-0813`，dev 与 test 均为此模型**。正式被评估模型仍为后续 `openai/gpt-5.6-luna`。

## 2. 问题分布

| 类别 | 案例数 |
|---|---:|
| 原英文注释过度解读 | 2 |
| 无效或不充分的冲突表达 | 8 |
| 证据虽逐字匹配但语义不支持 | 39 |
| 未表达冻结质量问题家族 | 3 |
| 长度/难度/语气/语言特征实现不足 | 93 |
| 污渍/破损事实或证据支持不足 | 58 |
| 缺失与明确不确定不匹配 | 3 |
| 原因事实或证据支持不足 | 12 |
| 吊牌事实或证据支持不足 | 8 |
| 超出检查使用事实或证据支持不足 | 19 |
| 需改写表述的近重复案例 | 13 |
| 与冻结 reason family 不一致 | 22 |
| 生成响应截断 | 6 |
| 原因缺失案例实际陈述或暗示原因 | 7 |
| 模型可见生成器/route/rule 泄漏 | 0 |

## 3. 最终审计

| 检查 | 结果 |
|---|---|
| 案例/非空消息 | 180 / 180 |
| 精确证据验证 | 180 / 180 |
| 原 Policy v1 route/rule 重算吻合 | 180 / 180 |
| 既定长度范围吻合 | 180 / 180 |
| 精确重复 | 0 |
| 最终近重复 | 1，全部已处理 |
| 跨 split 近重复 | 1，accepted_distinct |
| 模型可见 route/rule 泄漏 | 0 |
| 生成请求标签泄漏 | 0；180 个请求均扫描 |
| 当前中文软词警示 | 2：test_023、test_036 的自然服装“标签” |
| 英文注释警示 | 0；英文不进入模型输入 |
| 原始来源完整性 | 9 个受保护文件哈希未变 |
| 正式 GPT 评估调用 / 阈值选择 | 0 / 未选择 |

原 4 个中文软标记中，test_023 和 test_036 保留自然服装用词；test_047 因缺失/不确定语义修复移除相关句，test_081 因原因家族与真实缺失修复移除标签元说明。没有将普通服装“标签”视为 route 泄漏。原响应中的 4 个同类软词匹配仍保留在来源审计中，不是模型可见输入。

按 route 的格式统计：

| route | n | 平均字数 | 平均句数 | 平均标点数 | 平均 emoji 数 |
|---|---:|---:|---:|---:|---:|
| eligible | 60 | 52.55 | 2.13 | 7.35 | 0.0 |
| ineligible | 60 | 54.67 | 2.33 | 7.3 | 0.0 |
| manual_review | 60 | 55.1 | 2.38 | 7.58 | 0.0 |

每 split 的难度/长度 30/30/30 及路线 30/30/30 配额沿用蓝图。一个六字符常见开头 `你好,我想申` 出现在 6 案，跨 eligible、ineligible、manual_review 三类；完整常见句“你好，我想申请退货”出现在 4 案，亦跨三类。未发现明显格式标签暗示。这是审查/审计结果，不代表共享合成风格风险已被统计排除。

原 11 对近重复均经表述修复消除；第二轮另有 3 对新增相似标记经改写消除。最终保留 dev_052 / test_085，sequence ratio 0.81818、char3 Jaccard 0.29032：前者明确剪掉吊牌，走 IN03_NOT_INTACT/ineligible；后者完全缺失吊牌信息，走 MR02_CONDITION/manual_review。两者有不同条件/composition 与语气句式，重合来自短请求和共享状态词。完整逐对历史在 `construction/near_pair_review_history.json`，过期 pair_id 仅作为历史，不用于批准当前文本。

模型可见消息及英文审计快照 SHA-256：

`6bc97f310cffef6b62c32e473455bb7c60766479521d6d1d96758db94681977a`

包含 gold、证据及审查元数据的候选记录 SHA-256：

`722859cd31057e570e074e6f7c910d8a09fec38fd0b4b5390a2377bac3c98860`

候选文件 SHA-256：

| 文件 | SHA-256 |
|---|---|
| reviewed_candidate_dev.jsonl | `39943bdf053298dc3a9e6c45b58d6b6d06fb136fc1e5c30519b5de62e6c14c70` |
| reviewed_candidate_test.jsonl | `9b3fe0451253d089923c42ca5071684ad3c9d1d5ce3ab6814a0af9bc9a511933` |

## 4. 十个代表案例

以下展示 2 个无修改、2 个证据修复、2 个语义修复、2 个近重复相关、2 个截断补全。完整订单事实、设计约束、前后英文与 gold 位于 `construction/representative_cases.json`。

### dev_011 — clean/no-change

蓝图：EL01_7DAY / eligible；reason family=duplicate_purchase；composition=base。

修复前：您好，我5月23日收到的这件衬衫，吊牌还完整挂着，也没有污渍或破损。我只在家里试穿了一下，没有穿出门。因为朋友也送了一件一样的，想申请退货，麻烦您了。

问题：无。逐案确认文本、证据、设计实现与注释均有效。

修复后：您好，我5月23日收到的这件衬衫，吊牌还完整挂着，也没有污渍或破损。我只在家里试穿了一下，没有穿出门。因为朋友也送了一件一样的，想申请退货，麻烦您了。

Gold extraction / exact evidence：

```json
{
  "return_reason": {
    "value": "ordinary_return",
    "evidence": [
      "朋友也送了一件一样的"
    ]
  },
  "tag_status": {
    "value": "attached",
    "evidence": [
      "吊牌还完整挂着"
    ]
  },
  "damage_or_stain": {
    "value": "absent",
    "evidence": [
      "没有污渍或破损"
    ]
  },
  "use_beyond_inspection": {
    "value": "no",
    "evidence": [
      "只在家里试穿了一下",
      "没有穿出门"
    ]
  }
}
```

重算：EL01_7DAY / eligible。

审查说明：Same shirt gifted by a friend supports duplicate purchase. Fully attached tag, no stains/damage and home-only trial have exact spans. Receipt date matches trusted facts; polite long message includes unrelated date detail.

### dev_025 — clean/no-change

蓝图：EL02_BRAND14 / eligible；reason family=preference_mismatch；composition=base。

修复前：你好，我想申请退货，这件衣服不太适合我。吊牌还在，没有污渍和破损，只是试穿了一下。

问题：无。逐案确认文本、证据、设计实现与注释均有效。

修复后：你好，我想申请退货，这件衣服不太适合我。吊牌还在，没有污渍和破损，只是试穿了一下。

Gold extraction / exact evidence：

```json
{
  "return_reason": {
    "value": "ordinary_return",
    "evidence": [
      "不太适合我"
    ]
  },
  "tag_status": {
    "value": "attached",
    "evidence": [
      "吊牌还在"
    ]
  },
  "damage_or_stain": {
    "value": "absent",
    "evidence": [
      "没有污渍和破损"
    ]
  },
  "use_beyond_inspection": {
    "value": "no",
    "evidence": [
      "只是试穿了一下"
    ]
  }
}
```

重算：EL02_BRAND14 / eligible。

审查说明：Personal suitability supports ordinary preference mismatch, not a defect allegation. Attached tag, absence of both stains and damage, and exclusive trial are exact contiguous evidence; polite/direct medium wording and translation agree.

### dev_001 — evidence repair

蓝图：EL01_7DAY / eligible；reason family=size_fit；composition=base。

修复前：这件衣服尺码不合适，想申请退货，吊牌还在，没有污渍，只试穿了一下。

问题：Text or proposed evidence did not support absence/presence of both damage and stain.；Template similarity required varied surface wording while preserving all frozen facts.

修复后：这件尺码不合适想退，吊牌还在，没脏没破，只试穿了一下。

Gold extraction / exact evidence：

```json
{
  "return_reason": {
    "value": "ordinary_return",
    "evidence": [
      "尺码不合适"
    ]
  },
  "tag_status": {
    "value": "attached",
    "evidence": [
      "吊牌还在"
    ]
  },
  "damage_or_stain": {
    "value": "absent",
    "evidence": [
      "没脏没破"
    ]
  },
  "use_beyond_inspection": {
    "value": "no",
    "evidence": [
      "只试穿了一下"
    ]
  }
}
```

重算：EL01_7DAY / eligible。

审查说明：Original no-stain span did not exclude damage; made both explicit within short/direct constraints. Its original near-duplicate flag was resolved by the recorded surface changes; the final pair is re-audited under new content hashes.

### dev_019 — evidence repair

蓝图：EL02_BRAND14 / eligible；reason family=preference_mismatch；composition=base。

修复前：你好，这件衣服不太适合我，想申请退货，吊牌还在，没有污渍，只试穿了一下。

问题：Text or proposed evidence did not support absence/presence of both damage and stain.；Template similarity required varied surface wording while preserving all frozen facts.

修复后：你好，这件衣服不合我喜好，想申请退货。吊牌还在，没有污渍或破损，只试穿了一下，请帮我办理。

Gold extraction / exact evidence：

```json
{
  "return_reason": {
    "value": "ordinary_return",
    "evidence": [
      "不合我喜好"
    ]
  },
  "tag_status": {
    "value": "attached",
    "evidence": [
      "吊牌还在"
    ]
  },
  "damage_or_stain": {
    "value": "absent",
    "evidence": [
      "没有污渍或破损"
    ]
  },
  "use_beyond_inspection": {
    "value": "no",
    "evidence": [
      "只试穿了一下"
    ]
  }
}
```

重算：EL02_BRAND14 / eligible。

审查说明：Expanded stain-only statement to exclude damage too; made preference mismatch explicit and kept polite medium/direct style. Its original near-duplicate flag was resolved by the recorded surface changes; the final pair is re-audited under new content hashes.

### dev_073 — semantic repair

蓝图：MR03_REASON / manual_review；reason family=not_stated；composition=otherwise_intact。

修复前：这件衣服我5月9号收到的，试了一下不太合适，吊牌还在，想退掉。

问题：Text supplied or implied a causal reason despite frozen not_stated intent.；Text or proposed evidence did not support absence/presence of both damage and stain.；Length/tone/difficulty or required language feature was not fully realized.

修复后：这件衣服5月9号收到的，只有拆包检查，吊牌还在，没脏没破。盒子放在书架边，昨晚还找了半天，能帮它安排回去吗？

Gold extraction / exact evidence：

```json
{
  "return_reason": {
    "value": "not_stated",
    "evidence": []
  },
  "tag_status": {
    "value": "attached",
    "evidence": [
      "吊牌还在"
    ]
  },
  "damage_or_stain": {
    "value": "absent",
    "evidence": [
      "没脏没破"
    ]
  },
  "use_beyond_inspection": {
    "value": "no",
    "evidence": [
      "只有拆包检查"
    ]
  }
}
```

重算：MR03_REASON / manual_review。

审查说明：Removed actual does-not-fit reason from not_stated realization; retained unrelated date/box detail and indirect neutral hard request.

### dev_083 — semantic repair

蓝图：MR02_CONDITION / manual_review；reason family=duplicate_purchase；composition=contradiction。

修复前：您好，这件衣服我收到了，朋友也送了一件一样的，所以想退掉，5月12号签收的。试穿了一下，没有污渍破损；不过吊牌刚要拆还没拆，另一个衣架上的吊牌还在衣服上。

问题：Conflict spans were compatible, resolved, hedged, about different items, or missing.；Verbatim span existed but did not semantically support the intended value.

修复后：您好，朋友也送了一件一样的，这件怕是多出来了，能收回吗？5月12号签收，只试穿，没污渍破损。现在这件的吊牌完整连着；现在这件的吊牌已经剪下。两句话我都确认，但暂时解释不了，没法把其中一句改掉。

Gold extraction / exact evidence：

```json
{
  "return_reason": {
    "value": "ordinary_return",
    "evidence": [
      "朋友也送了一件一样的，这件怕是多出来了"
    ]
  },
  "tag_status": {
    "value": "conflicting",
    "evidence": [
      "现在这件的吊牌完整连着",
      "现在这件的吊牌已经剪下"
    ]
  },
  "damage_or_stain": {
    "value": "absent",
    "evidence": [
      "没污渍破损"
    ]
  },
  "use_beyond_inspection": {
    "value": "no",
    "evidence": [
      "只试穿"
    ]
  }
}
```

重算：MR02_CONDITION / manual_review。

审查说明：Original two spans both meant attached and referred to different items. Rewrote as two unresolved present-state assertions about the same item, preserving tag conflict and indirect duplicate reason.

### dev_017 — near-duplicate-related

蓝图：EL02_BRAND14 / eligible；reason family=no_longer_needed；composition=base。

修复前：这件衣服我不需要了，吊牌还在。没有污渍和破损，只试穿过。

问题：Template similarity required varied surface wording while preserving all frozen facts.

修复后：用不上这条裤子了。只试穿；吊牌连着，布面没脏没破，想退。

Gold extraction / exact evidence：

```json
{
  "return_reason": {
    "value": "ordinary_return",
    "evidence": [
      "用不上这条裤子了"
    ]
  },
  "tag_status": {
    "value": "attached",
    "evidence": [
      "吊牌连着"
    ]
  },
  "damage_or_stain": {
    "value": "absent",
    "evidence": [
      "布面没脏没破"
    ]
  },
  "use_beyond_inspection": {
    "value": "no",
    "evidence": [
      "只试穿"
    ]
  }
}
```

重算：EL02_BRAND14 / eligible。

审查说明：Reordered the short multi-sentence realization and used trousers/fabric context to break the near-duplicate cluster without changing facts.

### test_034 — near-duplicate-related

蓝图：IN01_CUSTOM / ineligible；reason family=changed_mind；composition=custom_only。

修复前：您好，这件定制衣服我不太想要了，吊牌还在，也没有污渍破损，只试穿过。

问题：Template similarity required varied surface wording while preserving all frozen facts.

修复后：您好，我改主意不留这件定制上衣了，想退。只在家试过，布料没脏没破，领口的吊牌还连着，麻烦办理。

Gold extraction / exact evidence：

```json
{
  "return_reason": {
    "value": "ordinary_return",
    "evidence": [
      "我改主意不留这件定制上衣了"
    ]
  },
  "tag_status": {
    "value": "attached",
    "evidence": [
      "领口的吊牌还连着"
    ]
  },
  "damage_or_stain": {
    "value": "absent",
    "evidence": [
      "布料没脏没破"
    ]
  },
  "use_beyond_inspection": {
    "value": "no",
    "evidence": [
      "只在家试过"
    ]
  }
}
```

重算：IN01_CUSTOM / ineligible。

审查说明：Reordered source template and used top/fabric/collar context to resolve similarity flags while retaining easy polite medium changed-mind custom case.

### dev_008 — formerly truncated

蓝图：EL01_7DAY / eligible；reason family=colour_style；composition=base。

修复前：（未能解析完整消息；原始失败响应仍保留。）

问题：Generation response truncated; surface/annotation/evidence incomplete.

修复后：收到后只在家对着镜子试了一下，根本没穿出门，吊牌也一直完整挂在衣服上，没有污渍、没有破损。不是我想挑剔，但这件的颜色不是我想要的那种，实在不喜欢，想申请退货。

Gold extraction / exact evidence：

```json
{
  "return_reason": {
    "value": "ordinary_return",
    "evidence": [
      "颜色不是我想要的那种，实在不喜欢"
    ]
  },
  "tag_status": {
    "value": "attached",
    "evidence": [
      "吊牌也一直完整挂在衣服上"
    ]
  },
  "damage_or_stain": {
    "value": "absent",
    "evidence": [
      "没有污渍、没有破损"
    ]
  },
  "use_beyond_inspection": {
    "value": "no",
    "evidence": [
      "只在家对着镜子试了一下，根本没穿出门"
    ]
  }
}
```

重算：EL01_7DAY / eligible。

审查说明：Retained the usable original partial message; completed the color-preference reason with frustrated non-trivial negation. All four definitive facts now have exact support.

可用原始截断片段（保留来源）：

```text
{
  "customer_message": "收到后只在家对着镜子试了一下，根本没穿出门，吊牌也一直完整挂在衣服上，没有污渍、没有破损
```

### test_033 — formerly truncated

蓝图：IN01_CUSTOM / ineligible；reason family=preference_mismatch；composition=custom_only。

修复前：（未能解析完整消息；原始失败响应仍保留。）

问题：Generation response truncated; surface/annotation/evidence incomplete.

修复后：6月22号收到的这件定制衣服，等了这么久，我本来想留，但试穿后越看越不喜欢，算了，还是不留了，不是我的风格。吊牌还完整挂着，没污渍也没破，就只在家试了试。现在不太想要了，能帮我安排退回吗？实在喜欢不起来。

Gold extraction / exact evidence：

```json
{
  "return_reason": {
    "value": "ordinary_return",
    "evidence": [
      "不是我的风格"
    ]
  },
  "tag_status": {
    "value": "attached",
    "evidence": [
      "吊牌还完整挂着"
    ]
  },
  "damage_or_stain": {
    "value": "absent",
    "evidence": [
      "没污渍也没破"
    ]
  },
  "use_beyond_inspection": {
    "value": "no",
    "evidence": [
      "就只在家试了试"
    ]
  }
}
```

重算：IN01_CUSTOM / ineligible。

审查说明：Recovered the complete Chinese message from the truncated JSON response and completed its annotation/evidence. Self-correction and indirect preference mismatch remain; custom-only semantics preserved.

可用原始截断片段（保留来源）：

```text
{
  "customer_message": "6月22号收到的这件定制衣服，等了这么久，我本来想留，但试穿后越看越不喜欢，算了，还是不留了，不是我的风格。吊牌还完整挂着，没污渍也没破，就只在家试了试。现在不太想要了，能帮我安排退回吗？实在喜欢不起来。",
  "english_annotation": "I received this custom-made item on June 22. After waiting so long, I originally wanted to keep it, but after trying it on, the more I looked at it
```

## 5. 课程要求与后续报告一致性

参考材料仅用于一致性核对，不重启设计。旧内容与冻结决策冲突时，以下列出差异并保持冻结实现。

| 来源/要求 | 差异或约束 | 报告处理 |
|---|---|
| 教师后续直接反馈 vs 旧时间表 | 后续反馈说 4 October；旧表写 20 September 2026 | 提交日期采用 2026-10-04；后续反馈未给出精确时间，不据此虚构时间 |
| 旧提案模型网关与 SDK | 旧提案偏向直接 OpenAI Responses SDK；冻结生成器/后续评估模型采用已记录的 OpenRouter ID | 报告实际 provider/model/run provenance；不回退网关或模型 |
| 旧提案只命名 held-out 生成器 | 教师指出 dev 生成模型未命名 | 明确 dev/test 均为 DeepSeek V4 Pro 0813，记录分离 job 和设置 |
| 旧提案个人手动核查措辞 | 新交接为结构化逐案审查，作者做数据集级批准 | 使用真实的结构化审查表述；批准后才可写作者批准最终数据集 |
| 旧提案 null、原始/去泄漏两版测试 | 冻结 schema 为 unknown/not_stated/conflicting；当前执行方案是单一受审查基准 | 记录设计演进，不添加 null 或额外测试集，不倒改冻结决策 |
| 90 个 dev、90% selective accuracy | 教师强调小样本估计不稳定 | 后续报告先给计数再给比例，阈值称 provisional，锁定后不做 test 调参 |
| OWASP 版本与风险篇幅 | 旧提案/课程 companion 引用 2025；教师要求核对 2026 | 最终报告按教师要求核对官方 2026 名称/编号与出处；本阶段不凭空替换编号，不扩大安全范围 |
| Rubric 1：15% | 问题、用户、范围现实性 | 保持内部门店服装退货初筛；场景工时/订单数是明确假设，不包装成实测 |
| Rubric 2：25% | 商业与技术取舍 | 保留一调用抽取 + 确定规则、own/rent 理由、实际使用成本与限制；不作生产精度保证 |
| Rubric 3：35% | 数据、实现、评估、可复现 | 本包完成审查与审计；正式评估/基线仍为批准与冻结之后的工作，不提前声称有成绩 |
| Rubric 4：25% | 演示与沟通，明确限制 | 后续录制 demo/video；最终分析 ≤1,200 words。共享生成器风格和小样本限制需表达清楚 |
| 教师课程覆盖反馈 | 1、2、3、5、6 已覆盖，4 已说明不适用 | 保留无 agent/tool loop 的适配理由；风险工作保持比例，无退款/真实客户数据/外部操作 |

上述日期、OWASP 与方案演进属于来源/叙述差异，不是本轮数据集批准阻塞项。OWASP 官方版本核对、正式 metrics、基线、报告与视频属于后续阶段，不在本轮宣布完成。

## 6. 可复核文件与批准边界

全部产物位于当前 PR #3：`structured_reviews.json`、候选 dev/test、`review_summary.json`、`final_review_audit.json`、10 案例、逐对历史、来源哈希和可选离线审查页。运行 `python scripts/check_review_readiness.py` 可重验明确案例记录、来源、长度、证据和 Policy v1。自动校验验证结构与规则；真实语义审查的凭证是逐案说明与修改记录。

当前没有 root `dev.jsonl`、`test.jsonl` 或 `freeze_manifest.json`；正式 GPT 评估调用仍为 0，阈值未选择。冻结需要项目作者/设计权威对上列具体快照作最终批准，并向冻结工具提供可追溯批准记录。依交接第 24 节 Step 8 停在此处。
