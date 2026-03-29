###
# 采用LangGraph工作流，定义状态、节点函数，并将它们编织成图。
###

import os
from typing import TypedDict, Optional, Any
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from models import CandidateInfo, MatchAssessment
import fitz  # PyMuPDF

# ==========================================
# 1. 定义智能体的全局状态 (State)
# 状态会在图的各个节点中传递和更新
# ==========================================
class AgentState(TypedDict):
    file_path: str                  # 输入：PDF文件路径
    jd_text: Optional[str]          # 输入：岗位JD（可选）
    resume_text: str                # 内部状态：解析出的简历文本
    parsed_info: Optional[dict]     # 内部状态：结构化的简历信息
    match_assessment: Optional[dict]# 内部状态：匹配度评估结果
    error: Optional[str]            # 错误信息记录


# ==========================================
# 2. 定义大模型及基础配置
# ==========================================
def get_llm():
    # 使用 LangChain 的 OpenAI 封装来调用通义千问
    return ChatOpenAI(
        model=os.getenv("QWEN_MODEL", "qwen-plus"), # "qwen-max","qwen-turbo"
        openai_api_key=os.getenv("DASHSCOPE_API_KEY"),
        openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1", # 阿里云百炼的配置调用地址
        temperature=0.1  # 保持低温度以确保信息抽取的准确性
    )


# ==========================================
# 3. 定义图的节点 (Nodes)
# ==========================================

#"""节点 1（extract）：读取 PDF 文档，提取纯文本"""
def extract_text_node(state: AgentState) -> dict:
    print(">>> [Node: Extract Text] 正在读取简历文件...")
    file_path = state["file_path"]
    try:
        doc = fitz.open(file_path)
        text = "".join([page.get_text("text") for page in doc])
        doc.close()

        # === 加入这个测试，看看为什么提取失败 ===
        print(f"    -> 成功提取文本长度: {len(text)} 字符")
        if len(text.strip()) < 20:
             print("    -> ⚠️ 警告：提取的文本极少，疑似图片/扫描件！")
        # ==================================

        # 返回要更新的 state 字段
        return {"resume_text": text.strip(), "error": None}
    except Exception as e:
        print(f"读取 PDF 失败: {e}")
        return {"resume_text": "", "error": str(e)}


#"""节点 2（parse）：利用 LLM 将非结构化文本转化为结构化 JSON"""
def parse_resume_node(state: AgentState) -> dict:
    print(">>>[Node: Parse Resume] 正在提取结构化信息...")
    if state.get("error") or not state.get("resume_text"):
        return {"parsed_info": None}

    llm = get_llm()
    # LangChain可以自动绑定Pydantic模型进行结构化输出
    structured_llm = llm.with_structured_output(CandidateInfo)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个资深HR，请从以下简历文本中提取信息。如果信息缺失，请填'未提供'。"),
        ("user", "【简历文本】\n{resume_text}")
    ])
    
    chain = prompt | structured_llm
    # 触发调用
    result = chain.invoke({"resume_text": state["resume_text"]})
    
    # 存入状态中（此时 result 是一个 Pydantic 对象，我们转成 dict 方便后续处理）
    return {"parsed_info": result.model_dump() if result else None}

#"""节点 3（match）：进行人岗匹配评估"""
def evaluate_match_node(state: AgentState) -> dict:
    print(">>>[Node: Evaluate Match] 发现 JD，正在进行岗位匹配度评估...")
    llm = get_llm()
    structured_llm = llm.with_structured_output(MatchAssessment)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是面试官，请对比候选人情况与岗位要求，给出客观的打分与优缺点分析。"),
        ("user", "【候选人信息】\n{parsed_info}\n\n【岗位要求 JD】\n{jd_text}")
    ])
    
    chain = prompt | structured_llm
    result = chain.invoke({
        "parsed_info": state["parsed_info"],
        "jd_text": state["jd_text"]
    })
    
    return {"match_assessment": result.model_dump() if result else None}


# ==========================================
# 4. 定义条件路由逻辑 (Conditional Edges)
# ==========================================
#"""判断是否需要进行 JD 评估"""
def router_should_evaluate(state: AgentState) -> str:
    # if state.get("error"):
    #     return "end" # 如果之前出错，直接结束
    if state.get("error") or not state.get("parsed_info"):
        print(">>> [Router] 提取简历文本信息失败或为空，终止后续图流转。")
        return "end" # 如果之前出错，或者连 parsed_info 都没拿到，直接结束
        
    if state.get("jd_text") and state["jd_text"].strip() != "":
        return "evaluate" # 去打分节点
    else:
        print(">>> [Router] 未检测到 JD，跳过评估直接结束。")
        return "end"      # 直接结束


# ==========================================
# 5. 编排并编译图 (Compile Graph)
# ==========================================
def build_resume_agent_graph():
    # 初始化状态图
    workflow = StateGraph(AgentState)

    # 1. 添加所有节点到图中
    workflow.add_node("extract_text", extract_text_node)
    workflow.add_node("parse_resume", parse_resume_node)
    workflow.add_node("evaluate_match", evaluate_match_node)

    # 2. 定义边 (控制执行流转)
    workflow.set_entry_point("extract_text") # 起点，都从extract简历文本开始
    workflow.add_edge("extract_text", "parse_resume") # 解析文本后进入结构化提取

    # 3. 添加条件边 (路由分支)
    workflow.add_conditional_edges(
        "parse_resume",              # 从提取节点出来后
        router_should_evaluate,      # 执行判断逻辑
        {
            "evaluate": "evaluate_match", # 如果返回 "evaluate"，去评价节点
            "end": END                    # 如果返回 "end"，去图的终点
        }
    )

    # 评价节点执行完后，走向终点
    workflow.add_edge("evaluate_match", END)

    # 编译成可执行应用
    return workflow.compile()
