const form = document.getElementById("questionForm");
const questionInput = document.getElementById("question");
const compareButton = document.getElementById("compareButton");
const resultsSection = document.getElementById("resultsSection");
const resultQuestion = document.getElementById("resultQuestion");
const resultsGrid = document.getElementById("resultsGrid");

document.querySelectorAll(".example").forEach((button) => {
  button.addEventListener("click", () => {
    questionInput.value = button.dataset.question;
    questionInput.focus();
  });
});

function loadingCards() {
  return ["Rules-based", "LLM only", "LLM + Vector"]
    .map(
      (name) => `
        <article class="result-card loading-card">
          <div class="card-head">
            <h3>${name}</h3>
          </div>
          <div class="skeleton title"></div>
          <div class="skeleton line"></div>
          <div class="skeleton line"></div>
          <div class="skeleton line short"></div>
        </article>
      `
    )
    .join("");
}

function formatTime(value) {
  if (value === null || value === undefined) {
    return "—";
  }

  if (value < 0.1) {
    return `${(value * 1000).toFixed(2)} ms`;
  }

  return `${value.toFixed(3)} s`;
}

function formatNumber(value) {
  if (value === null || value === undefined) {
    return "—";
  }

  return Number(value).toLocaleString();
}

function supportBadge(value, hasError) {
  if (hasError) {
    return '<span class="badge error">Error</span>';
  }

  if (value === true) {
    return '<span class="badge yes">Supported</span>';
  }

  if (value === false) {
    return '<span class="badge no">Not supported</span>';
  }

  return '<span class="badge no">Unknown</span>';
}

function vectorMatches(result) {
  if (!result.retrieved_policies) {
    return "";
  }

  return `
    <div class="matches">
      <details>
        <summary>Top 3 vector matches</summary>
        <ol>
          ${result.retrieved_policies
            .map(
              (policy) => `
                <li>
                  ${escapeHtml(policy.title)}
                  — ${Number(policy.similarity).toFixed(4)}
                </li>
              `
            )
            .join("")}
        </ol>
      </details>
    </div>
  `;
}

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = String(value ?? "");
  return div.innerHTML;
}

function resultCard(result) {
  if (result.error) {
    return `
      <article class="result-card">
        <div class="card-head">
          <h3>${escapeHtml(result.method)}</h3>
          ${supportBadge(null, true)}
        </div>
        <div class="error-message">
          ${escapeHtml(result.error)}
        </div>
      </article>
    `;
  }

  return `
    <article class="result-card">
      <div class="card-head">
        <h3>${escapeHtml(result.method)}</h3>
        ${supportBadge(
          result.supported_by_policy_database,
          false
        )}
      </div>

      <div class="label">Answer</div>
      <p class="answer">
        ${escapeHtml(result.answer)}
      </p>

      <div class="policy-box">
        <div class="label">Relevant policy</div>
        <div class="policy-name">
          ${escapeHtml(result.relevant_policy)}
        </div>
      </div>

      <div class="metrics">
        <div class="metric">
          <span>Response time</span>
          <strong>
            ${formatTime(result.response_time)}
          </strong>
        </div>

        <div class="metric">
          <span>Total LLM tokens</span>
          <strong>
            ${formatNumber(result.total_tokens)}
          </strong>
        </div>

        <div class="metric">
          <span>Input tokens</span>
          <strong>
            ${formatNumber(result.input_tokens)}
          </strong>
        </div>

        <div class="metric">
          <span>Output tokens</span>
          <strong>
            ${formatNumber(result.output_tokens)}
          </strong>
        </div>
      </div>

      ${vectorMatches(result)}
    </article>
  `;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const question = questionInput.value.trim();

  if (!question) {
    return;
  }

  compareButton.disabled = true;
  compareButton.textContent = "Comparing…";

  resultsSection.classList.remove("hidden");
  resultQuestion.textContent = question;
  resultsGrid.innerHTML = loadingCards();

  resultsSection.scrollIntoView({
    behavior: "smooth",
    block: "start",
  });

  try {
    const response = await fetch("/api/compare", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.error || "The comparison request failed."
      );
    }

    resultsGrid.innerHTML = [
      data.results.rules,
      data.results.llm,
      data.results.vector,
    ]
      .map(resultCard)
      .join("");
  } catch (error) {
    resultsGrid.innerHTML = `
      <div class="error-message">
        ${escapeHtml(error.message)}
      </div>
    `;
  } finally {
    compareButton.disabled = false;
    compareButton.textContent = "Compare approaches";
  }
});


