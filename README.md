# Company Policy Assistant — GitHub Pages Site

This is a static benchmark site comparing:

1. Rules-based policy retrieval
2. LLM-only policy answering
3. LLM + vector retrieval

## Run locally

Open `index.html` directly in a browser, or from this folder run:

```bash
python -m http.server 8000
```

Then visit `http://localhost:8000`.

## Publish with GitHub Pages

1. Create a new public GitHub repository.
2. Upload `index.html`, `styles.css`, `app.js`, and `.nojekyll` to the repository root.
3. In GitHub, open **Settings → Pages**.
4. Under **Build and deployment**, select **Deploy from a branch**.
5. Select the `main` branch and `/ (root)`, then save.
6. GitHub will display the published Pages URL after deployment.

## Benchmark note

The supplied console output contained four valid common policy questions. One vector run used a shell command as the question and was excluded.

The console block labelled "Rules based results" duplicated the LLM-only output. To keep a three-method comparison, rules-based outputs were reproduced from the deterministic keyword/synonym baseline previously defined for the same 98-policy CSV. The rules-based response time shown on the site is a local Python benchmark and is marked with an asterisk. LLM-only and LLM+Vector response times are the supplied LLM API-call measurements.

## Data editing

All benchmark values are stored near the top of `app.js`. Replace any values there if you rerun the experiments.
