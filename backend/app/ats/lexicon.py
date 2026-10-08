"""Skills taxonomy used for deterministic keyword extraction and matching.

ALIASES are true equivalents (same technology, different spelling) and count as a match.
RELATED are defensible partial relations (e.g. Scrum -> Agile) and count as partial evidence.
Unrelated technologies are never treated as equivalent (Django != React, AWS != Azure).
"""
from __future__ import annotations

CATEGORIES: dict[str, list[str]] = {
    "programming_language": [
        "Python", "Java", "JavaScript", "TypeScript", "C", "C++", "C#", "Go", "Rust", "Ruby", "PHP", "Kotlin",
        "Swift", "Objective-C", "Scala", "R", "MATLAB", "Perl", "Dart", "Elixir", "Haskell", "Lua", "Bash",
        "Shell scripting", "PowerShell", "SQL", "PL/SQL", "T-SQL", "HTML", "CSS", "SASS", "VBA", "Groovy",
        "Clojure", "F#", "Julia", "Solidity", "COBOL", "Fortran", "Assembly",
    ],
    "framework": [
        "Django", "Flask", "FastAPI", "Spring", "Spring Boot", "Hibernate", "Express", "NestJS", "Next.js",
        "React", "React Native", "Angular", "Vue.js", "Svelte", "Nuxt.js", "Redux", "Node.js", ".NET",
        "ASP.NET", "Entity Framework", "Laravel", "Symfony", "Ruby on Rails", "Rails", "jQuery", "Bootstrap",
        "Tailwind CSS", "Flutter", "Xamarin", "Electron", "Celery", "SQLAlchemy", "Pandas", "NumPy", "SciPy",
        "scikit-learn", "TensorFlow", "PyTorch", "Keras", "Hugging Face", "LangChain", "Spark", "PySpark",
        "Hadoop", "Airflow", "dbt", "Kafka Streams", "GraphQL", "gRPC", "Pydantic", "JUnit", "pytest", "Jest",
        "Mocha", "Cypress", "Selenium", "Playwright", "Storybook", "Webpack", "Vite", "Gin", "Fiber", "Micronaut",
        "Quarkus", "OpenCV", "Matplotlib", "Streamlit", "Unity", "Unreal Engine",
    ],
    "database": [
        "PostgreSQL", "MySQL", "MariaDB", "SQLite", "Oracle", "SQL Server", "MongoDB", "Redis", "Cassandra",
        "DynamoDB", "Elasticsearch", "OpenSearch", "Neo4j", "CouchDB", "Firebase", "Firestore", "Snowflake",
        "BigQuery", "Redshift", "Databricks", "ClickHouse", "InfluxDB", "Memcached", "Supabase", "Cosmos DB",
        "Pinecone", "Teradata",
    ],
    "cloud": [
        "AWS", "Azure", "GCP", "EC2", "S3", "Lambda", "ECS", "EKS", "Fargate", "CloudFormation", "CloudWatch",
        "RDS", "SQS", "SNS", "API Gateway", "IAM", "Route 53", "Azure Functions", "Azure DevOps", "App Engine",
        "Cloud Run", "Heroku", "Vercel", "Netlify", "DigitalOcean", "Cloudflare", "OpenShift", "Serverless",
        "Cloud computing",
    ],
    "tool": [
        "Docker", "Kubernetes", "Terraform", "Ansible", "Puppet", "Chef", "Jenkins", "GitHub Actions",
        "GitLab CI", "CircleCI", "Travis CI", "Argo CD", "Helm", "Prometheus", "Grafana", "Datadog", "New Relic",
        "Splunk", "ELK", "Kibana", "Logstash", "Git", "GitHub", "GitLab", "Bitbucket", "Jira", "Confluence",
        "Trello", "Asana", "Postman", "Swagger", "OpenAPI", "Nginx", "Apache", "Linux", "Unix", "Windows Server",
        "RabbitMQ", "Kafka", "ActiveMQ", "Vagrant", "Packer", "Vault", "Consul", "Istio", "SonarQube", "Maven",
        "Gradle", "npm", "Yarn", "Figma", "Sketch", "Adobe XD", "Photoshop", "Illustrator", "Tableau",
        "Power BI", "Looker", "Excel", "SAP", "Salesforce", "HubSpot", "ServiceNow", "Zendesk", "Slack",
        "VS Code", "IntelliJ", "Xcode", "Android Studio", "Snyk", "Sentry", "PagerDuty", "OpenTelemetry",
        "Microsoft Office", "Google Analytics", "QuickBooks", "AutoCAD", "SolidWorks",
    ],
    "methodology": [
        "Agile", "Scrum", "Kanban", "Waterfall", "Lean", "Six Sigma", "DevOps", "DevSecOps", "MLOps",
        "CI/CD", "TDD", "BDD", "Pair programming", "Code review", "Infrastructure as Code", "GitOps", "SRE",
        "Microservices", "Event-driven architecture", "Domain-driven design", "Object-oriented programming",
        "Functional programming", "Design patterns", "SOLID", "Clean architecture", "REST API", "SOAP",
        "Unit testing", "Integration testing", "Automated testing", "Load testing", "ITIL", "PRINCE2", "PMP",
        "OKRs", "SAFe", "Continuous improvement", "A/B testing", "Data modeling", "ETL", "Data warehousing",
        "System design", "Distributed systems", "Containerization", "Orchestration", "Monitoring", "Observability",
        "Caching", "Performance optimization", "Security best practices", "OAuth", "JWT", "SSO",
    ],
    "technical_skill": [
        "Machine learning", "Deep learning", "Artificial intelligence", "NLP", "Computer vision",
        "Generative AI", "LLM", "Data analysis", "Data science", "Data engineering", "Data visualization",
        "Statistics", "Big data", "Backend development", "Frontend development", "Full-stack development",
        "Web development", "Mobile development", "API development", "API design", "Database design",
        "Cloud architecture", "Networking", "Cybersecurity", "Penetration testing", "Embedded systems",
        "Blockchain", "UI/UX", "Responsive design", "Accessibility", "SEO", "Business intelligence",
        "Reporting", "Automation", "Scripting", "Debugging", "Troubleshooting", "Technical documentation",
        "Software development", "Software engineering", "Quality assurance", "Manual testing",
        "Requirements gathering", "Business analysis", "Project management", "Product management",
        "Stakeholder management", "Budgeting", "Forecasting", "Financial analysis", "Financial modeling",
        "Accounting", "Auditing", "Risk management", "Compliance", "Customer service", "Sales", "Marketing",
        "Digital marketing", "Content writing", "Copywriting", "Recruitment", "Supply chain", "Logistics",
        "Procurement", "Inventory management", "Operations management", "Vendor management",
    ],
    "soft_skill": [
        "Communication", "Leadership", "Teamwork", "Collaboration", "Problem solving", "Critical thinking",
        "Mentoring", "Time management", "Adaptability", "Attention to detail", "Presentation",
        "Negotiation", "Analytical skills", "Cross-functional collaboration", "Ownership", "Self-motivated",
        "Organizational skills", "Interpersonal skills", "Decision making", "Coaching",
    ],
}

