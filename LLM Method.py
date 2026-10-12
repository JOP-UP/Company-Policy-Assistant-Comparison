import os
import json
import time
import pandas as pd
from openai import OpenAI

# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

CSV_FILE = r"C:\Users\joeel\Downloads\company_policies.csv"

MODEL = "gpt-6-luna"

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)


# --------------------------------------------------
# 1. LOAD POLICY DATABASE
# --------------------------------------------------

df = pd.read_csv(CSV_FILE)

print(f"Loaded {len(df)} policies.")


# --------------------------------------------------
# 2. CONVERT ALL POLICIES INTO TEXT FOR THE LLM
# --------------------------------------------------

policy_database = ""

for i, row in df.iterrows():

    policy_database += f"""
POLICY {i + 1}
Title: {row['title']}
Department: {row['department']}
Category: {row['category']}
Policy text: {row['policy_text']}
---
"""


# --------------------------------------------------
# 3. FUNCTION FOR ASKING THE LLM
# --------------------------------------------------

def ask_llm(question):

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

Return your response as valid JSON using exactly this format:

{{
    "answer": "your answer here",
    "relevant_policy": "policy title here or None",
    "supported_by_policy_database": true
}}

Set supported_by_policy_database to false when the database does
not contain enough information to answer the question.

COMPANY POLICY DATABASE:

{policy_database}

EMPLOYEE QUESTION:

{question}
"""

    # Start timer
    start_time = time.perf_counter()

    response = client.responses.create(
        model=MODEL,
        input=prompt
    )

    # Stop timer
    response_time = time.perf_counter() - start_time

    raw_answer = response.output_text.strip()

    # Try to parse the JSON response
    try:
        result = json.loads(raw_answer)

    except json.JSONDecodeError:

        # If the model surrounds JSON with ```json
        cleaned = raw_answer.replace("```json", "").replace("```", "").strip()

        try:
            result = json.loads(cleaned)

        except json.JSONDecodeError:
            result = {
                "answer": raw_answer,
                "relevant_policy": "Could not parse",
                "supported_by_policy_database": None
            }


    # --------------------------------------------------
    # TOKEN USAGE
    # --------------------------------------------------

    input_tokens = getattr(response.usage, "input_tokens", 0)
    output_tokens = getattr(response.usage, "output_tokens", 0)
    total_tokens = getattr(response.usage, "total_tokens", 0)


    return {
        "answer": result.get("answer"),
        "relevant_policy": result.get("relevant_policy"),
        "supported_by_policy_database":
            result.get("supported_by_policy_database"),

        "response_time": response_time,

        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens
    }


# --------------------------------------------------
# 4. ASK A QUESTION
# --------------------------------------------------

question = input("\nAsk a company policy question: ")

result = ask_llm(question)


# --------------------------------------------------
# 5. DISPLAY RESULTS
# --------------------------------------------------

print("\nRESULT")
print("=" * 60)

print("\nAnswer:")
print(result["answer"])

print("\nRelevant policy:")
print(result["relevant_policy"])

print("\nSupported by policy database:")
print(result["supported_by_policy_database"])

print(f"\nResponse time: {result['response_time']:.3f} seconds")

print(f"Input tokens: {result['input_tokens']}")
print(f"Output tokens: {result['output_tokens']}")
print(f"Total tokens: {result['total_tokens']}")