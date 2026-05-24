"""
翻译提炼与格式化输出模块
"""

import json
import re
from typing import Dict, List, Any
from pydantic import BaseModel

# ===== 输出Schema定义 =====

class Citation(BaseModel):
    """引用结构"""
    claim: str              # 声明内容
    source_chunk_id: str    # 来源chunk ID
    source_text: str        # 原文片段
    location: str = ""      # 页码/章节
    confidence: float = 1.0 # 置信度


class PaperAnalysisOutput(BaseModel):
    """论文解读输出格式"""
    paper_title: str
    arxiv_id: str = ""

    # 餐巾纸摘要
    napkin_summary: str

    # 核心概念
    core_concepts: List[Dict]

    # 公式提炼
    formulas: List[Dict]

    # 中文通俗解读
    chinese_interpretation: str

    # 代码实现设计
    code_design: Dict

    # Citations
    citations: List[Citation]

    # 质量指标
    quality_metrics: Dict


class RAGQueryOutput(BaseModel):
    """RAG查询输出格式"""
    query: str
    intent: str

    # 检索结果
    retrieved_chunks: List[str]
    retrieval_scores: List[float]

    # 生成的答案
    answer: str

    # Citations
    citations: List[Citation]

    # 质量评估
    hallucination_risk: float
    citation_accuracy: float
    support_score: float

    # 元数据
    metadata: Dict = {}


class ContentTranslator:
    """内容翻译器"""

    # 学术术语翻译词典
    TERM_DICT = {
        "Self-Attention": "自注意力机制",
        "Multi-Head Attention": "多头注意力",
        "Encoder": "编码器",
        "Decoder": "解码器",
        "Positional Encoding": "位置编码",
        "Transformer": "Transformer",
        "Neural Network": "神经网络",
        "Deep Learning": "深度学习",
        "Machine Learning": "机器学习",
        "Token": "词元",
        "Embedding": "嵌入向量",
        "Layer Normalization": "层归一化",
        "Residual Connection": "残差连接",
        "Softmax": "归一化指数函数",
        "Query": "查询向量",
        "Key": "键向量",
        "Value": "值向量",
    }

    def translate_terms(self, text: str) -> str:
        """翻译学术术语"""
        result = text
        for eng, zh in self.TERM_DICT.items():
            # 保留英文，添加中文注释
            result = re.sub(
                f'({eng})',
                f'{eng}({zh})',
                result,
                flags=re.IGNORECASE
            )
        return result

    def extract_key_points(self, content: str) -> List[str]:
        """提炼关键点"""
        # 提取要点标记的内容
        key_points = []

        # 匹配数字列表
        numbered = re.findall(r'^\d+\.\s*(.+)', content, re.MULTILINE)
        key_points.extend(numbered)

        # 匹配bullet列表
        bullets = re.findall(r'^[-•]\s*(.+)', content, re.MULTILINE)
        key_points.extend(bullets)

        # 匹配"核心"/"关键"关键词段落
        key_paragraphs = re.findall(r'(核心[^。]+。|关键[^。]+。)', content)
        key_points.extend(key_paragraphs)

        return key_points[:10]  # 最多10个


class FormulaExtractor:
    """公式提取器"""

    def extract(self, text: str) -> List[Dict]:
        """提取公式及其解释"""
        formulas = []

        # 匹配LaTeX公式
        latex_formulas = re.findall(r'\$\$(.+?)\$\$|\$(.+?)\$', text, re.DOTALL)

        for i, (block, inline) in enumerate(latex_formulas):
            formula_text = block or inline
            formulas.append({
                "id": f"formula_{i+1}",
                "latex": formula_text.strip(),
                "context": self._find_context(text, formula_text),
                "explanation": ""  # 待LLM生成
            })

        # 匹配普通公式描述
        formula_desc = re.findall(r'(公式[：:]\s*[^。\n]+)', text)
        for desc in formula_desc:
            formulas.append({
                "id": f"formula_desc_{len(formulas)+1}",
                "description": desc,
                "latex": "",
                "context": "",
                "explanation": ""
            })

        return formulas

    def _find_context(self, text: str, formula: str) -> str:
        """查找公式的上下文"""
        # 找公式位置
        pos = text.find(formula)
        if pos == -1:
            return ""

        # 提取前后100字符作为上下文
        start = max(0, pos - 100)
        end = min(len(text), pos + len(formula) + 100)

        return text[start:end]


