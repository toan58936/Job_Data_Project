from typing import Any

SKILLS_TAXONOMY: dict[str, dict[str, Any]] = {
    "python": {"canonical": "Python", "aliases": ["Python", "python3", "Python3"]},
    "java": {"canonical": "Java", "aliases": ["Java", "Core Java"]},
    "nosql": {"canonical": "NoSQL", "aliases": ["NoSQL", "NoSql", "nosql"]},
    "sql": {"canonical": "SQL", "aliases": ["SQL", "Sql"]},
    "database": {"canonical": "Database", "aliases": ["Database", "Databases"]},
    "mongodb": {"canonical": "MongoDB", "aliases": ["MongoDB", "Mongo"]},
    "redis": {"canonical": "Redis", "aliases": ["Redis"]},
    "kotlin": {"canonical": "Kotlin", "aliases": ["Kotlin"]},
    "clickhouse": {"canonical": "ClickHouse", "aliases": ["Clickhouse", "ClickHouse"]},
    "aws": {"canonical": "AWS", "aliases": ["AWS", "Amazon Web Services"]},
    "aws-lambda": {"canonical": "AWS Lambda", "aliases": ["AWS Lambda", "Lambda"]},
    "aws-glue": {"canonical": "AWS Glue", "aliases": ["AWS Glue", "Glue"]},
    "pandas": {"canonical": "Pandas", "aliases": ["Pandas"]},
    "spark": {"canonical": "Spark", "aliases": ["Spark", "Apache Spark"]},
    "hadoop": {"canonical": "Hadoop", "aliases": ["Hadoop", "Apache Hadoop"]},
    "hive": {"canonical": "Hive", "aliases": ["Hive", "Apache Hive"]},
    "scala": {"canonical": "Scala", "aliases": ["Scala"]},
    "docker": {"canonical": "Docker", "aliases": ["Docker"]},
    "kubernetes": {"canonical": "Kubernetes", "aliases": ["Kubernetes", "K8s"]},
    "data-engineer": {"canonical": "Data Engineer", "aliases": ["Data Engineer", "Data Engineering"]},
    "big-data": {"canonical": "Big Data", "aliases": ["Big Data", "Bigdata"]},
    "data-modeling": {"canonical": "Data Modeling", "aliases": ["Data Modeling", "Data Model"]},
    "power-bi": {"canonical": "Power BI", "aliases": ["Power BI", "PowerBi", "Power BI Desktop"]},
    "machine-learning": {"canonical": "Machine Learning", "aliases": ["Machine Learning", "ML"]},
    "generative-ai": {"canonical": "Generative AI", "aliases": ["Generative AI", "GenAI", "AI"]},
    "kafka": {"canonical": "Kafka", "aliases": ["Kafka", "Apache Kafka", "kafka"]},
    "airflow": {"canonical": "Airflow", "aliases": ["Airflow", "Apache Airflow", "airflow"]},
    "postgresql": {"canonical": "PostgreSQL", "aliases": ["PostgreSQL", "Postgres", "postgresql", "PostgreSql"]},
    "dbt": {"canonical": "dbt", "aliases": ["dbt", "DBT"]},
    "gcp": {"canonical": "GCP", "aliases": ["GCP", "Google Cloud Platform", "Google Cloud", "gcp"]},
    "azure": {"canonical": "Azure", "aliases": ["Azure", "Microsoft Azure", "azure"]},
    "snowflake": {"canonical": "Snowflake", "aliases": ["Snowflake", "snowflake"]},
    "databricks": {"canonical": "Databricks", "aliases": ["Databricks", "databricks"]},
    "ci-cd": {"canonical": "CI/CD", "aliases": ["CI/CD", "CICD", "ci-cd", "ci/cd"]},
    "git": {"canonical": "Git", "aliases": ["Git", "git"]},
    "superset": {"canonical": "Superset", "aliases": ["Superset", "Apache Superset", "superset"]},
    "mlops": {"canonical": "MLOps", "aliases": ["MLOps"]},
    "data-lineage": {"canonical": "Data Lineage", "aliases": ["Data Lineage"]},
    "data-privacy": {"canonical": "Data Privacy/Compliance", "aliases": ["Data Privacy/Compliance", "Data Privacy", "Compliance"]},
    "project-management": {"canonical": "Project Management", "aliases": ["Project Management"]},
    "english": {"canonical": "English", "aliases": ["English"]},
    "team-management": {"canonical": "Team Management", "aliases": ["Team Management"]},
    "fresher-accepted": {"canonical": "Fresher Accepted", "aliases": ["Fresher Accepted", "freshers accepted", "Fresher"]},
    "troubleshooting": {"canonical": "Troubleshooting", "aliases": ["Troubleshooting"]},
    "async-programming": {"canonical": "Asynchronous Programming", "aliases": ["Asynchronous Programming", "Async Programming"]},
    "coroutines": {"canonical": "Coroutines", "aliases": ["Coroutines"]},
    "olap": {"canonical": "OLAP", "aliases": ["OLAP"]},
    "suspend-functions": {"canonical": "Suspend Functions", "aliases": ["Suspend Functions"]},
    "columnar-database": {"canonical": "Columnar Database", "aliases": ["Columnar Database"]},
    "performance-optimization": {"canonical": "Performance Optimization", "aliases": ["Performance Optimization"]},
    "distributed-systems": {"canonical": "Distributed Systems", "aliases": ["Distributed Systems"]},
    "high-traffic": {"canonical": "High Traffic", "aliases": ["High Traffic", "High Throughput"]},
    "etl": {"canonical": "ETL", "aliases": ["ETL", "ELT"]},
    "data-warehouse": {"canonical": "Data Warehouse", "aliases": ["Data Warehouse", "Data Warehousing"]},
    "data-lake": {"canonical": "Data Lake", "aliases": ["Data Lake"]},
    "presto": {"canonical": "Presto", "aliases": ["Presto"]},
    "pentaho": {"canonical": "Pentaho", "aliases": ["Pentaho"]},
    "hbase": {"canonical": "HBase", "aliases": ["HBase"]},
    "cassandra": {"canonical": "Cassandra", "aliases": ["Cassandra"]},

    # [MỚI] GenAI / LLM / Modern Data Stack -- bổ sung theo yêu cầu: Giai đoạn 1 đã giữ
    # nguyên các cụm "Vector Database", "RAG", "embeddings" nhà tuyển dụng gõ, nhưng
    # taxonomy trước đây chưa biết các từ này nên vẫn "mù" dù dữ liệu thô đã có sẵn.
    "llm": {"canonical": "LLM", "aliases": ["LLM", "LLMs", "Large Language Model", "Large Language Models"]},
    "agentic-ai": {"canonical": "Agentic AI", "aliases": ["Agentic AI", "AI Agent", "AI Agents"]},
    "rag": {"canonical": "RAG", "aliases": ["RAG", "Retrieval-Augmented Generation", "Retrieval Augmented Generation"]},
    "prompt-engineering": {"canonical": "Prompt Engineering", "aliases": ["Prompt Engineering"]},
    "embeddings": {"canonical": "Embeddings", "aliases": ["Embeddings", "Embedding"]},
    "vector-database": {"canonical": "Vector Database", "aliases": ["Vector Database", "Vector DB", "Vector Databases"]},
    "langchain": {"canonical": "LangChain", "aliases": ["LangChain", "Langchain"]},
    "llamaindex": {"canonical": "LlamaIndex", "aliases": ["LlamaIndex", "Llama Index"]},
    "openai-api": {"canonical": "OpenAI API", "aliases": ["OpenAI API", "OpenAI"]},
    "huggingface": {"canonical": "Hugging Face", "aliases": ["Hugging Face", "HuggingFace"]},
    "fine-tuning": {"canonical": "Fine-tuning", "aliases": ["Fine-tuning", "Finetuning", "Fine tuning"]},
    "pinecone": {"canonical": "Pinecone", "aliases": ["Pinecone"]},
    "weaviate": {"canonical": "Weaviate", "aliases": ["Weaviate"]},
    "milvus": {"canonical": "Milvus", "aliases": ["Milvus"]},
    "chromadb": {"canonical": "ChromaDB", "aliases": ["ChromaDB", "Chroma DB", "Chroma"]},
    "iceberg": {"canonical": "Apache Iceberg", "aliases": ["Apache Iceberg", "Iceberg"]},
    "delta-lake": {"canonical": "Delta Lake", "aliases": ["Delta Lake", "DeltaLake"]},
    "dagster": {"canonical": "Dagster", "aliases": ["Dagster"]},
    "fivetran": {"canonical": "Fivetran", "aliases": ["Fivetran"]},
    "trino": {"canonical": "Trino", "aliases": ["Trino"]},
}


def canonicalize_skill(skill: str) -> str:
    lowered = skill.strip().lower()
    for entry in SKILLS_TAXONOMY.values():
        if lowered in (a.lower() for a in entry["aliases"]):
            return entry["canonical"]
    return skill.strip()


def build_flashtext_keyword_processor():
    from flashtext import KeywordProcessor

    kp = KeywordProcessor(case_sensitive=False)
    for entry in SKILLS_TAXONOMY.values():
        for alias in entry["aliases"]:
            kp.add_keyword(alias, entry["canonical"])
    return kp