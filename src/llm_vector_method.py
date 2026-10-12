import os
import json
import time
import numpy as np
import pandas as pd
from openai import OpenAI


# ============================================================
# SETTINGS
# ============================================================

CSV_FILE = r"C:\Users\joeel\Downloads\company_policies.csv"

EMBEDDING_CACHE = "policy_embeddings.json"

EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-6-luna"

TOP_N = 3

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)


# ============================================================
# 1. LOAD POLICIES
# ============================================================

df = pd.read_csv(CSV_FILE)

df["embedding_text"] = (
    "Title: " + df["title"].fillna("").astype(str)
    + "\nDepartment: " + df["department"].fillna("").astype(str)
    + "\nCategory: " + df["category"].fillna("").astype(str)
    + "\nPolicy: " + df["policy_text"].fillna("").astype(str)
)


# ============================================================
# 2. CREATE OR LOAD POLICY EMBEDDINGS
# ============================================================

def create_policy_embeddings():

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=df["embedding_text"].tolist()
    )

    embeddings = [
        item.embedding
        for item in response.data
    ]

    with open(
        EMBEDDING_CACHE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(embeddings, f)

    return embeddings


if os.path.exists(EMBEDDING_CACHE):

    with open(
        EMBEDDING_CACHE,
        "r",
        encoding="utf-8"
    ) as f:
        policy_embeddings = json.load(f)

else:

    policy_embeddings = create_policy_embeddings()


policy_embeddings = [
    np.array(vector)
    for vector in policy_embeddings
]


# ============================================================
# 3. EMBED QUESTION
# ============================================================

def embed_question(question):

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=question
    )

    return np.array(
        response.data[0].embedding
    )


# ============================================================
# 4. COSINE SIMILARITY
# ============================================================

def cosine_similarity(a, b):

    return np.dot(a, b) / (
        np.linalg.norm(a)
        * np.linalg.norm(b)
    )


# ============================================================
# 5. RETRIEVE TOP 3 POLICIES
# ============================================================

def retrieve_policies(question):

    question_vector = embed_question(question)

    similarities = []

    for policy_vector in policy_embeddings:

        similarity = cosine_similarity(
            question_vector,
            policy_vector
        )

        similarities.append(similarity)

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
# 6. SEND TOP 3 POLICIES TO LLM
# ============================================================

def generate_answer(question, retrieved_policies):

    context = ""

    for number, (_, row) in enumerate(
        retrieved_policies.iterrows(),
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

Answer the employee's question using ONLY the policies
provided below.

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

RETRIEVED POLICIES:

{context}

EMPLOYEE QUESTION:

{question}
"""

    # Only measure the LLM response
    start_time = time.perf_counter()

    response = client.responses.create(
        model=LLM_MODEL,
        input=prompt
    )

    response_time = (
        time.perf_counter()
        - start_time
    )

    raw_output = response.output_text.strip()

    cleaned = (
        raw_output
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:
        result = json.loads(cleaned)

    except json.JSONDecodeError:
        result = {
            "answer": raw_output,
            "relevant_policy": "Could not parse response",
            "supported_by_policy_database": None
        }


    input_tokens = getattr(
        response.usage,
        "input_tokens",
        0
    )

    output_tokens = getattr(
        response.usage,
        "output_tokens",
        0
    )

    total_tokens = getattr(
        response.usage,
        "total_tokens",
        0
    )


    return {
        "answer": result.get("answer"),
        "relevant_policy": result.get("relevant_policy"),
        "supported": result.get(
            "supported_by_policy_database"
        ),
        "response_time": response_time,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens
    }


# ============================================================
# 7. ASK QUESTION
# ============================================================

question = input(
    "\nAsk a company policy question: "
)

retrieved_policies = retrieve_policies(question)

result = generate_answer(
    question,
    retrieved_policies
)


# ============================================================
# 8. DISPLAY RETRIEVED POLICIES
# ============================================================

print("\nTOP 3 VECTOR MATCHES")
print("=" * 60)

for rank, (_, row) in enumerate(
    retrieved_policies.iterrows(),
    start=1
):

    print(
        f"{rank}. {row['title']} "
        f"(Similarity: {row['similarity']:.4f})"
    )


# ============================================================
# 9. DISPLAY FINAL RESULT
# ============================================================

print("\nFINAL ANSWER")
print("=" * 60)

print("\nAnswer:")
print(result["answer"])

print("\nRelevant policy:")
print(result["relevant_policy"])

print("\nSupported by policy database:")
print(result["supported"])


# ============================================================
# 10. LLM PERFORMANCE ONLY
# ============================================================

print("\nLLM PERFORMANCE")
print("=" * 60)

print(
    f"Response time: "
    f"{result['response_time']:.3f} seconds"
)

print(
    f"Input tokens: "
    f"{result['input_tokens']}"
)

print(
    f"Output tokens: "
    f"{result['output_tokens']}"
)

print(
    f"Total tokens: "
    f"{result['total_tokens']}"
)