// ============================================================
// PAGE TABS
// ============================================================

document.querySelectorAll(".page-tab").forEach((button) => {
  button.addEventListener("click", () => {
    const tab = button.dataset.tab;

    document.querySelectorAll(".page-tab").forEach((item) => {
      item.classList.remove("active");
    });

    document.querySelectorAll(".tab-panel").forEach((panel) => {
      panel.classList.remove("active");
    });

    button.classList.add("active");

    if (tab === "live") {
      document.getElementById("liveTab").classList.add("active");
    } else {
      document.getElementById("benchmarkTab").classList.add("active");
    }
  });
});


// ============================================================
// ORIGINAL FOUR-QUESTION BENCHMARK
// ============================================================

const benchmarkResults = [
  {
    question: "Can I work from Spain for three weeks?",
    rules: {
      answer: "Employees may work remotely up to three days per week with manager approval.",
      policy: "Remote Work Policy",
      correct: false,
      time: 0.00208,
      tokens: 0
    },
    llm: {
      answer: "Yes. You may work abroad for up to 30 days with approval, so three weeks is within the limit.",
      policy: "Work From Abroad Policy",
      correct: true,
      time: 4.170,
      tokens: 3536
    },
    vector: {
      answer: "Yes, you may work from Spain for three weeks with approval.",
      policy: "Work From Abroad Policy",
      correct: true,
      time: 3.634,
      tokens: 368
    }
  },
  {
    question: "How many vacation days do I get?",
    rules: {
      answer: "Employees receive 15 vacation days per year. Unused days may roll over.",
      policy: "Vacation Policy",
      correct: true,
      time: 0.00212,
      tokens: 0
    },
    llm: {
      answer: "Employees receive 15 vacation days per year. Unused days may roll over.",
      policy: "Vacation Policy",
      correct: true,
      time: 2.892,
      tokens: 3478
    },
    vector: {
      answer: "Employees receive 15 vacation days per year.",
      policy: "Vacation Policy",
      correct: true,
      time: 2.360,
      tokens: 349
    }
  },
  {
    question: "Do expenses over $500 need approval?",
    rules: {
      answer: "All expenses over $500 require prior approval from Finance.",
      policy: "Expense Approval Policy",
      correct: true,
      time: 0.00223,
      tokens: 0
    },
    llm: {
      answer: "Yes. All expenses over $500 require prior approval from Finance.",
      policy: "Expense Approval Policy",
      correct: true,
      time: 3.549,
      tokens: 3511
    },
    vector: {
      answer: "Yes. Expenses over $500 require prior approval from Finance.",
      policy: "Expense Approval Policy",
      correct: true,
      time: 2.329,
      tokens: 338
    }
  },
  {
    question: "Can I bring my dog to the office?",
    rules: {
      answer: "No relevant policy was found in the policy database.",
      policy: "None",
      correct: true,
      time: 0.00202,
      tokens: 0
    },
    llm: {
      answer: "The policy database does not specify whether you may bring your dog to the office.",
      policy: "None",
      correct: true,
      time: 2.532,
      tokens: 3522
    },
    vector: {
      answer: "The policy database does not provide enough information to determine whether you can bring your dog to the office.",
      policy: "None",
      correct: true,
      time: 2.031,
      tokens: 343
    }
  }
];

function benchmarkAverage(values) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

