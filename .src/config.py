# config.py
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv("D:\\gitRepo\\camel\\.env")

def create_model():
    """创建并返回模型实例"""
    return ModelFactory.create(
        model_platform=ModelPlatformType.DEEPSEEK,
        model_type=ModelType.DEEPSEEK_CHAT,
        model_config_dict={"temperature": 0.0, "stream": True},
    )