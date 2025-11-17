# ===================================================================================
# Project: ChatSkLearn
# File: src/config.py
# Description: Configurations Setting file
# Author: LALAN KUMAR
# Created: [01-11-2025]
# Updated: [01-11-2025]
# LAST MODIFIED BY: LALAN KUMAR  [https://github.com/kumar8074]
# Version: 1.0.0
# ===================================================================================

import os
import sys
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

# Set Gemini API key
os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")

# Dynamically add the project root directory to sys.path
# Allows importing modules from the 'src' directory
current_file_path = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(current_file_path, "../../.."))
if project_root not in sys.path:
    sys.path.append(project_root)


class AppConfig(BaseSettings):
    """Application configuration"""
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    
    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore"
    )


class LLMConfig(BaseSettings):
    """LLM configuration"""
    model: str = Field(default="gemini-2.5-flash")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=8192)
    
    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        case_sensitive=False,
        extra="ignore"
    )


class EmbeddingConfig(BaseSettings):
    """Embedding model configuration"""
    model: str = Field(default="models/text-embedding-004")
    batch_size: int = Field(default=100, ge=1, le=1000)
    
    model_config = SettingsConfigDict(
        env_prefix="EMBEDDING_",
        case_sensitive=False,
        extra="ignore"
    )


class OpenSearchConfig(BaseSettings):
    """OpenSearch configuration"""
    host: str = Field(default="opensearch:9200")
    user: str = Field(default="admin")
    password: str = Field(default="admin")
    index_name: str = Field(default="sklearn_documentation")
    use_ssl: bool = Field(default=False)
    verify_certs: bool = Field(default=False)
    
    model_config = SettingsConfigDict(
        env_prefix="OPENSEARCH_",
        case_sensitive=False,
        extra="ignore"
    )


class ScraperConfig(BaseSettings):
    """Web scraper configuration"""
    base_url: str = Field(default="https://scikit-learn.org/stable/")
    output_dir: str = Field(default="temp")
    max_depth: int = Field(default=5)
    max_pages: int = Field(default=10000)
    concurrency: int = Field(default=25)
    
    model_config = SettingsConfigDict(
        env_prefix="SCRAPER_",
        case_sensitive=False,
        extra="ignore"
    )
    
class ChunkerConfig(BaseSettings):
    """Content chunker configuration"""
    urls_file: str = Field(default="temp/successful_urls.txt")
    output_dir: str = Field(default="temp/sklearn_scraped_data")
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=200)
    
    model_config = SettingsConfigDict(
        env_prefix="CHUNKER_",
        case_sensitive=False,
        extra="ignore"
    )



# Initialize configurations
app_config = AppConfig()
llm_config = LLMConfig()
embedding_config = EmbeddingConfig()
opensearch_config = OpenSearchConfig()
scraper_config = ScraperConfig()
chunker_config = ChunkerConfig()

# Initialize models
LLM_MODEL = ChatGoogleGenerativeAI(
    model=llm_config.model,
    temperature=llm_config.temperature,
    max_tokens=llm_config.max_tokens,
)

EMBEDDING_MODEL = GoogleGenerativeAIEmbeddings(model=embedding_config.model)

# Export for backward compatibility
OPENSEARCH_HOST = opensearch_config.host
OPENSEARCH_USER = opensearch_config.user
OPENSEARCH_PASS = opensearch_config.password
INDEX_NAME = opensearch_config.index_name