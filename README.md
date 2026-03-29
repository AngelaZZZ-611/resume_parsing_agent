# 🤖  简历解析与人岗匹配智能体 (Resume Parsing Agent)


## 📖 项目说明
本项目是一个基于大语言模型（LLM）的自动化 HR 简历处理助手。它能够批量读取本地 PDF 简历，自动提取候选人的结构化关键信息（姓名、学历、工作经验、技能等）。如果提供了岗位需求（JD），它还能像资深 HR 面试官一样，自动对简历和 JD 进行交叉对比，输出匹配度打分与录用建议，并最终汇总输出为方便 HR 阅读的 Excel 表格。


## 🛠 技术选型及理由

* **语言：Python**
  * *理由*：生态丰富，易于集成各类库。
* **大模型 API：阿里云 Qwen（通义千问）**
  * 示例结果使用的模型是 qwen-plus
  * *理由*：Qwen 系列（如 qwen-plus/max）在中文语义理解、指令遵循方面表现极佳。同时它提供了兼容 OpenAI 的接口，接入成本极低，API 费用相较于海外大模型更具性价比。替换成 DeepSeek API 也可以。
* **Agent框架：LangChain 生态系统中的 LangGraph 框架**
  * *理由*：LangGraph 是目前构建复杂 Agent 的行业标准和未来趋势（LangChain 官方已经明确宣布，传统的 AgentExecutor 将逐渐被淘汰，强烈建议开发者全面转向 LangGraph），它具有极强的可扩展性。
  * *注*：这个简单的任务写成一个 Chain 也是可以的，但是为了后续的可扩展性以及尽量少的代码重构，选择写成 Graph 。*例如：未来如果想加入“如果读取失败则循环调用 OCR 节点”、“在打分前加入 Human-in-the-loop（让人工介入确认信息）”，用 LangGraph 只需要加几行路由代码，而传统 Chain 则要重构整个项目。*
* **结构化提取：Pydantic**
  * *理由*：传统的 Prompt 容易导致大模型输出格式混乱。结合 Pydantic 定义严谨的 Schema，再反向生成 JSON Schema 注入 Prompt，能 100% 保证输出格式可被代码解析。另外，LangChain 原生支持 Pydantic 结构化输出。
* **PDF 读取：PyMuPDF (fitz)**
  * *理由*：适用于非扫描版 PDF 简历文本提取，相比于 pdfminer 或 PyPDF2，PyMuPDF 的文本提取速度最快，对复杂排版和表格中文本的读取准确率更高。
* **数据存储：Pandas**
  * *理由*：将复杂的嵌套 Python 字典展平并输出为高质量的 Excel/CSV 文件，方便 HR 直接在日常办公环境中使用。
  * *注*：批量解析的简历被自动整理存入同一个Excel文件中，每份简历为一行，方便 HR 进行统一查看、检索、依据Agent的打分排序等一系列后续Excel操作。
* **导出文件美化：ExcelWriter 配合 openpyxl 引擎**
  * *理由*：导出的文本里面会包含大量的换行符(\n)，如果直接用 Pandas 导出 Excel，HR 打开表格时内容会挤在一行里，必须手动双击或者点击“自动换行”才能看清。使用 openpyxl 让 Excel 默认支持自动换行（Wrap Text）和垂直居中，也可设置列宽等，让表格更方便、专业。



## 🚀 安装和运行步骤

### 1. 克隆项目

```bash
git clone https://github.com/AngelaZZZ-611/resume_parsing_agent
cd resume-parsing-agent
```

### 2. 环境准备
确保你的电脑安装了 Python 3.10 及以上版本。克隆或下载本项目后，在项目根目录运行：
```bash
pip install -r requirements.txt
```

### 3. 配置 API Key
在项目根目录创建一个 .env 文件（可参考 .env.example），配置你的 Qwen API 密钥：
```
DASHSCOPE_API_KEY="sk-你的通义千问APIKEY"
QWEN_MODEL="qwen-plus"
```
*(前往阿里云百炼平台 免费申请 API Key)*

### 4. 准备数据
* **文件解析目录（支持批量解析）**：将需要解析的 PDF 简历放入项目根目录下的 data/resumes/ 文件夹中。

* **[可选]人岗匹配评估**：如果需要进行“人岗匹配评估”，请在 data/ 目录下新建 jd.txt 文件，将岗位描述（Job Description）粘贴在里面。如果不提供此文件，Agent 将仅提取信息，不进行打分与评估。

### 5. 运行 Agent
```bash
python main.py
```
运行结束后，会自动生成一份名为 HR_简历智能解析_完整版.xlsx 的表格文件在项目根目录下的 res/ 文件夹中。*注*：批量解析的简历被自动整理存入同一个Excel文件中，每份简历为一行，方便 HR 进行统一查看、检索、依据Agent的打分排序等一系列后续Excel操作。



