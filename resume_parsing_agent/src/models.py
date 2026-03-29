###
# 定义Agent的输出字段规范，使用Pydantic数据模型实现强类型定义结构，确保大模型返回完美匹配的结构化JSON
###

from pydantic import BaseModel, Field
from typing import List, Optional

class Education(BaseModel):
    degree: str = Field(description="最高学历/学位，如：大专、本科、硕士、博士等")
    school: str = Field(description="毕业院校名称")
    major: str = Field(description="专业名称")
    # graduation_year: str = Field(description="毕业年份，如：2021")
    time_period: Optional[str] = Field(default=None, description="就读时间段，如：2018.09 - 2022.06")

class WorkExperience(BaseModel):
    company_name: str = Field(description="公司名称")
    job_title: str = Field(description="职位名称")
    time_period: Optional[str] = Field(default=None, description="工作时间段")
    description: Optional[str] = Field(default=None, description="工作内容或职责描述概括")

class ProjectExperience(BaseModel):
    project_name: str = Field(description="项目名称")
    role: Optional[str] = Field(default=None, description="担任角色")
    description: Optional[str] = Field(default=None, description="项目内容及个人贡献描述")

class CandidateInfo(BaseModel):
    name: str = Field(default="未提供", description="候选人姓名")
    phone: str = Field(default="未提供", description="联系电话")
    email: str = Field(default="未提供", description="电子邮箱")
    education: List[Education] = Field(default_factory=list, description="教育背景列表")
    # experiences: List[Experience] = Field(default_factory=list, description="工作经历列表")
    work_experience: List[WorkExperience] = Field(default_factory=list, description="工作经历列表")
    skills: List[str] = Field(default_factory=list, description="专业技能标签（关键词抽取），如：Java, Python, 项目管理 等")
    project_experience: Optional[List[ProjectExperience]] = Field(default="未提供", description="项目经验列表（如有）")

class MatchAssessment(BaseModel):
    score: int = Field(description="匹配度打分，0-100的整数")
    advantages: List[str] = Field(description="相比于JD的核心优势")
    disadvantages: List[str] = Field(description="不满足JD的潜在风险或不足（简单描述）") # 可要可不要
    recommendation: str = Field(description="一句话的录用建议，如：强烈推荐面试 / 建议作为备选 / 不匹配")

class AgentOutput(BaseModel):
    info: CandidateInfo
    match_assessment: Optional[MatchAssessment] = Field(
        default=None, 
        description="岗位匹配度评估。若未提供JD，则此项为空"
    )