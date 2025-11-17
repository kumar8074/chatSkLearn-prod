# ===================================================================================
# Project: ChatSkLearn
# File: src/services/langfuse/langfuse_tracer.py
# Description: Langfuse configuration and callback handler setup
# Author: LALAN KUMAR
# Created: [09-11-2025]
# Updated: [09-11-2025]
# LAST MODIFIED BY: LALAN KUMAR  [https://github.com/kumar8074]
# Version: 1.1.0
# ===================================================================================

import os
import sys
from typing import Optional
from langfuse.langchain import CallbackHandler
from langfuse import Langfuse
from dotenv import load_dotenv
load_dotenv()

# Dynamically add the project root directory to sys.path
current_file_path = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(current_file_path, "../../../.."))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.logger import logging


class LangfuseConfig:
    """Langfuse configuration and callback handler manager"""
    
    def __init__(
        self,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        host: Optional[str] = None,
        enabled: bool = True
    ):
        """
        Initialize Langfuse configuration
        
        Args:
            public_key: Langfuse public key (from env if not provided)
            secret_key: Langfuse secret key (from env if not provided)
            host: Langfuse host URL (from env if not provided)
            enabled: Enable/disable Langfuse tracing
        """
        self.enabled = enabled and os.getenv("LANGFUSE_ENABLED", "true").lower() == "true"
        
        if not self.enabled:
            logging.warning("Langfuse tracing disabled")
            return
        
        self.public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
        self.secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
        self.host = host or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        
        # Validate required keys
        if not self.public_key or not self.secret_key:
            self.enabled = False
            logging.warning("Langfuse keys not found. Tracing disabled.")
            return
        
        # Set environment variables for the CallbackHandler to use
        os.environ["LANGFUSE_PUBLIC_KEY"] = self.public_key
        os.environ["LANGFUSE_SECRET_KEY"] = self.secret_key
        os.environ["LANGFUSE_HOST"] = self.host
        
        # Initialize Langfuse client for flush operations
        try:
            self.client = Langfuse(
                public_key=self.public_key,
                secret_key=self.secret_key,
                host=self.host
            )
            logging.info(f"Langfuse initialized: {self.host}")
        except Exception as e:
            logging.error(f"Failed to initialize Langfuse client: {e}")
            self.enabled = False
    
    def get_callback_handler(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        trace_name: Optional[str] = None,
        metadata: Optional[dict] = None,
        tags: Optional[list] = None
    ) -> Optional[CallbackHandler]:
        """
        Create a Langfuse callback handler
        
        In v3, CallbackHandler() reads credentials from environment variables
        that were set during initialization.
        
        Args:
            session_id: Session/thread identifier  
            user_id: User identifier
            trace_name: Name for the trace
            metadata: Additional metadata to attach
            tags: Tags for filtering/organizing traces
            
        Returns:
            CallbackHandler instance or None if disabled
        """
        if not self.enabled:
            return None
        
        try:
            # Create handler - it reads credentials from environment variables
            # We just create a basic handler and will update trace info per-request
            handler = CallbackHandler()
            return handler
        except Exception as e:
            logging.error(f"Failed to create callback handler: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def flush(self):
        """Flush any pending traces to Langfuse"""
        if self.enabled and hasattr(self, 'client'):
            try:
                self.client.flush()
            except Exception as e:
                logging.error(f"Error flushing Langfuse: {e}")


# Global Langfuse configuration instance
_langfuse_config: Optional[LangfuseConfig] = None

def get_langfuse_config() -> LangfuseConfig:
    """Get or create global Langfuse configuration"""
    global _langfuse_config
    if _langfuse_config is None:
        _langfuse_config = LangfuseConfig()
    return _langfuse_config


def get_langfuse_callback(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    trace_name: Optional[str] = None,
    metadata: Optional[dict] = None,
    tags: Optional[list] = None
) -> Optional[CallbackHandler]:
    """
    Convenience function to get a Langfuse callback handler
    
    Note: In Langfuse v3, session_id, user_id, trace_name, tags, and metadata
    need to be set on the LangChain runnable config, not on the handler itself.
    
    Args:
        session_id: Session/thread identifier (not used in v3)
        user_id: User identifier (not used in v3)
        trace_name: Name for the trace (not used in v3)
        metadata: Additional metadata (not used in v3)
        tags: Tags for the trace (not used in v3)
        
    Returns:
        CallbackHandler or None if disabled
    """
    config = get_langfuse_config()
    return config.get_callback_handler(
        session_id=session_id,
        user_id=user_id,
        trace_name=trace_name,
        metadata=metadata,
        tags=tags
    )