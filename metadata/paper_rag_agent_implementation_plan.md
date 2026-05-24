# 论文RAG系统专用Agent落地方案

> 基于hello-agents学习成果与当前RAG开发内容整合
> 日期: 2026-05-24

---

## 一、现状回顾

### 当前已完成的RAG核心模块

| 模块 | 文件 | 功能 | 状态 |
|-----|------|------|------|
| 数据库Schema | `database/schema.py` | 7表审计系统 | ✓ 完成 |
| Schema迁移 | `database/schema_migration.py` | v2扩展表 | ✓ 完成 |
| 审计日志 | `database/audit_logger.py` | 全流程审计 | ✓ 完成 |
| 注入防御 | `core/prompt_restructurer.py` | 5类攻击检测 | ✓ 完成 |
| 输出格式化 | `core/output_formatter.py` | Citation/Markdown | ✓ 完成 |
| 指标采集 | `core/metrics_collector.py` | 30+指标6层 | ✓ 完成 |
| API客户端 | `core/api_client.py` | DashScope集成 | ✓ 完成 |
| Agent框架 | `agents/paper_rag_agent.py` | LangGraph实现 | ✓ 完成 |
| 集成测试 | `tests/integration_test.py` | 全流程验证 | ✓ 通过 |

### hello-agents核心精华提取

**框架对比分析**:
| 框架 | 优势 | 适用场景 |
|-----|------|---------|
| **LangGraph** | 图结构、条件边循环 | 复杂工作流、反思-修正 |
| **HelloAgents** | 轻量、万物皆工具 | 教学、快速原型 |
| **AutoGen** | 对话驱动群聊 | 多角色协作 |
| **AgentScope** | 消息驱动分布式 | 大规模部署 |

**可复用的设计模式**:
- ReAct循环 (Thought-Action-Observation)
- Pipeline编排 (规划→执行→总结→报告)
- 记忆系统 (工作记忆 + 情景记忆)
- 工具注册表 (ToolRegistry统一接口)
- 降级策略 (LLM失败→模拟模式)
- 流式输出 (事件队列推送进度)

---

## 二、专用Agent落地方案

### 方案A: LangGraph增强方案（推荐）

**核心思路**: 保持当前LangGraph Agent框架，融合hello-agents的工具生态和记忆系统。

```
┌─────────────────────────────────────────────────────────────┐
│                    论文RAG Agent 架构                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────┐    ┌───────────────┐    ┌────────────┐   │
│  │ PaperRAGState │───▶│ LangGraph节点 │───▶│ ToolRegistry│   │
│  │ (StateGraph)  │    │ interpret     │    │ (融合设计) │   │
│  │               │    │ retrieve      │    │            │   │
│  │ query         │    │ grade_docs    │    │ VectorTool │   │
│  │ chunks        │    │ generate      │    │ SearchTool │   │
│  │ citations     │    │ reflect       │    │ TableTool  │   │
│  │ metrics       │    │ cite_check    │    │ PythonTool │   │
│  └───────────────┘    └───────────────┘    └────────────┘   │
│         │                    │                    │         │
│         ▼                    ▼                    ▼         │
│  ┌───────────────┐    ┌───────────────┐    ┌────────────┐   │
│  │ AuditLogger   │    │ MetricsCollect│    │ MemoryMgr  │   │
│  │ (SQLite审计)  │    │ (30+指标)     │    │ (新增模块) │   │
│  └───────────────┘    └───────────────┘    └────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**新增组件**:

1. **MemoryManager** - 借鉴HelloAgents第8章
```python
class PaperMemoryManager:
    """论文分析记忆管理器"""
    def __init__(self, session_id: str):
        self.working_memory = []  # 当前会话上下文
        self.episodic_memory = []  # 历史分析事件
        
    def add_episodic(self, paper_id: str, analysis: Dict):
        """记录论文分析历史"""
        self.episodic_memory.append({
            "paper_id": paper_id,
            "timestamp": datetime.now(),
            "summary": analysis.get("napkin_summary"),
            "key_points": analysis.get("core_concepts")
        })
        
    def retrieve_relevant(self, query: str) -> List[Dict]:
        """检索相关历史分析"""
        # 使用向量相似度检索
        pass