const benchmarkRulesCorrect = benchmarkResults.filter(
  (item) => item.rules.correct
).length;

const benchmarkLlmCorrect = benchmarkResults.filter(
  (item) => item.llm.correct
).length;

const benchmarkVectorCorrect = benchmarkResults.filter(
  (item) => item.vector.correct
).length;

const benchmarkLlmAvgTokens = benchmarkAverage(
  benchmarkResults.map((item) => item.llm.tokens)
);

const benchmarkVectorAvgTokens = benchmarkAverage(
  benchmarkResults.map((item) => item.vector.tokens)
);

const benchmarkTokenReduction =
  (1 - benchmarkVectorAvgTokens / benchmarkLlmAvgTokens) * 100;

document.getElementById("benchmarkSummary").innerHTML = `
  <div class="benchmark-stat">
    <span>Rules-based accuracy</span>
    <strong>${benchmarkRulesCorrect}/4</strong>
  </div>
  <div class="benchmark-stat">
    <span>LLM-only accuracy</span>
    <strong>${benchmarkLlmCorrect}/4</strong>
  </div>
  <div class="benchmark-stat">
    <span>LLM + Vector accuracy</span>
    <strong>${benchmarkVectorCorrect}/4</strong>
  </div>
  <div class="benchmark-stat">
    <span>Vector token reduction</span>
    <strong>${benchmarkTokenReduction.toFixed(1)}%</strong>
  </div>
`;

function compactBenchmarkCell(result, method) {
  return `
    <div class="benchmark-cell">
      <strong>
        ${result.correct ? "✓ Correct" : "✗ Incorrect"}
      </strong>
      <small>${escapeHtml(result.policy)}</small>
      <small>
        ${method === "rules"
          ? `${(result.time * 1000).toFixed(2)} ms`
          : `${result.time.toFixed(3)} s`}
        · ${result.tokens.toLocaleString()} tokens
      </small>
    </div>
  `;
}

document.getElementById("benchmarkTableBody").innerHTML =
  benchmarkResults
    .map(
      (item) => `
        <tr>
          <td>${escapeHtml(item.question)}</td>
          <td>${compactBenchmarkCell(item.rules, "rules")}</td>
          <td>${compactBenchmarkCell(item.llm, "llm")}</td>
          <td>${compactBenchmarkCell(item.vector, "vector")}</td>
        </tr>
      `
    )
    .join("");

function detailedBenchmarkMethod(name, result, method) {
  return `
    <div class="benchmark-method">
      <h4>${name}</h4>
      <div class="label">Answer</div>
      <p>${escapeHtml(result.answer)}</p>

      <div class="label">Relevant policy</div>
      <p><strong>${escapeHtml(result.policy)}</strong></p>

      <div class="benchmark-meta">
        <div>
          <span>Correct</span>
          <strong>${result.correct ? "Yes" : "No"}</strong>
        </div>

        <div>
          <span>Response time</span>
          <strong>
            ${method === "rules"
              ? `${(result.time * 1000).toFixed(2)} ms`
              : `${result.time.toFixed(3)} s`}
          </strong>
        </div>

        <div>
          <span>LLM tokens</span>
          <strong>${result.tokens.toLocaleString()}</strong>
        </div>
      </div>
    </div>
  `;
}

document.getElementById("benchmarkCards").innerHTML =
  benchmarkResults
    .map(
      (item, index) => `
        <article class="benchmark-question">
          <div class="benchmark-question-head">
            <span>Question ${index + 1}</span>
            <h3>${escapeHtml(item.question)}</h3>
          </div>

          <div class="benchmark-methods">
            ${detailedBenchmarkMethod(
              "Rules-based",
              item.rules,
              "rules"
            )}

            ${detailedBenchmarkMethod(
              "LLM only",
              item.llm,
              "llm"
            )}

            ${detailedBenchmarkMethod(
              "LLM + Vector",
              item.vector,
              "vector"
            )}
          </div>
        </article>
      `
    )
    .join("");
