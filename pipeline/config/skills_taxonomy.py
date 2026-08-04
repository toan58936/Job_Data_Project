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


    # ============================================================
    # [MỚI] Bổ sung theo dữ liệu THẬT từ unrecognized_skills.jsonl
    # (tần suất ≥ 13) + danh sách P0 trong elt_audit_report.md.
    # Đây là phương pháp gán nhãn: đọc dữ liệu thực tế, thêm vào taxonomy
    # để giảm job_skills rỗng và thu hẹp khoảng trống vocab.
    # ============================================================

    # --- IaC / DevOps / Monitoring ---
    "terraform": {"canonical": "Terraform", "aliases": ["Terraform", "Terraform Cloud"]},
    "pulumi": {"canonical": "Pulumi", "aliases": ["Pulumi"]},
    "devops": {"canonical": "DevOps", "aliases": ["DevOps", "Dev Ops"]},
    "grafana": {"canonical": "Grafana", "aliases": ["Grafana"]},
    "prometheus": {"canonical": "Prometheus", "aliases": ["Prometheus"]},
    "datadog": {"canonical": "Datadog", "aliases": ["Datadog"]},
    "monitoring": {"canonical": "Monitoring", "aliases": ["Monitoring", "Monitoring Tools"]},
    "observability": {"canonical": "Observability", "aliases": ["Observability"]},
    "gitops": {"canonical": "GitOps", "aliases": ["GitOps"]},
    "gitlab-ci": {"canonical": "GitLab CI", "aliases": ["GitLab CI", "Gitlab CI", "GitLab CI/CD"]},
    "linux": {"canonical": "Linux", "aliases": ["Linux", "Linux Server"]},

    # --- Ngôn ngữ lập trình / Framework ---
    "rust": {"canonical": "Rust", "aliases": ["Rust"]},
    "golang": {"canonical": "Go", "aliases": ["GoLang", "Golang", "Go Language"]},
    "javascript": {"canonical": "JavaScript", "aliases": ["JavaScript", "Javascript", "JS", "Node.js", "NodeJS", "Node Js"]},
    "typescript": {"canonical": "TypeScript", "aliases": ["TypeScript", "Typescript", "TS"]},
    "react": {"canonical": "React", "aliases": ["React", "React.js", "ReactJS", "React Js"]},
    "vue": {"canonical": "Vue.js", "aliases": ["Vue.js", "VueJS", "Vue Js", "Vue"]},
    "angular": {"canonical": "Angular", "aliases": ["Angular", "AngularJS"]},
    "nextjs": {"canonical": "Next.js", "aliases": ["Next.js", "NextJS", "NextJs"]},
    "svelte": {"canonical": "Svelte", "aliases": ["Svelte", "SvelteKit"]},
    "fastapi": {"canonical": "FastAPI", "aliases": ["FastAPI", "Fast Api"]},
    "spring": {"canonical": "Spring", "aliases": ["Spring", "Spring Boot", "SpringBoot"]},
    "cpp": {"canonical": "C++", "aliases": ["C++", "Cpp"]},
    "csharp": {"canonical": "C#", "aliases": ["C#", "CSharp"]},
    "microservices": {"canonical": "Microservices", "aliases": ["Microservices", "Microservice", "Micro Service"]},
    "elasticsearch": {"canonical": "Elasticsearch", "aliases": ["Elasticsearch", "Elastic Search"]},

    # --- AI / ML / Data Science ---
    "numpy": {"canonical": "NumPy", "aliases": ["NumPy", "Numpy"]},
    "pytorch": {"canonical": "PyTorch", "aliases": ["PyTorch", "Pytorch", "Torch"]},
    "tensorflow": {"canonical": "TensorFlow", "aliases": ["TensorFlow", "Tensorflow", "TF"]},
    "opencv": {"canonical": "OpenCV", "aliases": ["OpenCV"]},
    "playwright": {"canonical": "Playwright", "aliases": ["Playwright"]},
    "data-science": {"canonical": "Data Science", "aliases": ["Data Science", "DataScience", "Khoa Học Dữ Liệu"]},
    "data-analysis": {"canonical": "Data Analysis", "aliases": ["Data Analysis"]},
    "chatbot": {"canonical": "Chatbot", "aliases": ["Chatbot", "Chat Bot"]},

    # --- BI / Analytics / Visualization ---
    "tableau": {"canonical": "Tableau", "aliases": ["Tableau"]},
    "bigquery": {"canonical": "BigQuery", "aliases": ["BigQuery", "Google BigQuery", "Big Query"]},
    "quicksight": {"canonical": "QuickSight", "aliases": ["QuickSight", "Amazon QuickSight"]},
    "looker": {"canonical": "Looker", "aliases": ["Looker"]},
    "metabase": {"canonical": "Metabase", "aliases": ["Metabase"]},
    "streamlit": {"canonical": "Streamlit", "aliases": ["Streamlit"]},
    "appsflyer": {"canonical": "AppsFlyer", "aliases": ["AppsFlyer", "Appsflyer"]},

    # --- Databases / Data Engineering ---
    "oracle": {"canonical": "Oracle", "aliases": ["Oracle", "Oracle Database", "Oracle DB"]},
    "pyspark": {"canonical": "PySpark", "aliases": ["PySpark", "Pyspark"]},
    "airbyte": {"canonical": "Airbyte", "aliases": ["Airbyte"]},
    "debezium": {"canonical": "Debezium", "aliases": ["Debezium"]},
    "openmetadata": {"canonical": "OpenMetadata", "aliases": ["OpenMetadata"]},
    "n8n": {"canonical": "n8n", "aliases": ["n8n", "N8n"]},
    "apache-hudi": {"canonical": "Apache Hudi", "aliases": ["Apache Hudi", "Hudi"]},
    "great-expectations": {"canonical": "Great Expectations", "aliases": ["Great Expectations", "GreatExpectations"]},
    "monte-carlo": {"canonical": "Monte Carlo", "aliases": ["Monte Carlo"]},
    "datalake": {"canonical": "Data Lake", "aliases": ["Data Lake", "Datalake", "DataLake"]},
    "data-pipeline": {"canonical": "Data Pipeline", "aliases": ["Data Pipeline", "Data pipeline"]},
    "data-quality": {"canonical": "Data Quality", "aliases": ["Data Quality", "Data Quality Tools"]},
    "data-governance": {"canonical": "Data Governance", "aliases": ["Data Governance", "data governance"]},
    "data-mart": {"canonical": "Data Mart", "aliases": ["Data Mart", "Data Marts"]},
    "star-schema": {"canonical": "Star Schema", "aliases": ["Star schema", "Star Schema"]},
    "cdc": {"canonical": "CDC", "aliases": ["CDC", "Change Data Capture"]},
    "batch-processing": {"canonical": "Batch Processing", "aliases": ["Batch Processing"]},
    "streaming-processing": {"canonical": "Streaming Processing", "aliases": ["Streaming Processing", "Streaming"]},
    "relational-databases": {"canonical": "Relational Databases", "aliases": ["Relational Databases", "Relational database"]},
    "rest-apis": {"canonical": "REST APIs", "aliases": ["REST APIs", "REST API", "Restful API"]},
    "sqlalchemy": {"canonical": "SQLAlchemy", "aliases": ["SQLAlchemy"]},
    "pydantic": {"canonical": "Pydantic", "aliases": ["Pydantic"]},
    "firebase": {"canonical": "Firebase", "aliases": ["Firebase"]},

    # --- Chung / Cross-cutting ---
    "api": {"canonical": "API", "aliases": ["API", "Rest API", "APIs"]},
    "cloud": {"canonical": "Cloud", "aliases": ["Cloud", "Cloud Services", "Cloud Computing"]},
    "json": {"canonical": "JSON", "aliases": ["JSON", "Json"]},
    "agile": {"canonical": "Agile", "aliases": ["Agile", "Scrum"]},
    "software-architecture": {"canonical": "Software Architecture", "aliases": ["Software Architecture", "Solution Architecture"]},
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