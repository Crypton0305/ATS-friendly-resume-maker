"""
skills_db.py
------------
A lightweight built-in skill taxonomy used to detect skills mentioned in a
resume when the HR user hasn't (or in addition to what they have) supplied
an explicit required-skills list. Grouped by category purely for nicer
reporting; matching itself is flat.
"""

SKILL_TAXONOMY = {
    "Programming Languages": [
        "python", "java", "javascript", "typescript", "c++", "c#", "go",
        "golang", "rust", "ruby", "php", "swift", "kotlin", "scala", "r",
        "matlab", "sql",
    ],
    "Web & Frameworks": [
        "react", "angular", "vue", "django", "flask", "fastapi", "node.js",
        "nodejs", "express", "spring", "next.js", "streamlit", "asp.net",
    ],
    "Data & AI/ML": [
        "machine learning", "deep learning", "nlp", "computer vision",
        "pytorch", "tensorflow", "scikit-learn", "sklearn", "keras",
        "pandas", "numpy", "data analysis", "data science", "llm",
        "generative ai", "opencv", "spacy", "hugging face", "transformers",
    ],
    "Cloud & DevOps": [
        "aws", "azure", "gcp", "google cloud", "docker", "kubernetes",
        "terraform", "ci/cd", "jenkins", "ansible", "linux", "git",
        "github actions",
    ],
    "Databases": [
        "mysql", "postgresql", "postgres", "mongodb", "redis", "oracle",
        "sqlite", "elasticsearch", "cassandra", "dynamodb",
    ],
    "Soft Skills": [
        "leadership", "communication", "teamwork", "problem solving",
        "project management", "agile", "scrum", "stakeholder management",
        "mentoring", "collaboration", "critical thinking",
    ],
    "Business & Analytics": [
        "excel", "power bi", "tableau", "salesforce", "sap", "jira",
        "product management", "business analysis", "financial modeling",
    ],
}


def all_known_skills():
    flat = []
    for skills in SKILL_TAXONOMY.values():
        flat.extend(skills)
    return sorted(set(flat))