```

2. **ToolRegistry统一接口** - 借鉴YYHDBL-HelloCodeAgentCli
```python
class PaperToolRegistry:
    """论文分析工具注册中心"""
    def __init__(self):
        self.tools = {
            "vector_search": VectorSearchTool(chroma_client),
            "bm25_search": BM25SearchTool(whoosh_index),
            "table_extract": TableExtractTool(pdfplumber),  # 新增
            "python_exec": PythonExecTool(),  # 新增
            "citation_check": CitationCheckTool(),
            "hallucination_detect": HallucinationDetectTool(),
        }
    
    def execute(self, tool_name: str, params: Dict) -> Dict:
        """统一工具执行接口"""
        return self.tools[tool_name].run(params)
```

3. **StreamOutput进度推送** - 借鉴DeepResearch
```python
class PaperAnalysisStream:
    """论文分析进度流"""
    def __init__(self):
        self.event_queue = Queue()
        
    def emit(self, event_type: str, data: Dict):
        """推送进度事件"""
        self.event_queue.put({
            "type": event_type,
            "timestamp": datetime.now(),
            "data": data
        })
        
    # 事件类型: "retrieve_start", "retrieve_done", "generate_start", "generate_done", "quality_check"
```

---

### 方案B: CLI Agent交互方案

**核心思路**: 将当前RAG系统封装为交互式CLI，支持闲聊检测、历史回顾、Todo任务板。

```python
class PaperRAGCLI:
    """论文RAG命令行交互器"""
    
    def __init__(self):
        self.agent = PaperRAGAgent()
        self.memory = PaperMemoryManager()
        self.todo = TodoTool()  # 借鉴HelloCodeAgentCli
        self.audit = AuditLogger()
        
    def _is_chitchat(self, text: str) -> bool:
        """闲聊检测"""
        patterns = ["你好", "您好", "hello", "hi", "在吗"]
        return text.strip().lower() in patterns
        
    def _is_history_query(self, text: str) -> bool:
        """历史回顾检测"""
        patterns = ["刚才说了什么", "回顾", "之前分析了什么"]
        return any(p in text for p in patterns)
        
    def run_turn(self, user_input: str) -> str:
        """执行一轮对话"""
        # 闲聊直接回复
        if self._is_chitchat(user_input):
            return "你好！我是论文分析助手，可以帮你检索和解读论文内容。"
            
        # 历史回顾
        if self._is_history_query(user_input):
            return self._reply_with_recent_history()
            
        # 多步骤任务检测
        if "分步" in user_input or "计划" in user_input:
            self.todo.add_task(user_input)
            
        # 执行RAG Agent
        result = self.agent.run(user_input)
        
        # 记录审计
        self.audit.log_output(result)
        
        return result
```

---

## 三、专用Agent角色分工

### 角色1: PaperRetrievalAgent（检索专家）

**职责**: 专注于论文检索和召回优化
**工具**: VectorSearchTool, BM25SearchTool, RRF融合
**输出**: 检索结果 + 相关度评分 + 召回指标

### 角色2: PaperAnalysisAgent（解读专家）

**职责**: 论文深度解读、公式提取、中文通俗化
**工具**: FormulaExtractor, ContentTranslator, OutputFormatter
**输出**: 餐巾纸摘要 + 核心概念 + 公式解释 + 代码设计

### 角色3: QualityAssuranceAgent（质量专家）

**职责**: 幻觉检测、引用验证、支撑度评估
**工具**: HallucinationDetectTool, CitationCheckTool
**输出**: 质量评分 + 风险告警 + 修正建议

### 角色4: CodeReproductionAgent（复现专家）

**职责**: 论文代码复现设计、测试验证
**工具**: PythonExecTool, TestGenerator
**输出**: 代码模块 + 测试用例 + 运行结果

---

## 四、融合hello-agents共创项目

### healer-666-Academic-Data-Agent 融合点

**PDF表格提取增强**:
```python
# 在现有 vectordb/scripts/add_paper.py 中增强
from document_ingestion import extract_tables_from_pdf

