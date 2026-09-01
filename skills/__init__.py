from skills.base import BaseSkill
from skills.data_processing import data_processing_skill
from skills.data_management import data_management_skill
from skills.financial_analytics import financial_analytics_skill
from skills.rag_context import rag_context_skill
from skills.hf_skills import hf_skill

ALL_SKILLS = [
    data_processing_skill,
    data_management_skill,
    financial_analytics_skill,
    rag_context_skill,
    hf_skill
]
