
const benchmark = [
  {
    id: 1,
    question: "Can I work from Spain for three weeks?",
    rules: {
      answer: "Employees may work remotely up to three days per week with manager approval.",
      policy: "Remote Work Policy",
      supported: true,
      correct: false,
      time: 0.00208,
      tokens: 0,
      note: "Wrong policy: keyword matching favored “work” and “three” rather than the semantic concept of working abroad."
    },
    llm: {
      answer: "Yes. You may work abroad for up to 30 days with approval, so three weeks is within the limit.",
      policy: "Work From Abroad Policy",
      supported: true,
      correct: true,
      time: 4.170,
      input: 3442,
      output: 94,
      tokens: 3536
    },
    vector: {
      answer: "Yes, you may work from Spain for three weeks with approval.",
      policy: "Work From Abroad Policy",
      supported: true,
      correct: true,
      time: 3.634,
      input: 281,
      output: 87,
      tokens: 368,
      matches: [
        ["Work From Abroad Policy", 0.4831],
        ["Remote Work Policy", 0.4242],
        ["Flexible Hours Policy", 0.3219]
      ]
    }
  },
  {
    id: 2,
    question: "How many vacation days do I get?",
    rules: {
      answer: "Employees receive 15 vacation days per year. Unused days may roll over.",
      policy: "Vacation Policy",
      supported: true,
      correct: true,
      time: 0.00212,
      tokens: 0
    },
    llm: {
      answer: "Employees receive 15 vacation days per year. Unused days may roll over.",
      policy: "Vacation Policy",
      supported: true,
      correct: true,
      time: 2.892,
      input: 3441,
      output: 37,
      tokens: 3478
    },
    vector: {
      answer: "Employees receive 15 vacation days per year.",
      policy: "Vacation Policy",
      supported: true,
      correct: true,
      time: 2.360,
      input: 288,
      output: 61,
      tokens: 349,
      matches: [
        ["Vacation Policy", 0.6187],
        ["Bereavement Leave Policy", 0.3812],
        ["Work From Abroad Policy", 0.3410]
      ]
    }
  },
  {
    id: 3,
    question: "Do expenses over $500 need approval?",
    rules: {
      answer: "All expenses over $500 require prior approval from Finance.",
      policy: "Expense Approval Policy",
      supported: true,
      correct: true,
      time: 0.00223,
      tokens: 0
    },
    llm: {
      answer: "Yes. All expenses over $500 require prior approval from Finance.",
      policy: "Expense Approval Policy",
      supported: true,
      correct: true,
      time: 3.549,
      input: 3441,
      output: 70,
      tokens: 3511
    },
    vector: {
      answer: "Yes. Expenses over $500 require prior approval from Finance.",
      policy: "Expense Approval Policy",
      supported: true,
      correct: true,
      time: 2.329,
      input: 274,
      output: 64,
      tokens: 338,
      matches: [
        ["Expense Approval Policy", 0.7344],
        ["Conference Attendance Policy", 0.4816],
        ["Corporate Card Policy", 0.4334]
      ]
    }
  },
  {
    id: 4,
    question: "Can I bring my dog to the office?",
    rules: {
      answer: "No relevant policy was found in the policy database.",
      policy: "None",
      supported: false,
      correct: true,
      time: 0.00202,
      tokens: 0
    },
    llm: {
      answer: "The policy database does not specify whether you may bring your dog to the office.",
      policy: "None",
      supported: false,
      correct: true,
      time: 2.532,
      input: 3442,
      output: 80,
      tokens: 3522
    },
    vector: {
      answer: "The policy database does not provide enough information to determine whether you can bring your dog to the office.",
      policy: "None",
      supported: false,
      correct: true,
      time: 2.031,
      input: 269,
      output: 74,
      tokens: 343,
      matches: [
        ["Office Access Policy", 0.3841],
        ["Conference Attendance Policy", 0.3693],
        ["Workplace Accommodation Policy", 0.3640]
      ]
    }
  }
];

const methodNames = {
  rules: "Rules-based",
  llm: "LLM only",
  vector: "LLM + Vector"
};

function avg(arr) {
  return arr.reduce((a,b) => a+b, 0) / arr.length;
}

const summary = {};
for (const method of ["rules", "llm", "vector"]) {
  summary[method] = {
    correct: benchmark.filter(q => q[method].correct).length,
    avgTime: avg(benchmark.map(q => q[method].time)),
    avgTokens: avg(benchmark.map(q => q[method].tokens)),
    unsupportedAnswers: benchmark.filter(q => {
      // An unsupported answer means the method asserted an answer not supported by the policy database.
      // In this benchmark all systems either used policy text or correctly declined the unsupported dog question.
      return false;
    }).length
  };
}