## 🧠 设计思路说明

本智能体采用了 **标准的基于状态图（StateGraph）的智能体工作流（workflow）** 的设计模式。LangGraph 把整个流程抽象为**状态（State）**、**节点**（**Nodes/Tools**， 如 文档读取工具(extract)、 结构化解析工具(parse)、 人岗匹配评估工具(match)等 ）和**边**（**Edges/Routing**，如 条件路由）。使用节点和边，可以将这些步骤解耦。


### 1. LangGraph 设计思维导图

在这个设计中，定义一个智能体的全局状态并初始化（State 包含当前处理的简历文本、解析的信息、JD文本、匹配度评估结果等），之后状态会在图的各个节点中传递和更新。创建状态图，添加所有的节点（Nodes/Tools）到图中，设置起点，添加固定边（控制执行流转，如extract -> parse），添加条件边（路由分支、执行判断逻辑，比如判断是否需要执行JD匹配度评估）。

状态会在各个节点之间进行流转，直到走向终点(END)：

```Text
[ START ]
│
   ▼
( Node 1: Extract Text ) ── 读取PDF，将纯文本存入 State
   │
   ▼
( Node 2: Parse Resume ) ── 调用LLM将State中的非结构化的文本转化为结构化信息，存入 State
   │
   ▼
[ Conditional Edge (条件边) ] ── 判断 State 中是否有 JD？
   ├─▶ 有 JD ─▶ ( Node 3: Evaluate Match ) ── 调用LLM进行人岗匹配评估 ─▶ [ END ]
   │
   └─▶ 无 JD ───────────────────────────────────────────▶ [ END ]
```
程序执行完成后，处理图返回的最终状态(final_state)。解析的简历信息、匹配度评估结果等可从 final_state 中获得。

---

🎉 未来可扩展功能（节点）示例 -- 超强可扩展性：
* **增加智能容错功能（OCR节点）**
   * 如果PDF读取不出来/是乱码（可能是纯图片/扫描版PDF），只需加一个节点 `ocr_fallback_node`(做 OCR 处理) 和一条新的条件边。比如：判断如果 Node 1 输出的纯文本长度小于50或者是乱码，则`extract -> ocr_fallback_node`
   * *注：现版本（v1.0）若是纯图片/扫描版PDF会报出警告（提示解析失败或提取文本为空），并跳过此简历处理下一份，所有跳过的简历文件名会被存入一个Excel中（Agent未能处理的简历文件名汇总.xlsx）方便 HR 人工处理。*
* **HR 需要人工审核（Human-in-the-loop）**：
   * 假设希望：AI提取出信息后先暂停，发送一个确认页面给 HR，HR 说“没问题”才进行与 JD 的匹配度打分。
   * LangGraph 原生支持在特定的节点暂停（Interrupt），等待人类确认或修改 State 后再继续执行：增加断点，使程序走到打分前自动暂停，HR查看/修改，然后可以通过 UI 接收修改后的 state，继续后续操作。       


### 2. 模块划分
* `models.py`：定义 Agent 的输出规范。用 Pydantic 数据模型实现强类型定义结构，确保大模型返回完美匹配的结构化信息。
   * Education：最高学历/学位、毕业院校名称、专业名称、就读时间段
   * WorkExperience：公司名称、职位名称、工作时间短、工作内容或职责描述概括
   * ProjectExperience（可有可无）：项目名称、担任角色、项目内容及个人贡献描述
   * CandidateInfo：候选人姓名、联系电话、电子邮箱、教育背景列表、工作经历列表、专业技能标签（关键词抽取）、项目经历列表（如有）
   * MatchAssessment：匹配度打分（0-100的整数）、相比于JD的核心优势、不满足JD的潜在风险或不足（简单描述）、一句话的录用建议（如：强烈推荐面试 / 建议作为备选 / 不匹配）
   * AgentOutput：CandidateInfo、MatchAssessment（岗位匹配度评估。若未提供JD，则此项为空）

* `graph_agent.py`：[核心] LangGraph 工作流定义。定义状态、节点函数，并将它们编织成图。
   * `extract_text_node`: extract 节点 -- 读取 PDF 文档，提取纯文本
   * `parse_resume_node`: parse 节点 -- 利用 LLM 将非结构化文本转化为结构化 JSON
   * `evaluate_match_node`: match 节点 -- 进行人岗匹配评估
   * `router_should_evaluate`: 定义条件路由逻辑，判断是否需要进行 JD 评估
   * `build_resume_agent_graph`: 编排并编译图 (Compile Graph)

* `main.py`：调用封装好的 LangGraph，批量处理简历（单个也可），结果保存（格式调整、设置自动换行和垂直居中并导出 Excel ）

