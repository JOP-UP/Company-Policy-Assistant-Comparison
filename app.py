import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from openai import OpenAI

load_dotenv()

# ============================================================
# SETTINGS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "data", "company_policies.csv")
VECTOR_INDEX_FILE = os.path.join(BASE_DIR, "data", "policy_embeddings.json")

EMBEDDING_MODEL = os.environ.get(
    "EMBEDDING_MODEL",
    "text-embedding-3-small"
)
LLM_MODEL = os.environ.get(
    "LLM_MODEL",
    "gpt-6-luna"
)

TOP_N = 3
MAX_QUESTION_CHARS = 1000

app = Flask(__name__)

if not os.environ.get("OPENAI_API_KEY"):
    raise RuntimeError(
        "OPENAI_API_KEY is not set. Add it to your environment "
        "or a local .env file before starting the app."
    )

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


# ============================================================
# LOAD POLICY DATABASE
# ============================================================

df = pd.read_csv(CSV_FILE)

required_columns = {
    "title",
    "department",
    "policy_text",
    "category"
}

missing_columns = required_columns - set(df.columns)

if missing_columns:
    raise RuntimeError(
        "Policy CSV is missing columns: "
        + ", ".join(sorted(missing_columns))
    )

df["embedding_text"] = (
    "Title: " + df["title"].fillna("").astype(str)
    + "\nDepartment: " + df["department"].fillna("").astype(str)
    + "\nCategory: " + df["category"].fillna("").astype(str)
    + "\nPolicy: " + df["policy_text"].fillna("").astype(str)
)


# ============================================================
# RULES-BASED BASELINE
# ============================================================

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "to", "of", "for",
    "from", "in", "on", "at", "by", "with", "about", "is", "are",
    "was", "were", "be", "do", "does", "did", "can", "could", "may",
    "might", "must", "should", "would", "will", "i", "me", "my",
    "we", "our", "you", "your", "they", "their", "it", "this",
    "that", "how", "what", "when", "where", "why", "who", "which",
    "have", "has", "had", "company", "employee", "employees", "policy"
}

SYNONYMS = {
    "holiday": {"vacation"},
    "holidays": {"vacation"},
    "pto": {"vacation"},
    "expense": {"expenses", "reimbursement", "spending", "cost"},
    "expenses": {"expense", "reimbursement", "spending", "cost"},
    "password": {"passwords", "credential", "credentials"},
    "vehicle": {"car", "cars"},
    "car": {"vehicle"},
    "gift": {"gifts", "present", "presents"},
    "harassment": {"bullying"},
    "sick": {"ill", "illness"},
    "parental": {"maternity", "paternity"},
    "bereavement": {"funeral"},
    "software": {"program", "application", "app"},
}


def tokenize(text):
    words = re.findall(r"[a-z0-9$]+", str(text).lower())
    return [word for word in words if word not in STOPWORDS]


def expand_tokens(tokens):
    expanded = set(tokens)

    for token in tokens:
        if token in SYNONYMS:
            expanded.update(SYNONYMS[token])

        for key, values in SYNONYMS.items():
            if token in values:
                expanded.add(key)

    return expanded


def score_policy(question, row):
    question_tokens = expand_tokens(tokenize(question))

    title_tokens = set(tokenize(row["title"]))
    policy_tokens = set(tokenize(row["policy_text"]))
    category_tokens = set(tokenize(row["category"]))
    department_tokens = set(tokenize(row["department"]))

    score = 0

    score += 4 * len(question_tokens & title_tokens)
    score += 2 * len(question_tokens & policy_tokens)
    score += 1 * len(question_tokens & category_tokens)
    score += 0.5 * len(question_tokens & department_tokens)

    question_numbers = set(re.findall(r"\d+", question))
    policy_numbers = set(re.findall(r"\d+", str(row["policy_text"])))

    score += 4 * len(question_numbers & policy_numbers)

    return score


