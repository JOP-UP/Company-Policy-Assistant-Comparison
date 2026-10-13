# Company Policy Assistant Comparison

Interactive website comparing three approaches for answering company policy questions:

1. Rules-based policy retrieval
2. LLM without a vector index
3. LLM with vector retrieval using Retrieval-Augmented Generation (RAG)

The same user question is automatically processed by all three methods and the site displays the answer, relevant policy, response time, LLM token usage, and whether the method reports that the answer is supported by the policy database.

## Project Structure

```text
/
├── app.py
├── build_embeddings.py
├── requirements.txt
├── render.yaml
├── .env.example
├── .gitignore
│
├── data/
│   ├── company_policies.csv
│   └── policy_embeddings.json   # created by build_embeddings.py
│
├── templates/
│   └── index.html
│
└── static/
    ├── styles.css
    └── app.js
```

## Methods

### Rules-based

The rules-based approach uses deterministic keyword, synonym, number, category, department, and title scoring. It does not use an LLM.

### LLM without Vector Index

The complete policy database is included in the prompt with the employee question. The LLM identifies the relevant policy and generates an answer.

### LLM + Vector Retrieval

Policies are embedded using `text-embedding-3-small`. The employee question is embedded with the same model and compared with the saved policy vectors using cosine similarity.

The three closest policies are supplied to `gpt-6-luna`, which generates the final answer. This follows the RAG pattern: retrieve, augment, generate.

## Local Setup

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```text
OPENAI_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-6-luna
EMBEDDING_MODEL=text-embedding-3-small
```

Do not commit `.env` to GitHub.

## Build the Vector Index Once

Run:

```bash
python build_embeddings.py
```

This creates:

```text
data/policy_embeddings.json
```

You can commit this JSON file to the repository so the deployed application does not need to recreate all policy embeddings when it starts.

## Run the Website Locally

Run:

```bash
python app.py
```

Then open:

```text
http://localhost:5000
```

Enter one company policy question and click **Compare approaches**.

## Deployment

This project is designed to run as a Python web service because the OpenAI API key must remain server-side.

A `render.yaml` file is included for deployment on Render.

Typical Render configuration:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Environment variable: `OPENAI_API_KEY`

Do not place the API key in `static/app.js`, HTML, GitHub Pages, or any other client-side file.

## Benchmark Timing

For the LLM + Vector method, the displayed response time and token usage cover the final LLM generation call only. Question embedding and vector retrieval time/token usage are intentionally excluded to match the benchmark definition used in the project.

## Slack Bot

The existing Slack bot can continue using the same LLM + Vector/RAG logic. It does not need to be hosted permanently for the assignment if it is run locally during testing.