ALIASES: dict[str, list[str]] = {
    "REST API": ["REST APIs", "RESTful API", "RESTful APIs", "RESTful services", "RESTful web services",
                 "REST services", "RESTful", "REST"],
    "PostgreSQL": ["Postgres", "psql"],
    "AWS": ["Amazon Web Services"],
    "GCP": ["Google Cloud", "Google Cloud Platform"],
    "Azure": ["Microsoft Azure"],
    "Kubernetes": ["K8s"],
    "JavaScript": ["ECMAScript", "ES6"],
    "Node.js": ["NodeJS", "Node"],
    "React": ["React.js", "ReactJS"],
    "Vue.js": ["Vue", "VueJS"],
    "Next.js": ["NextJS"],
    "Express": ["Express.js", "ExpressJS"],
    "CI/CD": ["continuous integration", "continuous delivery", "continuous deployment", "CI CD", "CICD"],
    "Machine learning": ["ML"],
    "Artificial intelligence": ["AI"],
    "NLP": ["natural language processing"],
    "LLM": ["large language models", "large language model", "LLMs"],
    "Golang": ["Go"],
    "Go": ["Golang"],
    "C#": ["C sharp", "CSharp"],
    ".NET": ["dotnet", ".NET Core", "ASP.NET Core"],
    "SQL Server": ["MSSQL", "Microsoft SQL Server"],
    "Elasticsearch": ["Elastic Search"],
    "Infrastructure as Code": ["IaC"],
    "TDD": ["test-driven development", "test driven development"],
    "BDD": ["behavior-driven development", "behaviour-driven development"],
    "Object-oriented programming": ["OOP", "object oriented programming", "object-oriented design", "OOD"],
    "Shell scripting": ["shell scripts", "shell script", "bash scripting"],
    "Microservices": ["microservice", "micro-services", "microservice architecture"],
    "Backend development": ["back-end development", "backend engineering", "back end development",
                            "backend services", "back-end services", "server-side development"],
    "Frontend development": ["front-end development", "frontend engineering", "front end development"],
    "Full-stack development": ["full stack development", "fullstack development", "full-stack engineering"],
    "Unit testing": ["unit tests"],
    "Code review": ["code reviews", "reviewing code"],
    "Pair programming": ["pairing"],
    "Mentoring": ["mentored", "mentor", "mentorship"],
    "Communication": ["communication skills", "communicating"],
    "Problem solving": ["problem-solving", "solving problems"],
    "Collaboration": ["collaborated", "collaborative", "collaborating"],
    "Leadership": ["led", "leading", "lead"],
    "Data visualization": ["data visualisation"],
    "Performance optimization": ["performance optimisation", "performance tuning", "optimized performance",
                                 "optimised performance", "query optimisation", "query optimization"],
    "Caching": ["cache", "cached"],
    "Containerization": ["containerisation", "containerized", "containerised"],
    "Automation": ["automated", "automating", "automate"],
    "Power BI": ["PowerBI"],
    "Excel": ["Microsoft Excel", "MS Excel"],
    "Microsoft Office": ["MS Office", "Office 365", "Microsoft 365"],
    "GitHub Actions": ["GH Actions"],
    "Six Sigma": ["6 Sigma"],
    "UI/UX": ["UX/UI", "user experience", "UX design", "UI design"],
    "Cloud computing": ["cloud"],
    "Spring Boot": ["SpringBoot"],
    "scikit-learn": ["sklearn", "scikit learn"],
    "Ruby on Rails": ["Rails", "RoR"],
}

