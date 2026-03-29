###
# 用到的一些辅助函数，比如：处理输出保存的数据格式
###

# ==========================================
# 用于将简历解析的结构都存下来（方便HR查看）
# 辅助函数：把解析出来的结构化的列表转化为 Excel 里易读的换行文本
# ==========================================

def format_education(edu_list):
    """格式化教育背景：[2018.09 - 2022.06] 清华大学 - 计算机科学 (本科)"""
    if not edu_list or not isinstance(edu_list, list):
        return "未提供"
    
    res =[]
    for e in edu_list:
        # 使用 or "未知" 防止模型返回 None 时拼接出 "None" 字符串
        time = e.get("time_period") or "时间未知"
        school = e.get("school") or "学校未知"
        major = e.get("major") or "专业未知"
        degree = e.get("degree") or "学历未知"
        
        res.append(f"[{time}] {school} - {major} ({degree})")
    
    return "\n".join(res)

def format_work_experience(work_list):
    """格式化工作经历，包含职责描述"""
    if not work_list or not isinstance(work_list, list):
        return "未提供"
    
    res =[]
    for w in work_list:
        time = w.get("time_period") or "时间未知"
        company = w.get("company_name") or "公司未知"
        title = w.get("job_title") or "职位未知"
        desc = w.get("description") or "无描述"
        
        # 把描述里可能自带的换行符替换为空格，保持排版整洁
        desc = desc.replace("\n", " ") 
        
        # 拼装单段经历：
        # [时间段] 公司名称 - 职位名称
        #   职责: xxxx
        res.append(f"[{time}] {company} - {title}\n  职责: {desc}")
    
    # 多段工作经历之间用两个换行符隔开，Excel里看起来更清晰
    return "\n\n".join(res)

def format_project_experience(proj_list):
    """格式化项目经验"""
    # 兼容处理：因为解析格式模型里设定了 default="未提供"，判断一下类型
    if not proj_list or isinstance(proj_list, str):
        return "未提供"
    
    res =[]
    for p in proj_list:
        name = p.get("project_name") or "项目未知"
        role = p.get("role") or "未提及角色"
        desc = p.get("description") or "无描述"
        desc = desc.replace("\n", " ")
        
        res.append(f"* {name} (角色: {role})\n  描述: {desc}")
        
    return "\n\n".join(res)