def process_pdf_enhanced(pdf_path: str) -> Dict:
    # 原有文本处理
    text = _extract_text(pdf_path)
    chunks = _chunk_text(text)
    
    # 新增表格提取
    tables = extract_tables_from_pdf(pdf_path)
    table_chunks = _tables_to_chunks(tables)
    
    # 合并存储
    all_chunks = chunks + table_chunks
    return {"chunks": all_chunks, "tables": tables}
```

### haoye2-UniversalAgent 融合点

**多引擎网络搜索补充**:
```python
class WebSearchTool:
    """补充网络检索能力"""
    engines = ["duckduckgo", "brave", "ecosia", "searx"]
    
    def search(self, query: str) -> List[Dict]:
        """智能切换搜索引擎"""
        for engine in self.engines:
            try:
                results = self._search_with_engine(engine, query)
                if results:
                    return results
            except Exception:
                continue  # 降级到下一个引擎
        return []  # 所有引擎失败
```

---

## 五、落地实施步骤

### 第一阶段: 增强现有Agent（1周）

1. 在 `paper_rag_agent.py` 中添加MemoryManager
2. 创建 ToolRegistry 统一工具接口
3. 实现流式输出进度推送
4. 集成TableExtractTool（表格处理）

### 第二阶段: 专用Agent分工（2周）

1. 分离检索逻辑为 PaperRetrievalAgent
2. 分离质量检查为 QualityAssuranceAgent  
3. 创建 CodeReproductionAgent
4. 设计Agent间协作协议（MCP/A2A）

### 第三阶段: CLI交互界面（1周）

1. 实现 PaperRAGCLI 交互循环
2. 添加闲聊检测和历史回顾
3. 集成 TodoTool 任务板
4. 设计友好的CLI输出格式

### 第四阶段: WebUI Dashboard（2周）

1. FastAPI后端API
2. Streamlit或Vue前端
3. 指标可视化Dashboard
4. 用户反馈收集界面

---

## 六、验收标准

| 功能 | 验收标准 | 测试方法 |
|-----|----------|---------|
| 记忆系统 | 跨会话论文分析历史可检索 | 单元测试 + 手动验证 |
| 工具注册 | 所有工具统一接口调用 | ToolRegistry.test() |
| 流式输出 | 进度事件实时推送 | WebSocket测试 |
| 表格提取 | PDF表格正确解析为Markdown | 对比验证 |
| CLI交互 | 闲聊/历史/任务检测正常 | 集成测试 |
| 专用Agent | 四角色Agent独立可运行 | 单元测试 |
| Dashboard | 30+指标可视化展示 | UI测试 |

---

## 七、参考代码路径

### hello-agents精华代码

| 功能 | 代码路径 |
|-----|---------|
| ReAct循环 | `/home/nvidia/workspace/hello-agents/code/chapter4/ReAct.py` |
| 记忆系统 | `/home/nvidia/workspace/hello-agents/code/chapter15/.../agents.py` |
| Pipeline编排 | `/home/nvidia/workspace/hello-agents/code/chapter14/.../agent.py` |
| 工具注册 | `/home/nvidia/workspace/hello-agents/Co-creation-projects/YYHDBL-.../tools/registry.py` |
| 表格提取 | `/home/nvidia/workspace/hello-agents/Co-creation-projects/healer-666-.../document_ingestion.py` |
| CLI交互 | `/home/nvidia/workspace/hello-agents/Co-creation-projects/YYHDBL-.../hello_code_cli.py` |

### 当前RAG代码

| 功能 | 代码路径 |
|-----|---------|
| LangGraph Agent | `/home/nvidia/workspace/paper/vectordb/agents/paper_rag_agent.py` |
| 审计系统 | `/home/nvidia/workspace/paper/vectordb/database/audit_logger.py` |
| API客户端 | `/home/nvidia/workspace/paper/vectordb/core/api_client.py` |
| 混合检索 | `/home/nvidia/workspace/paper/vectordb/scripts/search.py` |

---

**总结**: 落地方案采用"LangGraph增强 + hello-agents精华融合"策略，保持当前架构的稳定性，同时引入记忆系统、工具统一接口、流式输出等hello-agents的优秀设计模式。专用Agent分工让论文分析更专业，CLI/WebUI提升用户体验。