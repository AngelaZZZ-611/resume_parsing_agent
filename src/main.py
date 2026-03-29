###
# 主程序：调用写好的LangGraph工作流、数据处理、简历批量处理、结果保存。
###
import os
import pandas as pd
from dotenv import load_dotenv
from graph_agent import build_resume_agent_graph
from utils import *

load_dotenv()

# 文件地址，之后也可以写成argparse的形式来传入文件路径（工程优化）
JD_PATH = "resume_parsing_agent/data/jd.txt"
RESUMES_DIR = "resume_parsing_agent/data/resumes"
SAVE_PATH = "resume_parsing_agent/res"

def main():
    # 编译 LangGraph 工作流
    app = build_resume_agent_graph()
    
    # 准备 JD
    jd_text = None
    if os.path.exists(f"{JD_PATH}"):
        with open(f"{JD_PATH}", "r", encoding="utf-8") as f:
            jd_text = f.read().strip()

    resumes_dir = RESUMES_DIR #"resumes"
    pdf_files =[f for f in os.listdir(resumes_dir) if f.endswith(".pdf")]
    
    results = []
    failed_files = []
    
    for file in pdf_files:
        print(f"\n========== 开始处理: {file} ==========")
        file_path = os.path.join(resumes_dir, file)
        
        # 初始化这个图的初始状态 (Initial State)
        initial_state = {
            "file_path": file_path,
            "jd_text": jd_text,
            "resume_text": "",
            "parsed_info": None,
            "match_assessment": None,
            "error": None
        }
        
        # 调用 LangGraph 运行 (invoke)
        # 此时程序会按设定好的节点和边，在图里漫游/跳转，直到走到 END
        final_state = app.invoke(initial_state)
        
        # 处理图返回的最终状态
        if final_state.get("error"):
            print(f"处理跳过，原因: {final_state['error']}")
            continue
            
        # info = final_state.get("parsed_info", {})
        # match = final_state.get("match_assessment")
        info = final_state.get("parsed_info") or {}
        match = final_state.get("match_assessment") or {}

        # 增加业务拦截：如果 info 真是空的，说明解析彻底失败，直接记录并跳过
        if not info:
            print(f"！ 警告: [{file}] 解析失败或提取文本为空 (可能是图片型PDF或大模型处理异常)，已跳过。")
            failed_files.append(file)
            continue

        ## Save
        # 展平所有的字段并拼接，存入 Excel
        row = {
            "文件名": file,
            "姓名": info.get("name", "未提供"),
            "电话": info.get("phone", "未提供"),
            "邮箱": info.get("email", "未提供"),
            
            # 下面的简历解析细节想存可存（建议存！），不想存可注释掉：
            # 调用辅助函数完整保留所有经历
            "教育背景": format_education(info.get("education")),
            "工作经历": format_work_experience(info.get("work_experience")),
            "项目经验": format_project_experience(info.get("project_experience")),
            
            # 技能列表转为逗号分隔的字符串
            "专业技能": ", ".join(info.get("skills",[])) if isinstance(info.get("skills"), list) else "未提供",
        }
        
        # 如果提供了 JD 且进行了匹配评估，追加评估结论
        if match:
            row.update({
                "匹配度得分": match.get("score"),
                "HR录用建议": match.get("recommendation"),
                "核心优势": "\n".join(match.get("advantages",[])), # 可存可不存
                "潜在风险/不足": "\n".join(match.get("disadvantages",[])) # 可存可不存
            })
            
        results.append(row)

    # 导出 Excel
    if results:
        df = pd.DataFrame(results)
        output_file = f"{SAVE_PATH}/HR_简历智能解析_完整版.xlsx"
        # pd.DataFrame(results).to_excel("HR_简历智能解析_Graph版.xlsx", index=False)
        
        ### 让 Excel 默认支持自动换行（Wrap Text），不用手动，不在意可以不要
        # 使用 ExcelWriter 配合 openpyxl 引擎
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='简历解析汇总')
            
            # 获取当前的工作表
            worksheet = writer.sheets['简历解析汇总']
            
            # 遍历所有单元格，设置自动换行和垂直居中
            from openpyxl.styles import Alignment
            for row in worksheet.iter_rows():
                for cell in row:
                    cell.alignment = Alignment(wrap_text=True, vertical='top')
                    
            # # (可选) 设置列宽，让体验更好
            # worksheet.column_dimensions['A'].width = 20 # 文件名
            # worksheet.column_dimensions['E'].width = 30 # 教育背景
            # worksheet.column_dimensions['F'].width = 50 # 工作经历
            # worksheet.column_dimensions['G'].width = 50 # 项目经验

        print(f"\n*** 全部处理完成，Excel报表已生成：{output_file} ***")

    # 记录下Agent未能处理的简历文件名，存入Excel
    if failed_files != []:
        pd.DataFrame(failed_files).to_excel(f"{SAVE_PATH}/Agent未能处理的简历文件名汇总.xlsx", index=False)

if __name__ == "__main__":
    main()
