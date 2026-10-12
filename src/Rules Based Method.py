import pandas as pd
import re
import time

# Load policy database
df = pd.read_csv(r"C:\Users\joeel\Downloads\company_policies.csv")

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "to", "of", "for",
    "from", "in", "on", "at", "by", "with", "about", "is", "are",
    "was", "were", "be", "do", "does", "did", "can", "could", "may",
    "might", "must", "should", "would", "will", "i", "me", "my",
    "we", "our", "you", "your", "they", "their", "it", "this",
    "that", "how", "what", "when", "where", "why", "who", "which",
    "have", "has", "had", "company", "employee", "employees", "policy"
}

# Manually defined search rules/synonyms
SYNONYMS = {
    "holiday": {"vacation"},
    "holidays": {"vacation"},
    "pto": {"vacation"},

    "expense": {"expenses", "reimbursement", "spending", "cost"},
    "expenses": {"expense", "reimbursement", "spending", "cost"},

    "password": {"passwords", "credential", "credentials"},

    "vehicle": {"car", "cars"},
    "gift": {"gifts", "present", "presents"},
    "harassment": {"bullying"},
    "sick": {"ill", "illness"},
    "parental": {"maternity", "paternity"},
    "bereavement": {"funeral"},
    "software": {"program", "application", "app"},
}


def tokenize(text):
    """Convert text into useful lowercase keywords."""
    text = str(text).lower()
    words = re.findall(r"[a-z0-9$]+", text)

    return [word for word in words if word not in STOPWORDS]


def expand_tokens(tokens):
    """Add manually defined synonyms."""
    expanded = set(tokens)

    for token in tokens:
        if token in SYNONYMS:
            expanded.update(SYNONYMS[token])

        # Also search synonym rules backwards
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

    # Title matches are most important
    score += 4 * len(question_tokens & title_tokens)

    # Words occurring in policy text
    score += 2 * len(question_tokens & policy_tokens)

    # Category matches
    score += 1 * len(question_tokens & category_tokens)

    # Department matches
    score += 0.5 * len(question_tokens & department_tokens)

    # Matching numbers are especially useful
    # Example: "$500" or "30 days"
    question_numbers = set(re.findall(r"\d+", question))
    policy_numbers = set(re.findall(r"\d+", str(row["policy_text"])))

    score += 4 * len(question_numbers & policy_numbers)

    return score


def search_policy(question):

    start_time = time.perf_counter()

    df["score"] = df.apply(
        lambda row: score_policy(question, row),
        axis=1
    )

    results = df.sort_values("score", ascending=False)

    best_match = results.iloc[0]

    response_time = time.perf_counter() - start_time

    # If nothing matches sufficiently well
    if best_match["score"] < 6:

        return {
            "answer": "No relevant policy was found in the policy database.",
            "relevant_policy": "None",
            "response_time": response_time,
            "tokens": 0,
            "score": best_match["score"]
        }

    return {
        "answer": best_match["policy_text"],
        "relevant_policy": best_match["title"],
        "response_time": response_time,
        "tokens": 0,
        "score": best_match["score"]
    }


# TEST
question = input("Ask a company policy question: ")

result = search_policy(question)

print("\nAnswer:", result["answer"])
print("Relevant policy:", result["relevant_policy"])
print("Response time:", result["response_time"])
print("Token usage:", result["tokens"])
print("Match score:", result["score"])
