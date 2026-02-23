let packages = [];
let filtered = [];
let sortKey = "score";
let sortDir = "desc";

const tbody = document.getElementById("package-table");
const searchEl = document.getElementById("search");
const sortEl = document.getElementById("sort-by");
const countEl = document.getElementById("result-count");

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

// ── Filter & sort ───────────────────────────────────────────
function applyFilter() {
  const q = searchEl.value.trim().toLowerCase();
  filtered = q
    ? packages.filter((p) => p.name?.toLowerCase().includes(q))
    : [...packages];
}

function applySort() {
  const [key, dir] = sortEl.value.split("_");
  const asc = dir === "asc";

  filtered.sort((a, b) => {
    let av, bv;
    if (key === "name") {
      av = a.name || "";
      bv = b.name || "";
      return asc ? av.localeCompare(bv) : bv.localeCompare(av);
    }
    if (key === "release") {
      av = a.latest_release || "";
      bv = b.latest_release || "";
      return asc ? av.localeCompare(bv) : bv.localeCompare(av);
    }
    if (key === "downloads") {
      av = a.downloads_total || 0;
      bv = b.downloads_total || 0;
    } else {
      av = a[key] || 0;
      bv = b[key] || 0;
    }
    return asc ? av - bv : bv - av;
  });
}

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

      const score = p.score || 0;
      let scoreCls = score > 66 ? "score-high" : "score-mid";
      const scoreLabel = score.toLocaleString(undefined, {
        maximumFractionDigits: 1,
      });

      let dateCls = "date-cell";
      let dateLabel = p.latest_release || "—";
      if (p.latest_release) {
        const ageMs = now - new Date(p.latest_release);
        const ageDays = ageMs / 86400000;
        if (ageDays < 180) dateCls = "date-recent";
        else if (ageDays < 730) dateCls = "date-old";
        else dateCls = "date-ancient";
      }

      return `<tr style="animation-delay:${Math.min(i, 30) * 12}ms">
      <td>${nameHtml}</td>
      <td><a href="${p.repository}" target="_blank"><img src="assets/img/git-solid.svg" class="icon" alt="Repository"></a></td>
      <td class="num-cell">${(p.downloads_total || 0).toLocaleString()}</td>
      <td class="num-cell">${(p.favers || 0).toLocaleString()}</td>
      <td class="${dateCls}">${dateLabel}</td>
      <td><span class="score-badge ${scoreCls}">${scoreLabel}</span></td>
    </tr>`;
    })
    .join("");
}

// ── Events ──────────────────────────────────────────────────
searchEl.addEventListener("input", render);
sortEl.addEventListener("change", render);

// ── Boot ────────────────────────────────────────────────────
loadJSON(
  "https://raw.githubusercontent.com/Huluti/ossatrisk/main/data/php-packages.json",
);
