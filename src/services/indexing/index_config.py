# ===================================================================================
# Project: ChatSkLearn
# File: src/services/indexing/index_config.py
# Description: OpenSearch index configuration
# Author: LALAN KUMAR
# Created: [01-11-2025]
# Updated: [01-11-2025]
# LAST MODIFIED BY: LALAN KUMAR  [https://github.com/kumar8074]
# Version: 1.1.0
# ===================================================================================

SKLEARN_INDEX_BODY = {
    "settings": {
        "index": {
            "knn": True,
            "number_of_shards": 2,
            "number_of_replicas": 1,
            "refresh_interval": "1s"
        },
        "analysis": {
            "analyzer": {
                "code_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "code_filter"]
                },
                "sklearn_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "stop", "sklearn_synonym"]
                }
            },
            "filter": {
                "code_filter": {
                    "type": "word_delimiter",
                    "preserve_original": True,
                    "split_on_numerics": False
                },
                "sklearn_synonym": {
                    "type": "synonym",
                    "synonyms": [
                        "classifier, classification",
                        "regressor, regression",
                        "estimator, model",
                        "hyperparameter, parameter",
                        "cross validation, cv, cross_validation",
                        "train, fit",
                        "predict, prediction"
                    ]
                }
            }
        }
    },
    "mappings": {
        "properties": {
            # Identifiers
            "chunk_id": {"type": "keyword"},
            "type": {"type": "keyword"},
            "page_type": {"type": "keyword"},
            
            # Content fields
            "heading": {
                "type": "text",
                "analyzer": "sklearn_analyzer",
                "fields": {
                    "keyword": {"type": "keyword"}
                }
            },
            "text": {
                "type": "text",
                "analyzer": "sklearn_analyzer"
            },
            "full_text": {
                "type": "text",
                "analyzer": "code_analyzer"
            },
            "enriched_text": {
                "type": "text",
                "analyzer": "sklearn_analyzer"
            },
            
            # Vector embedding
            "embedding": {
                "type": "knn_vector",
                "dimension": 768,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "nmslib",
                    "parameters": {
                        "ef_construction": 512,
                        "m": 16
                    }
                }
            },
            
            # Code blocks
            "code_blocks": {
                "type": "nested",
                "properties": {
                    "index": {"type": "integer"},
                    "code": {
                        "type": "text",
                        "analyzer": "code_analyzer"
                    },
                    "language": {"type": "keyword"},
                    "context": {"type": "text"},
                    "lines": {"type": "integer"}
                }
            },
            "has_code": {"type": "boolean"},
            "total_code_lines": {"type": "integer"},
            
            # Navigation
            "source_url": {"type": "keyword"},
            "breadcrumbs": {"type": "keyword"},
            
            # Metadata
            "metadata": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "description": {"type": "text"}
                }
            },
            
            # Statistics
            "word_count": {"type": "integer"},
            "indexed_at": {
                "type": "date",
                "format": "strict_date_optional_time||epoch_millis"
            }
        }
    }
}