# Defensible partial relations: having the right side is partial evidence of the left side.
RELATED: dict[str, list[str]] = {
    "Agile": ["Scrum", "Kanban", "sprints", "sprint", "SAFe"],
    "Cloud computing": ["AWS", "Azure", "GCP"],
    "Containerization": ["Docker", "Kubernetes", "Podman"],
    "Orchestration": ["Kubernetes", "ECS", "Docker Swarm", "Nomad"],
    "CI/CD": ["GitHub Actions", "Jenkins", "GitLab CI", "CircleCI", "Travis CI", "Argo CD", "pipelines"],
    "DevOps": ["CI/CD", "Docker", "Kubernetes", "Terraform", "Ansible", "Jenkins", "GitHub Actions"],
    "Infrastructure as Code": ["Terraform", "CloudFormation", "Ansible", "Pulumi"],
    "Monitoring": ["Prometheus", "Grafana", "Datadog", "CloudWatch", "New Relic", "Splunk"],
    "Observability": ["OpenTelemetry", "Prometheus", "Grafana", "Datadog"],
    "Serverless": ["Lambda", "Azure Functions", "Cloud Run"],
    "API development": ["REST API", "GraphQL", "gRPC", "FastAPI"],
    "API design": ["REST API", "OpenAPI", "Swagger"],
    "Backend development": ["Django", "FastAPI", "Flask", "Spring Boot", "Express", "Node.js", "backend"],
    "Frontend development": ["React", "Angular", "Vue.js", "Svelte", "frontend", "front-end"],
    "Unit testing": ["pytest", "JUnit", "Jest", "Mocha"],
    "Automated testing": ["pytest", "JUnit", "Jest", "Selenium", "Cypress", "Playwright", "unit tests"],
    "Database design": ["schemas", "schema design", "data modeling"],
    "Data modeling": ["schemas", "schema design"],
    "Machine learning": ["scikit-learn", "TensorFlow", "PyTorch", "Keras"],
    "Deep learning": ["TensorFlow", "PyTorch", "Keras"],
    "Version control": ["Git", "GitHub", "GitLab", "Bitbucket"],
    "Distributed systems": ["Microservices", "Kafka", "Cassandra"],
    "Software development": ["Software engineering", "developed", "built applications"],
    "Teamwork": ["Collaboration", "cross-functional"],
    "Message queues": ["RabbitMQ", "Kafka", "SQS", "Celery"],
}

# Short/ambiguous terms that must be matched case-sensitively.
CASE_SENSITIVE = {"Go", "R", "C", "Rails", "Lean", "Chef", "Puppet", "Spring", "Express", "Lambda", "Node", "AI",
                  "ML", "Unity", "Swift", "Dart", "Apache", "SAP", "Excel", "Oracle", "Slack", "Sales", "Vue",
                  "REST", "IAM", "SNS", "SQS", "RDS", "ELK", "SSO", "JWT", "Gin", "Fiber", "Vault", "Consul",
                  "Helm", "Packer", "Lead", "lead"}

TERM_CATEGORY: dict[str, str] = {t.lower(): cat for cat, terms in CATEGORIES.items() for t in terms}
ALL_TERMS: list[str] = [t for terms in CATEGORIES.values() for t in terms]

# Terms we never auto-extract from free text because they are too generic on their own.
NOT_EXTRACTABLE = {"c", "r", "go", "lean", "chef", "puppet", "spring", "express", "lambda", "presentation",
                   "reporting", "sales", "ownership", "rails", "apache", "unity", "swift", "dart", "excel",
                   "oracle", "slack", "monitoring", "caching", "automation", "scripting", "solid", "lead"}


def category_of(term: str) -> str:
    return TERM_CATEGORY.get(term.lower(), "other")
