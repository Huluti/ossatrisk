let packages = [];
let filtered = [];
let sortCol = "score"; // active data key
let sortDir = "desc"; // 'asc' | 'desc'

const tbody = document.getElementById("package-table");
const searchEl = document.getElementById("search");
const sortEl = document.getElementById("sort-by");
const countEl = document.getElementById("result-count");

// Columns where sort is not available
const UNSORTABLE = new Set(["actions"]);
// Columns that sort lexicographically
const STRING_COLS = new Set(["name", "latest_release"]);

// ── Ecosystem tabs ──────────────────────────────────────────
document.querySelectorAll(".eco-tab:not(.soon)").forEach((tab) => {
  tab.addEventListener("click", () => {
    document
      .querySelectorAll(".eco-tab")
      .forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById("eco-label").textContent = tab.dataset.eco;
    packages = [];
    tbody.innerHTML =
      '<tr class="status-row"><td colspan="5"><span class="loading-dots">loading</span></td></tr>';
    loadJSON(tab.dataset.url);
  });
});

// ── Load data ───────────────────────────────────────────────
async function loadJSON(url) {
  try {
    const res = await fetch(url);
    packages = await res.json();
    updateStats();
    render();
  } catch (err) {
    tbody.innerHTML =
      '<tr class="status-row"><td colspan="5">⚠ failed to load data — check network or CORS</td></tr>';
    console.error(err);
  }
}

// ── Stats ───────────────────────────────────────────────────
function updateStats() {
  const total = packages.length;
  const installs = packages.reduce((s, p) => s + (p.downloads_total || 0), 0);
  const favers = packages.reduce((s, p) => s + (p.favers || 0), 0);

  document.getElementById("stat-total").textContent = total.toLocaleString();
  document.getElementById("stat-installs").textContent = fmtCompact(installs);
  document.getElementById("stat-favers").textContent = fmtCompact(favers);
}

function fmtCompact(n) {
  if (n >= 1e9) return (n / 1e9).toFixed(1) + "B";
  if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + "K";
  return n.toLocaleString();
}

// ── Filter ──────────────────────────────────────────────────
function applyFilter() {
  const q = searchEl.value.trim().toLowerCase();
  filtered = q
    ? packages.filter((p) => p.name?.toLowerCase().includes(q))
    : [...packages];
}

// ── Sort ────────────────────────────────────────────────────
function applySort() {
  const asc = sortDir === "asc";
  filtered.sort((a, b) => {
    if (STRING_COLS.has(sortCol)) {
      const av = (a[sortCol] || "").toString();
      const bv = (b[sortCol] || "").toString();
      return asc ? av.localeCompare(bv) : bv.localeCompare(av);
    }
    const av = a[sortCol] || 0;
    const bv = b[sortCol] || 0;
    return asc ? av - bv : bv - av;
  });
}

// ── Update header arrow UI ───────────────────────────────────
function updateSortUI() {
  document.querySelectorAll("th[data-col]").forEach((th) => {
    const col = th.dataset.col;
    const arrow = th.querySelector(".sort-arrow");
    if (!arrow) return;
    if (col === sortCol) {
      th.classList.add("sorted");
      arrow.textContent = sortDir === "asc" ? "↑" : "↓";
    } else {
      th.classList.remove("sorted");
      arrow.textContent = "↕";
    }
  });
  // Sync dropdown if a matching option exists
  const match = sortEl.querySelector(`option[value="${sortCol}_${sortDir}"]`);
  if (match) sortEl.value = match.value;
}

// ── Wire th clicks ───────────────────────────────────────────
document.querySelectorAll("th[data-col]").forEach((th) => {
  const col = th.dataset.col;
  if (UNSORTABLE.has(col)) {
    th.style.cursor = "default";
    return;
  }
  th.style.cursor = "pointer";
  th.addEventListener("click", () => {
    if (sortCol === col) {
      sortDir = sortDir === "asc" ? "desc" : "asc";
    } else {
      sortCol = col;
      sortDir = STRING_COLS.has(col) ? "asc" : "desc";
    }
    updateSortUI();
    render();
  });
});

