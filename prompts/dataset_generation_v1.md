你为一个合成中文客服对话研究写单条顾客退货申请。每次请求是独立的；只使用本次给出的事实与语言要求。

只输出指定 JSON：customer_message 为自然的简体中文顾客消息；english_annotation 为忠实英文翻译，仅供研究者阅读；proposed_evidence 为四个事实字段在中文消息中的逐字证据片段数组。

事实约束必须全部保持，不添加新的退货理由或改变商品状态。ordinary_return 使用给定的普通退货理由；quality_or_fulfillment_issue 根据给定问题描述明确说明问题来自收货时已有瑕疵、错发或运输损坏；not_stated 只提出退货请求，不给出真正退货原因。普通退货中的 damage_or_stain=present 应表达收货后顾客使用/保管造成的污损，不能改写为收货时已损坏。

tag_status=attached 表达吊牌仍完整连接；removed 表达已剪掉或拆掉。damage_or_stain=absent 明确无污渍、无破损。use_beyond_inspection=no 表达仅合理试穿/检查，没有穿出去使用；yes 明确超出试穿的使用。

对 unknown，根据 uncertainty_expression 要求省略该事实，或明确表达不知道/不确定。省略时该字段证据必须为 []；明确不确定时保留对应原文片段。对 conflicting，写出两个针对同一当前商品状态的互不相容说法，保持矛盾未解决；不是已经解释清楚的时间变化，也不是明确更正旧说法。证据必须给出两个不同的片段。

中文消息只写顾客话语，不包含研究标记、分类名称、政策结果、编号、分析、JSON 外的说明或英文翻译。不输出客服回应。证据必须为 customer_message 的非空逐字子串，不翻译、不概括、不拼接。

按指定 tone、difficulty 和语言特征自然组织消息。easy 保持事实直接清晰；medium 有一项语言挑战；hard 有多项挑战但不得使本应清晰的事实变得不确定。语言特征不得覆盖必需事实约束。长度范围是近似目标，优先保持事实完整。可自然变化句式、服装种类和无关背景，避免固定开头与重复模板。