* `utils.py`：一些辅助函数。把解析出来的结构化的 Pydantic/JSON 列表进行展平平铺（多段经历合并等），转化为 Excel 里易读的换行文本（方便 HR 查看）。
   * `format_education`格式化教育背景、`format_work_experience`格式化工作经历（含职责描述）、`format_project_experience`格式化项目经验



## 📂 支持的文件格式与限制
**当前版本（v1.0）支持的输入格式：**
* ✅ **纯文本版 PDF (`.pdf`)**：由 Word、WPS 等排版软件直接导出的 PDF 文件，或者各大招聘网站导出的标准 PDF 简历。

**当前版本暂不支持的输入格式（将报出警告、被系统自动跳过、并将无法处理的文件名统一存入一个Excel文件）：**
* ❌ **扫描版/图片版 PDF**：由扫描仪或多张图片转成的 PDF。当前系统未接入 OCR 引擎，无法读取其中的文字。
* ❌ **Word 文档 (`.doc`, `.docx`)**：暂未集成 Word 解析库。
* ❌ **纯文本文件 (`.txt`) 或 图片 (`.jpg`, `.png`)**。



## 🚧 已知局限和未来改进方向
### 当前局限
1. **文件格式强依赖**：目前强依赖于 `PyMuPDF` 的底层文本提取能力，如果简历是截图生成的 PDF 或扫描件，当前版本会提取为空；对于带有复杂背景水印、或者文字被图片覆盖的 PDF，提取的文本可能会出现乱码或缺失。
2. **大模型不可控性**：尽管使用了强校验的 Pydantic 结构化输出（`with_structured_output`），但在极少数情况下，大模型可能依然会返回破损的 JSON，此时系统会报出警告（大模型处理异常）并跳过，这部分简历需要 HR 手工介入（未被成功处理的简历文件名会被统一存入一个Excel中）。
3. **上下文窗口截断**：如果候选人简历长达十几页（如包含大量长篇论文发表记录），加上长篇的岗位 JD，可能会突破 Qwen 模型的单次 Token 限制，导致尾部信息丢失。
4. **字段缺失容错**：若候选人刻意隐瞒某些经历，模型只能返回“未提供”，无法通过第三方背调补充。


### 未来改进方向 (TODO)
* [ ] **多格式解析器集成**：在 `extract_text_node` 中引入 `python-docx` 库以支持 `.docx` 简历，引入内置的 `open()` 函数支持 `.txt` 解析。
* [ ] **集成 OCR 模块-视觉兜底机制**：使用 `PaddleOCR` 或直接调用大模型的多模态视觉能力（如 `Qwen-VL`）。当判定 PDF 提取文本极少（疑似扫描件）时，自动将 PDF 转成图片丢给视觉模型读取。
* [ ] **可视化交互界面 (Web UI)**：基于 `Streamlit` 或 `Gradio` 搭建前端页面，允许 HR 直接拖拽上传简历，并实时查看 LangGraph 节点的执行轨迹与提取结果；引入多轮对话交互：允许 HR 针对某份简历追问 Agent（例如：“他为什么从上一家公司离职？”）。
* [ ] **RAG 人才库检索**：将结构化提取后的数据（尤其是工作和项目经历）向量化并存入向量数据库 `Chroma` 或 `Milvus`，支持 HR “用自然语言从库里捞人”（例如：“帮我找一个懂 Python 且有 3 年以上经验的人”）。


## 🔎 [示例]运行显示

示例简历在 data/resumes/ 文件夹中，示例岗位 JD 见 data/jd.txt。示例简历的解析结果输出见 **res/HR_简历智能解析_完整版.xlsx** （一个Excel表格）。

运行程序（示例）时的显示如下：
[示例-运行程序显示如图](https://github.com/AngelaZZZ-611/resume_parsing_agent/blob/main/res/%E7%A4%BA%E4%BE%8B-%E8%BF%90%E8%A1%8C%E6%98%BE%E7%A4%BA.png)

若文本无法解析（比如纯图片/扫描版PDF），当前版本（V1.0）会显示警告如下图所示：
[示例-文本解析异常警告如图](https://github.com/AngelaZZZ-611/resume_parsing_agent/blob/main/res/%E7%A4%BA%E4%BE%8B-%E6%96%87%E6%9C%AC%E8%A7%A3%E6%9E%90%E5%BC%82%E5%B8%B8%E8%AD%A6%E5%91%8A.png)

所有跳过的简历（无论是文本格式无法解析或者是大模型处理失败），其简历文件名会被统一存入一个Excel中 -- **res/Agent未能处理的简历文件名汇总.xlsx**，方便 HR 知道哪些简历未被Agent成功处理并进行人工处理。