// ── Dropdown ─────────────────────────────────────────────────
sortEl.addEventListener("change", () => {
  const parts = sortEl.value.split("_");
  sortDir = parts.pop(); // last token is dir
  sortCol = parts.join("_"); // rest is the col key (handles downloads_total)
  updateSortUI();
  render();
});

// ── Search ───────────────────────────────────────────────────
searchEl.addEventListener("input", render);

// ── Render ──────────────────────────────────────────────────
function render() {
  applyFilter();
  applySort();

  countEl.textContent = `${filtered.length} / ${packages.length} packages`;

  if (!filtered.length) {
    tbody.innerHTML =
      '<tr class="status-row"><td colspan="5">no packages match your filter</td></tr>';
    return;
  }

  const now = new Date();
  tbody.innerHTML = filtered
    .map((p, i) => {
      const [vendor, pkg] = (p.name || "").split("/");
      const nameHtml = pkg
        ? `<a href="${p.package_url}" class="pkg-vendor">${vendor}/</a><a href="${p.package_url}" class="pkg-name">${pkg}</a>`
        : `<a href="${p.package_url}" class="pkg-name">${p.name}</a>`;

      const suggHtml = p.suggested_package
        ? `<br>↳ <div class="suggestion">
          <a href="${p.suggested_package_url}" target="_blank" title="Suggested replacement" rel="noopener">${p.suggested_package}</a>
        </div>`
        : "";

      const score = p.score || 0;
      let scoreCls = score > 66 ? "score-high" : "score-mid";
      const scoreLabel = score.toLocaleString(undefined, {
        maximumFractionDigits: 1,
      });

      let dateCls = "date-cell";
      let dateLabel = "—";
      if (p.latest_release) {
        const releaseDate = new Date(p.latest_release);
        dateLabel = releaseDate.toISOString().split("T")[0];
        const ageMs = now - releaseDate;
        const ageDays = ageMs / 86400000;
        // Only two categories since no package < 12 months old
        if (ageDays < 730)
          dateCls = "warning-cell"; // updated within ~2 years
        else dateCls = "error-cell"; // older than ~2 years
      }

      const actionsHtml = `<a href="${p.repository}" target="_blank" class="btn-action btn-green">
        <img src="assets/img/heart.svg" class="icon" alt="Contribute">
        Contribute
      </a><a href="${p.repository}/issues" target="_blank" class="btn-action btn-blue">
        <img src="assets/img/list.svg" class="icon" alt="Check issues">
        Check issues
      </a><a href="${p.repository}/fork" target="_blank" class="btn-action ">
        <img src="assets/img/git-fork.svg" class="icon" alt="Fork">
        Fork
      </a>`;

      return `<tr style="animation-delay:${Math.min(i, 30) * 12}ms">
      <td>${nameHtml}${suggHtml}</td>
      <td class="num-cell">${(p.downloads_total || 0).toLocaleString()}</td>
      <td class="num-cell">${(p.favers || 0).toLocaleString()}</td>
      <td class="${dateCls}">${dateLabel}</td>
      <td class="num-cell">${(p.github_open_issues || 0).toLocaleString()}</td>
      <td class="num-cell ${p.cves_count > 0 ? "error-cell" : ""}">${(p.cves_count || 0).toLocaleString()}</td>
      <td><span class="score-badge ${scoreCls}">${scoreLabel}</span></td>
      <td>${actionsHtml}</td>
    </tr>`;
    })
    .join("");

  updateSortUI();
}

// ── Boot ────────────────────────────────────────────────────
loadJSON(
  "https://raw.githubusercontent.com/Huluti/ossatrisk/main/data/php-packages.json",
);