class OutputFormatter:
    """输出格式化器"""

    def format_analysis_output(self, raw_output: str, paper_title: str) -> PaperAnalysisOutput:
        """格式化论文解读输出"""
        translator = ContentTranslator()
        formula_extractor = FormulaExtractor()

        # 解析原始输出
        sections = self._parse_sections(raw_output)

        # 提取核心概念
        core_concepts = []
        if "核心概念" in sections or "核心创新" in sections:
            content = sections.get("核心概念", sections.get("核心创新", ""))
            core_concepts = [
                {"name": line.strip(), "description": ""}
                for line in content.split('\n')
                if line.strip() and not line.startswith('#')
            ]

        # 提取公式
        formulas = formula_extractor.extract(raw_output)

        # 提取Citations
        citations = self._extract_citations(raw_output)

        return PaperAnalysisOutput(
            paper_title=paper_title,
            napkin_summary=sections.get("餐巾纸摘要", sections.get("摘要", "")),
            core_concepts=core_concepts,
            formulas=formulas,
            chinese_interpretation=sections.get("通俗解读", raw_output),
            code_design={"modules": [], "interfaces": []},
            citations=citations,
            quality_metrics={
                "hallucination_risk": 0.0,
                "citation_accuracy": len(citations) / max(len(core_concepts), 1),
            }
        )

    def format_query_output(self,
                            query: str,
                            intent: str,
                            chunks: List[Dict],
                            raw_answer: str) -> RAGQueryOutput:
        """格式化RAG查询输出"""
        # 提取chunk_ids和scores
        chunk_ids = [c.get('chunk_id', '') for c in chunks]
        scores = [c.get('rrf_score', 0) for c in chunks]

        # 提取Citations
        citations = self._extract_citations(raw_answer)

        # 计算质量指标
        citation_accuracy = len(citations) / max(len(raw_answer.split('\n')), 1)
        support_score = sum(scores[:len(citations)]) / max(len(citations), 1)

        return RAGQueryOutput(
            query=query,
            intent=intent,
            retrieved_chunks=chunk_ids,
            retrieval_scores=scores,
            answer=raw_answer,
            citations=citations,
            hallucination_risk=0.05,  # 待实际检测
            citation_accuracy=min(citation_accuracy, 1.0),
            support_score=support_score,
            metadata={"chunks_count": len(chunks)}
        )

    def _parse_sections(self, text: str) -> Dict[str, str]:
        """解析Markdown章节"""
        sections = {}

        # 匹配Markdown标题
        pattern = r'^#+\s*(.+)\n((?:[^#].*\n)*)'
        matches = re.findall(pattern, text, re.MULTILINE)

        for title, content in matches:
            sections[title.strip()] = content.strip()

        return sections

    def _extract_citations(self, text: str) -> List[Citation]:
        """提取Citations"""
        citations = []

        # 匹配 [chunk_id] 格式
        inline_cites = re.findall(r'\[chunk_([^\]]+)\]', text)
        for chunk_id in inline_cites:
            citations.append(Citation(
                claim="",
                source_chunk_id=f"chunk_{chunk_id}",
                source_text=""
            ))

        # 匹配 Citation格式
        formal_cites = re.findall(
            r'Source:\s*(chunk_[^\n]+)\s*Text:\s*([^\n]+)',
            text,
            re.MULTILINE
        )
        for chunk_id, source_text in formal_cites:
            citations.append(Citation(
                claim="",
                source_chunk_id=chunk_id.strip(),
                source_text=source_text.strip()
            ))

        return citations

    def to_json(self, output: BaseModel) -> str:
        """转换为JSON字符串"""
        return json.dumps(output.model_dump(), ensure_ascii=False, indent=2)

    def to_markdown(self, output: BaseModel) -> str:
        """转换为Markdown"""
        if isinstance(output, PaperAnalysisOutput):
            md = f"""# {output.paper_title} 论文解读

## 餐巾纸摘要
{output.napkin_summary}

## 核心概念
"""
            for concept in output.core_concepts:
                md += f"- {concept['name']}\n"

            md += f"""
## 公式提炼
"""
            for formula in output.formulas:
                md += f"- {formula.get('latex', formula.get('description', ''))}\n"

            md += f"""
## 中文通俗解读
{output.chinese_interpretation}

## Citations
"""
            for cite in output.citations:
                md += f"- [{cite.source_chunk_id}] {cite.source_text[:50]}...\n"

            return md

        elif isinstance(output, RAGQueryOutput):
            md = f"""# 查询结果

**问题**: {output.query}
**意图**: {output.intent}

## 答案
{output.answer}

## 检索来源
"""
            for i, (chunk_id, score) in enumerate(zip(output.retrieved_chunks, output.retrieval_scores)):
                md += f"{i+1}. [{chunk_id}] (相关度: {score:.2f})\n"

            md += f"""
## Citations
"""
            for cite in output.citations:
                md += f"- Claim: {cite.claim}\n"
                md += f"  Source: {cite.source_chunk_id}\n"

            md += f"""
## 质量指标
- 幻觉风险: {output.hallucination_risk:.2%}
- 引用准确率: {output.citation_accuracy:.2%}
- 支撑度: {output.support_score:.2%}
"""
            return md

        return ""


# 测试
if __name__ == "__main__":
    # 测试格式化
    formatter = OutputFormatter()

    test_output = """
# Transformer论文解读

## 餐巾纸摘要
Transformer让AI学会了一眼看全文，抓住重点。

## 核心创新
- 自注意力机制
- 多头注意力
- 位置编码

## 公式
$$Attention(Q,K,V) = softmax(QK^T/√d_k)V$$

## Citations
- Source: chunk_abc123
  Text: Transformer employs self-attention mechanism
"""

    result = formatter.format_analysis_output(test_output, "Transformer")
    print(formatter.to_markdown(result))
    print("\n--- JSON格式 ---\n")
    print(formatter.to_json(result)[:500])