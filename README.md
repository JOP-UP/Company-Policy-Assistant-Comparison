# Company Policy Assistant Comparison

This project compares three approaches for answering company policy questions:

1. Rules-based policy retrieval
2. LLM without a vector index
3. LLM with vector retrieval using Retrieval-Augmented Generation (RAG)

The project also includes a Slack bot that uses the LLM + vector retrieval approach to answer company policy questions and identify the relevant policy.

## Live Website

The deployed comparison website is available here:

https://jop-up.github.io/Company-Policy-Assistant-Comparison/

## Website

The website presents the benchmark results for the three approaches, including:

- Answer
- Relevant policy
- Response time
- Token usage
- Whether the answer is supported by the policy database

The website is built with HTML, CSS, and JavaScript and is deployed using GitHub Pages.

## Project Structure

```text
/
├── index.html
├── styles.css
├── app.js
├── README.md
├── .nojekyll
│
├── src/
│   ├── rules_based.py
│   ├── llm_method.py
│   ├── llm_vector_method.py
│   └── slack_bot.py
│
└── data/
    └── company_policies.csv
```

## Methods

### Rules-based

The rules-based approach uses predefined keyword, synonym, and scoring rules to identify the most relevant policy. No LLM is used.

### LLM without Vector Index

The complete policy database is included in the LLM prompt together with the employee question. The LLM identifies the relevant policy and generates an answer.

### LLM + Vector Retrieval

The policy database is embedded using a text embedding model. Each employee question is also embedded and compared with the stored policy vectors using similarity search.

The three most relevant policies are retrieved and provided to the LLM, which generates the final answer. This follows a Retrieval-Augmented Generation (RAG) approach.

## Slack Bot

The Slack bot uses the LLM + vector retrieval method.

A user can mention the bot in a Slack channel and ask a company policy question, for example:

```text
@Company Policy Assistant Can I work from Spain for three weeks?
```

The bot retrieves the relevant policies, generates an answer, and responds with both the answer and the relevant policy.

The Slack bot runs locally using Slack Socket Mode.

## Requirements

Install the required Python packages:

```bash
pip install openai pandas numpy slack_bolt
```

The following environment variables are required:

```text
OPENAI_API_KEY
SLACK_BOT_TOKEN
SLACK_APP_TOKEN
```

API keys and Slack tokens are not included in this repository.

## Run the Website Locally

From the repository folder, run:

```bash
python -m http.server 8000
```

Then open:

```text
http://localhost:8000
```

## Run the Slack Bot

Set the required environment variables and run:

```bash
python src/slack_bot.py
```

The bot will remain active while the Python process is running.

## GitHub Pages Deployment

The website is deployed from the `main` branch using GitHub Pages.

The website files are stored in the repository root:

- `index.html`
- `styles.css`
- `app.js`
- `.nojekyll`

The Python source files are stored separately in the `src` folder and do not affect the GitHub Pages website.

## Benchmark

The same policy questions were tested across the three approaches to compare policy selection, answer quality, response time, token usage, and unsupported answers.

The benchmark results used by the website are stored in app.js.
