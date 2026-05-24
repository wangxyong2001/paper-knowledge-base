# 问题清单

> 论文知识库向量数据库系统 SIT测试问题追踪

## 最终测试结果

| 统计项 | 数量 |
|--------|------|
| 总测试数 | 20 |
| 通过 | 20 |
| 失败 | 0 |
| 错误 | 0 |
| 通过率 | 100.0% |

**状态**: 所有问题已修复，测试全部通过。

---

## 问题 #1: BM25索引中文搜索失败 [已修复]

### 问题描述

**测试名称**: `test_bm25_index_write_read`

**原始错误信息**:
```
AssertionError: 0 not greater than 0
```

### 问题原因

Whoosh库默认使用英文分词器，对中文文本按空格分词。由于中文文本没有空格分隔，导致无法进行有效的关键词检索。

### 解决方案

**已实施修复**:

1. 安装jieba中文分词库
2. 在测试中使用ChineseAnalyzer
3. 更新add_paper.py使用ChineseAnalyzer

**修复代码**:
```python
from jieba.analyse import ChineseAnalyzer

schema = Schema(
    content=TEXT(stored=True, analyzer=ChineseAnalyzer()),
    paper_title=TEXT(stored=True, analyzer=ChineseAnalyzer()),
)
```

### 修复验证

```
[PASS] BM25索引读写: 搜索返回1条（使用ChineseAnalyzer）
```

### 状态

- [x] 问题识别
- [x] 原因分析
- [x] 解决方案设计
- [x] 代码修复
- [x] 测试验证

---

## 修复记录

| 日期 | 操作 | 结果 |
|------|------|------|
| 2026-05-24 | 安装jieba | 成功 |
| 2026-05-24 | 更新tests.py使用ChineseAnalyzer | 测试通过 |
| 2026-05-24 | 更新add_paper.py使用ChineseAnalyzer | 成功 |
| 2026-05-24 | 重新运行全部测试 | 100%通过 |

---

## 依赖更新

**新增依赖**:
```
jieba-0.42.1
```

**安装命令**:
```bash
pip install jieba
```