def rules_based_method(question):
    start = time.perf_counter()

    results = df.copy()
    results["score"] = results.apply(
        lambda row: score_policy(question, row),
        axis=1
    )
    results = results.sort_values("score", ascending=False)
    best = results.iloc[0]

    response_time = time.perf_counter() - start

    if float(best["score"]) < 6:
        return {
            "method": "Rules-based",
            "answer": "No relevant policy was found in the policy database.",
            "relevant_policy": "None",
            "supported_by_policy_database": False,
            "response_time": response_time,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "match_score": float(best["score"]),
        }

    return {
        "method": "Rules-based",
        "answer": str(best["policy_text"]),
        "relevant_policy": str(best["title"]),
        "supported_by_policy_database": True,
        "response_time": response_time,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "match_score": float(best["score"]),
    }


# ============================================================
# COMMON LLM HELPERS
# ============================================================

def clean_json_response(raw_output):
    cleaned = (
        raw_output
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "answer": raw_output,
            "relevant_policy": "Could not parse response",
            "supported_by_policy_database": None,
        }


def llm_result(response, response_time, method):
    parsed = clean_json_response(response.output_text.strip())

    usage = response.usage

    return {
        "method": method,
        "answer": parsed.get("answer"),
        "relevant_policy": parsed.get("relevant_policy"),
        "supported_by_policy_database": parsed.get(
            "supported_by_policy_database"
        ),
        "response_time": response_time,
        "input_tokens": getattr(usage, "input_tokens", 0),
        "output_tokens": getattr(usage, "output_tokens", 0),
        "total_tokens": getattr(usage, "total_tokens", 0),
    }


# ============================================================
# LLM-ONLY METHOD
# ============================================================

POLICY_DATABASE_TEXT = "\n".join(
    f"""POLICY {i + 1}
Title: {row['title']}
Department: {row['department']}
Category: {row['category']}
Policy text: {row['policy_text']}
---"""
    for i, (_, row) in enumerate(df.iterrows())
)


def llm_only_method(question):
    prompt = f"""
You are a company policy assistant.

Below is the COMPLETE company policy database.

Answer the employee's question using ONLY information contained
in this policy database.

Rules:
1. Do not use outside knowledge.
2. Do not invent company rules.
3. Identify the specific policy that supports your answer.
4. If the database does not contain enough information to answer
   the question, clearly say so.
5. If no policy supports the answer, use "None" as the relevant policy.

Return valid JSON exactly like this:

{{
  "answer": "your answer here",
  "relevant_policy": "exact policy title or None",
  "supported_by_policy_database": true
}}

Set "supported_by_policy_database" to false when the database
does not contain enough information to answer the question.

COMPANY POLICY DATABASE:

{POLICY_DATABASE_TEXT}

EMPLOYEE QUESTION:

{question}
"""

    start = time.perf_counter()

    response = client.responses.create(
        model=LLM_MODEL,
        input=prompt
    )

    response_time = time.perf_counter() - start

    return llm_result(
        response=response,
        response_time=response_time,
        method="LLM only"
    )


# ============================================================
# VECTOR INDEX
# ============================================================

_policy_embeddings = None


