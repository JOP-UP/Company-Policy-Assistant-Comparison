import json
import os

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

CSV_FILE = os.path.join(
    BASE_DIR,
    "data",
    "company_policies.csv"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "policy_embeddings.json"
)

EMBEDDING_MODEL = os.environ.get(
    "EMBEDDING_MODEL",
    "text-embedding-3-small"
)

if not os.environ.get("OPENAI_API_KEY"):
    raise RuntimeError(
        "OPENAI_API_KEY is not set."
    )

client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"]
)

df = pd.read_csv(CSV_FILE)

embedding_text = (
    "Title: " + df["title"].fillna("").astype(str)
    + "\nDepartment: " + df["department"].fillna("").astype(str)
    + "\nCategory: " + df["category"].fillna("").astype(str)
    + "\nPolicy: " + df["policy_text"].fillna("").astype(str)
)

print(
    f"Embedding {len(df)} policies "
    f"with {EMBEDDING_MODEL}..."
)

response = client.embeddings.create(
    model=EMBEDDING_MODEL,
    input=embedding_text.tolist()
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

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:
    json.dump(payload, file)

print(
    f"Saved {len(embeddings)} embeddings "
    f"to {OUTPUT_FILE}"
)