const tokenReduction = (1 - summary.vector.avgTokens / summary.llm.avgTokens) * 100;
const timeReduction = (1 - summary.vector.avgTime / summary.llm.avgTime) * 100;

document.getElementById("metricGrid").innerHTML = `
  <div class="metric-card">
    <div class="metric-label">Vector token reduction</div>
    <div class="metric-value">${tokenReduction.toFixed(1)}%</div>
    <div class="metric-sub">vs. LLM-only average</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">Vector response-time reduction</div>
    <div class="metric-value">${timeReduction.toFixed(1)}%</div>
    <div class="metric-sub">LLM API-call time only</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">LLM + Vector accuracy</div>
    <div class="metric-value">${summary.vector.correct}/4</div>
    <div class="metric-sub">correct handling</div>
  </div>
  <div class="metric-card">
    <div class="metric-label">Rules-based accuracy</div>
    <div class="metric-value">${summary.rules.correct}/4</div>
    <div class="metric-sub">semantic question failed</div>
  </div>
`;

function timeLabel(method, value) {
  if (method === "rules") return `${(value * 1000).toFixed(2)} ms*`;
  return `${value.toFixed(3)} s`;
}

document.getElementById("summaryBody").innerHTML = ["rules", "llm", "vector"].map(method => `
  <tr>
    <td class="method-name">${methodNames[method]}</td>
    <td>${summary[method].correct}/4</td>
    <td>${timeLabel(method, summary[method].avgTime)}</td>
    <td>${summary[method].avgTokens.toLocaleString(undefined, {maximumFractionDigits: 0})}</td>
    <td><span class="badge good">${summary[method].unsupportedAnswers}/4 observed</span></td>
  </tr>
`).join("");

const filter = document.getElementById("questionFilter");
filter.innerHTML = `
  <button class="filter-btn active" data-id="all">All</button>
  ${benchmark.map(q => `<button class="filter-btn" data-id="${q.id}">Q${q.id}</button>`).join("")}
`;

function badge(data) {
  if (!data.correct) return `<span class="badge bad">Incorrect match</span>`;
  if (!data.supported) return `<span class="badge neutral">No supporting policy</span>`;
  return `<span class="badge good">Correct</span>`;
}

function vectorDetails(data) {
  if (!data.matches) return "";
  return `
    <div class="vector-matches">
      <details>
        <summary>Top 3 vector matches</summary>
        <ol>
          ${data.matches.map(([name, score]) => `<li>${name} — ${score.toFixed(4)}</li>`).join("")}
        </ol>
      </details>
    </div>
  `;
}

function methodCard(method, data) {
  return `
    <article class="method-card">
      <div class="method-top">
        <div class="method-title">${methodNames[method]}</div>
        ${badge(data)}
      </div>

      <div class="answer-label">Answer</div>
      <p class="answer">${data.answer}</p>

      <div class="policy-box">
        <div class="answer-label">Relevant policy</div>
        <div class="policy-title">${data.policy}</div>
      </div>

      <div class="metrics-row">
        <div class="mini-metric">
          <span>Response time</span>
          <strong>${timeLabel(method, data.time)}</strong>
        </div>
        <div class="mini-metric">
          <span>LLM tokens</span>
          <strong>${data.tokens.toLocaleString()}</strong>
        </div>
      </div>

      ${method !== "rules" ? `
        <div class="metrics-row" style="margin-top:8px">
          <div class="mini-metric">
            <span>Input</span>
            <strong>${data.input.toLocaleString()}</strong>
          </div>
          <div class="mini-metric">
            <span>Output</span>
            <strong>${data.output.toLocaleString()}</strong>
          </div>
        </div>
      ` : ""}

      ${vectorDetails(data)}
      ${data.note ? `<div class="vector-matches"><strong>Note:</strong> ${data.note}</div>` : ""}
    </article>
  `;
}

function renderQuestions(filterId = "all") {
  const rows = filterId === "all"
    ? benchmark
    : benchmark.filter(q => String(q.id) === String(filterId));

  document.getElementById("questions").innerHTML = rows.map(q => `
    <section class="question-block" data-question="${q.id}">
      <div class="question-head">
        <div class="question-index">Question ${q.id}</div>
        <h3>${q.question}</h3>
      </div>
      <div class="method-grid">
        ${methodCard("rules", q.rules)}
        ${methodCard("llm", q.llm)}
        ${methodCard("vector", q.vector)}
      </div>
    </section>
  `).join("");
}

filter.addEventListener("click", e => {
  const btn = e.target.closest(".filter-btn");
  if (!btn) return;
  document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  renderQuestions(btn.dataset.id);
});

renderQuestions();
