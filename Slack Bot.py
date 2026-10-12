import os
import re
import json
import time

import numpy as np
import pandas as pd

from openai import OpenAI
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler


# ============================================================
# SETTINGS
# ============================================================

CSV_FILE = r"C:\Users\joeel\Downloads\company_policies.csv"

EMBEDDING_CACHE = "policy_embeddings.json"

EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-6-luna"

TOP_N = 3


# ============================================================
# CHECK ENVIRONMENT VARIABLES
# ============================================================

required_variables = [
    "OPENAI_API_KEY",
    "SLACK_BOT_TOKEN",
    "SLACK_APP_TOKEN"
]

for variable in required_variables:
    if not os.environ.get(variable):
        raise ValueError(
            f"{variable} is not set as an environment variable."
        )


# ============================================================
# OPENAI CLIENT
# ============================================================

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)


# ============================================================
# SLACK APP
# ============================================================

app = App(
    token=os.environ["SLACK_BOT_TOKEN"]
)


# ============================================================
# 1. LOAD POLICIES
# ============================================================

df = pd.read_csv(CSV_FILE)

print(f"Loaded {len(df)} policies.")


df["embedding_text"] = (
    "Title: " + df["title"].fillna("").astype(str)
    + "\nDepartment: " + df["department"].fillna("").astype(str)
    + "\nCategory: " + df["category"].fillna("").astype(str)
    + "\nPolicy: " + df["policy_text"].fillna("").astype(str)
)


# ============================================================
# 2. CREATE POLICY EMBEDDINGS
# ============================================================

def create_policy_embeddings():

    print("Creating policy embeddings...")

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

        json.dump(
            embeddings,
            f
        )

    print(
        f"Created and saved "
        f"{len(embeddings)} policy embeddings."
    )

    return embeddings


# ============================================================
# 3. LOAD OR CREATE POLICY EMBEDDINGS
# ============================================================

if os.path.exists(EMBEDDING_CACHE):

    print("Loading saved policy embeddings...")

    with open(
        EMBEDDING_CACHE,
        "r",
        encoding="utf-8"
    ) as f:

        policy_embeddings = json.load(f)

    # Recreate embeddings if the CSV has changed in size
    if len(policy_embeddings) != len(df):

        print(
            "Policy database has changed. "
            "Recreating embeddings..."
        )

        policy_embeddings = create_policy_embeddings()

else:

    policy_embeddings = create_policy_embeddings()


policy_embeddings = [
    np.array(vector)
    for vector in policy_embeddings
]


# ============================================================
# 4. EMBED QUESTION
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
# 5. COSINE SIMILARITY
# ============================================================

def cosine_similarity(a, b):

    return np.dot(a, b) / (
        np.linalg.norm(a)
        * np.linalg.norm(b)
    )


# ============================================================
# 6. RETRIEVE TOP 3 POLICIES
# ============================================================

def retrieve_policies(question):

    question_vector = embed_question(
        question
    )

    similarities = []

    for policy_vector in policy_embeddings:

        similarity = cosine_similarity(
            question_vector,
            policy_vector
        )

        similarities.append(
            similarity
        )

    results = df.copy()

    results["similarity"] = similarities

    results = (
        results
        .sort_values(
            "similarity",
            ascending=False
        )
        .head(TOP_N)
    )

    return results


# ============================================================
# 7. SEND RETRIEVED POLICIES TO LLM
# ============================================================

def generate_answer(
    question,
    retrieved_policies
):

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
5. Give a concise and clear answer.
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

    start_time = time.perf_counter()

    response = client.responses.create(
        model=LLM_MODEL,
        input=prompt
    )

    response_time = (
        time.perf_counter()
        - start_time
    )

    raw_output = (
        response.output_text
        .strip()
    )

    cleaned = (
        raw_output
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:

        result = json.loads(
            cleaned
        )

    except json.JSONDecodeError:

        result = {
            "answer": raw_output,
            "relevant_policy":
                "Could not parse response",
            "supported_by_policy_database":
                None
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
        "answer":
            result.get("answer"),

        "relevant_policy":
            result.get(
                "relevant_policy"
            ),

        "supported":
            result.get(
                "supported_by_policy_database"
            ),

        "response_time":
            response_time,

        "input_tokens":
            input_tokens,

        "output_tokens":
            output_tokens,

        "total_tokens":
            total_tokens
    }


# ============================================================
# 8. SLACK EVENT HANDLER
# ============================================================

@app.event("app_mention")
def handle_mention(
    event,
    say
):

    try:

        # Original Slack message
        message_text = event.get(
            "text",
            ""
        )

        # Slack sends mentions like:
        # <@U12345678> Can I work from Spain?
        #
        # Remove the bot mention from the question.
        question = re.sub(
            r"<@[A-Z0-9]+>",
            "",
            message_text
        ).strip()


        # If the user only writes @Bot with no question
        if not question:

            say(
                "Please ask me a company policy question."
            )

            return


        print("\n" + "=" * 60)

        print(
            f"Slack question: "
            f"{question}"
        )


        # ====================================================
        # VECTOR RETRIEVAL
        # ====================================================

        retrieved_policies = retrieve_policies(
            question
        )


        print("\nTOP 3 VECTOR MATCHES")

        for rank, (_, row) in enumerate(
            retrieved_policies.iterrows(),
            start=1
        ):

            print(
                f"{rank}. "
                f"{row['title']} "
                f"(Similarity: "
                f"{row['similarity']:.4f})"
            )


        # ====================================================
        # LLM ANSWER
        # ====================================================

        result = generate_answer(
            question,
            retrieved_policies
        )


        # ====================================================
        # TERMINAL INFORMATION
        # ====================================================

        print("\nFINAL ANSWER")

        print(
            result["answer"]
        )

        print(
            f"Relevant policy: "
            f"{result['relevant_policy']}"
        )

        print(
            f"Supported: "
            f"{result['supported']}"
        )


        print("\nLLM PERFORMANCE")

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


        # ====================================================
        # SEND ANSWER BACK TO SLACK
        # ====================================================

        slack_message = (
            f"{result['answer']}\n\n"
            f"*Relevant policy:* "
            f"{result['relevant_policy']}"
        )

        say(
            slack_message
        )


    except Exception as error:

        print(
            "\nERROR:"
        )

        print(
            error
        )

        say(
            "Sorry, an error occurred while "
            "processing the policy question."
        )


# ============================================================
# 9. START SLACK BOT
# ============================================================

if __name__ == "__main__":

    print("\nCompany Policy Assistant starting...")
    print("Waiting for Slack questions...\n")

    SocketModeHandler(
        app,
        os.environ["SLACK_APP_TOKEN"]
    ).start()