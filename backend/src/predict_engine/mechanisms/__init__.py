"""predict_engine/mechanisms/ —— 预测机制子模块。

当前阶段：所有机制定义仍在 predict/mechanisms.py 中。
后续拆分计划：
  static_rules.py  — 静态规则（生肖、五行、头尾、单双等固定映射）
  dynamic_rules.py — 动态规则（文字历史映射、标题配置生成）
  parsers.py       — 内容解析器（jiexi、tail_code、xiao_code 等）
  formatters.py    — 输出格式化（format_* 系列函数）
  loaders.py       — 内容加载器（loaders, outcome builders）
  status.py        — 机制状态管理
"""

from __future__ import annotations