def create_policy_embeddings():
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=df["embedding_text"].tolist()
    )

    embeddings = [
        item.embedding
        for item in response.data
    ]

    payload = {
        "embedding_model": EMBEDDING_MODEL,
        "policy_count": len(df),
        "embeddings": embeddings,
    }

    os.makedirs(
        os.path.dirname(VECTOR_INDEX_FILE),
        exist_ok=True
    )

    with open(
        VECTOR_INDEX_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(payload, file)

    return embeddings


def load_policy_embeddings():
    global _policy_embeddings

    if _policy_embeddings is not None:
        return _policy_embeddings

    if os.path.exists(VECTOR_INDEX_FILE):
        with open(
            VECTOR_INDEX_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            payload = json.load(file)

        valid_cache = (
            payload.get("embedding_model") == EMBEDDING_MODEL
            and payload.get("policy_count") == len(df)
            and len(payload.get("embeddings", [])) == len(df)
        )

        if valid_cache:
            embeddings = payload["embeddings"]
        else:
            embeddings = create_policy_embeddings()
    else:
        embeddings = create_policy_embeddings()

    _policy_embeddings = np.array(
        embeddings,
        dtype=np.float32
    )

    return _policy_embeddings


def embed_question(question):
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=question
    )

    return np.array(
        response.data[0].embedding,
        dtype=np.float32
    )


def cosine_similarities(question_vector, policy_vectors):
    question_norm = np.linalg.norm(question_vector)

    policy_norms = np.linalg.norm(
        policy_vectors,
        axis=1
    )

    denominator = policy_norms * question_norm

    denominator = np.where(
        denominator == 0,
        1e-12,
        denominator
    )

    return (
        policy_vectors @ question_vector
    ) / denominator


def retrieve_policies(question):
    policy_vectors = load_policy_embeddings()
    question_vector = embed_question(question)

    similarities = cosine_similarities(
        question_vector,
        policy_vectors
    )

    results = df.copy()
    results["similarity"] = similarities

    return (
        results
        .sort_values(
            "similarity",
            ascending=False
        )
        .head(TOP_N)
    )


# ============================================================
# LLM + VECTOR / RAG METHOD
# ============================================================

def vector_method(question):
    retrieved = retrieve_policies(question)

    context = ""

    for number, (_, row) in enumerate(
        retrieved.iterrows(),
        start=1
    ):
        context += f"""
POLICY {number}
Title: {row['title']}
Department: {row['department']}
Category: {row['category']}
Policy text: {row['policy_text']}
---
"""

    prompt = f"""
You are a company policy assistant.

Answer the employee's question using ONLY the policies provided below.

Rules:
1. Do not use outside knowledge.
2. Do not invent company rules.
3. Select the policy that actually supports the answer.
4. If none of the supplied policies contains enough information,
   say that the policy database does not provide enough information.
5. Give a concise answer.
6. State the exact title of the relevant policy.
7. If no policy supports the answer, use "None".

Return valid JSON exactly like this:

{{
  "answer": "answer here",
  "relevant_policy": "exact policy title or None",
  "supported_by_policy_database": true
}}

Set "supported_by_policy_database" to false if the supplied
policies do not contain enough information.

RETRIEVED POLICIES:

{context}

EMPLOYEE QUESTION:

{question}
"""

    # Per your benchmark design, only the LLM generation time and
    # LLM token usage are reported for this method. Embedding and
    # vector-retrieval time/token usage are intentionally excluded.
    start = time.perf_counter()

    response = client.responses.create(
        model=LLM_MODEL,
        input=prompt
    )

    response_time = time.perf_counter() - start

    result = llm_result(
        response=response,
        response_time=response_time,
        method="LLM + Vector"
    )

    result["retrieved_policies"] = [
        {
            "title": str(row["title"]),
            "similarity": round(
                float(row["similarity"]),
                4
            ),
        }
        for _, row in retrieved.iterrows()
    ]

    return result


# ============================================================
# SAFE METHOD WRAPPER
# ============================================================

def safe_run(method_name, function, question):
    try:
        return function(question)
    except Exception as error:
        app.logger.exception(
            "%s failed",
            method_name
        )

        return {
            "method": method_name,
            "error": str(error),
            "answer": None,
            "relevant_policy": None,
            "supported_by_policy_database": None,
            "response_time": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
        }


# ============================================================
# ROUTES
# ============================================================

@app.get("/")
def home():
    return render_template(
        "index.html",
        policy_count=len(df),
        llm_model=LLM_MODEL,
        embedding_model=EMBEDDING_MODEL,
    )


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "policies": len(df),
    })


@app.post("/api/compare")
def compare():
    data = request.get_json(silent=True) or {}

    question = str(
        data.get("question", "")
    ).strip()

    if not question:
        return jsonify({
            "error": "Please enter a policy question."
        }), 400

    if len(question) > MAX_QUESTION_CHARS:
        return jsonify({
            "error": (
                f"Question is too long. "
                f"Maximum length is {MAX_QUESTION_CHARS} characters."
            )
        }), 400

    rules_result = safe_run(
        "Rules-based",
        rules_based_method,
        question
    )

    # Run the two API-based methods concurrently so the user does
    # not have to wait for them one after another.
    with ThreadPoolExecutor(
        max_workers=2
    ) as executor:
        llm_future = executor.submit(
            safe_run,
            "LLM only",
            llm_only_method,
            question
        )

        vector_future = executor.submit(
            safe_run,
            "LLM + Vector",
            vector_method,
            question
        )

        llm_result_data = llm_future.result()
        vector_result_data = vector_future.result()

    return jsonify({
        "question": question,
        "results": {
            "rules": rules_result,
            "llm": llm_result_data,
            "vector": vector_result_data,
        }
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=True,
    )
