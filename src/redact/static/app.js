const fileInput = document.getElementById("file");
const drop = document.getElementById("drop");
const selectedLabel = document.getElementById("selected");
const ocr = document.getElementById("ocr");
const go = document.getElementById("go");
const statusLine = document.getElementById("status");
const result = document.getElementById("result");
const resultTitle = document.getElementById("result-title");
const timing = document.getElementById("timing");
const preview = document.getElementById("preview");
const countNote = document.getElementById("count-note");
const findingsBody = document.getElementById("findings");
const selectAll = document.getElementById("select-all");
const warnings = document.getElementById("warnings");
const apply = document.getElementById("apply");
const download = document.getElementById("download");
const report = document.getElementById("report");
const htmlReport = document.getElementById("html-report");

const state = { file: null, job: null, findings: [] };
const MAX_BYTES = 12 * 1024 * 1024;

function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value < 10 && unit > 0 ? value.toFixed(1) : Math.round(value)} ${units[unit]}`;
}

function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#39;");
}

function setStatus(message, isError = false) {
  statusLine.textContent = message;
  statusLine.classList.toggle("is-error", isError);
}

function setPreview(source, isPdf, label) {
  preview.innerHTML = isPdf
    ? `<iframe src="${escapeHtml(source)}" title="${escapeHtml(label)}"></iframe>`
    : `<img src="${escapeHtml(source)}" alt="${escapeHtml(label)}">`;
}

function setFile(file) {
  if (!file) return;
  if (file.size > MAX_BYTES) {
    setStatus("That file is larger than 12 MB. Choose a smaller file.", true);
    return;
  }
  state.file = file;
  selectedLabel.hidden = false;
  selectedLabel.textContent = `${file.name} · ${formatBytes(file.size)}`;
  result.hidden = true;
  state.job = null;
  setStatus("");
}

fileInput.addEventListener("change", () => setFile(fileInput.files[0]));

["dragenter", "dragover"].forEach((eventName) => {
  drop.addEventListener(eventName, (event) => {
    event.preventDefault();
    drop.classList.add("is-over");
  });
});
["dragleave", "drop"].forEach((eventName) => {
  drop.addEventListener(eventName, (event) => {
    event.preventDefault();
    drop.classList.remove("is-over");
  });
});
drop.addEventListener("drop", (event) => {
  const file = event.dataTransfer.files[0];
  if (file) setFile(file);
});
document.addEventListener("paste", (event) => {
  const items = event.clipboardData ? event.clipboardData.items : [];
  for (const item of items) {
    if (item.type.startsWith("image/")) {
      const file = item.getAsFile();
      if (file) {
        setFile(file);
        setStatus("Image pasted. Click Scan to review findings.");
      }
      break;
    }
  }
});

function renderFindings(findings, selectable) {
  if (!findings.length) {
    findingsBody.innerHTML = '<tr><td colspan="6">No matches. Review the file manually.</td></tr>';
    return;
  }
  findingsBody.innerHTML = findings.map((finding) => `<tr data-finding="${escapeHtml(finding.digest)}">
    <td data-label="Include">${selectable
      ? `<input type="checkbox" class="finding-check" data-digest="${escapeHtml(finding.digest)}" checked aria-label="Redact ${escapeHtml(finding.kind)} on page ${Number(finding.page) + 1}">`
      : '<span aria-hidden="true">✓</span>'}</td>
    <td data-label="Type">${escapeHtml(String(finding.kind).replaceAll("_", " "))}</td>
    <td data-label="Page">${Number(finding.page) + 1}</td>
    <td data-label="Preview">${escapeHtml(finding.preview)}</td>
    <td data-label="Source">${escapeHtml(finding.source)}</td>
    <td data-label="Confidence">${(Number(finding.confidence) * 100).toFixed(0)}%</td>
  </tr>`).join("");
}

function renderScan(data) {
  state.job = data.job;
  state.findings = data.findings || [];
  result.hidden = false;
  resultTitle.textContent = "Review findings";
  timing.textContent = `${data.took_ms} ms`;
  const total = data.counts_total || 0;
  countNote.textContent = total
    ? `${total} item${total === 1 ? "" : "s"} found. Uncheck anything that should stay visible.`
    : "No personal information was detected. Review the file manually.";
  setPreview(data.preview, Boolean(data.is_pdf), "Original document preview");
  renderFindings(state.findings, true);
  selectAll.checked = true;
  selectAll.disabled = total === 0;
  apply.hidden = total === 0;
  download.hidden = true;
  report.hidden = true;
  htmlReport.hidden = true;
  warnings.innerHTML = (data.warnings || []).map((warning) => `<p class="warning">${escapeHtml(warning)}</p>`).join("");
  resultTitle.focus();
}

function renderFinal(data) {
  result.hidden = false;
  resultTitle.textContent = "Redacted copy";
  const total = data.counts_total || 0;
  countNote.textContent = total
    ? `${total} item${total === 1 ? "" : "s"} redacted. Review the copy before sharing it.`
    : "No personal information was redacted. Review the file manually.";
  setPreview(data.preview, Boolean(data.is_pdf), "Redacted document preview");
  renderFindings(data.findings || [], false);
  selectAll.disabled = true;
  apply.hidden = true;
  download.href = data.download;
  report.href = data.report;
  htmlReport.href = data.html_report || data.report;
  download.hidden = false;
  report.hidden = false;
  htmlReport.hidden = false;
  setStatus("Done. Review the redacted copy before sharing it.");
  resultTitle.focus();
}

function selectedDigests() {
  return Array.from(findingsBody.querySelectorAll(".finding-check:checked")).map((item) => item.dataset.digest);
}

async function scan() {
  if (!state.file) {
    setStatus("Choose a PDF or photo first.", true);
    return;
  }
  go.disabled = true;
  go.textContent = "Scanning...";
  setStatus("Scanning locally. Nothing is redacted until you choose.");
  result.hidden = true;
  document.querySelector("main").setAttribute("aria-busy", "true");
  const body = new FormData();
  body.append("file", state.file);
  body.append("ocr", ocr.value);
  try {
    const response = await fetch("/api/scan", { method: "POST", body });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Server returned ${response.status}`);
    }
    renderScan(await response.json());
    setStatus("Review the findings, then redact the selection.");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    go.disabled = false;
    go.textContent = "Scan";
    document.querySelector("main").setAttribute("aria-busy", "false");
  }
}

async function applySelection() {
  const digests = selectedDigests();
  if (!state.job || !digests.length) {
    setStatus("Select at least one finding to redact.", true);
    return;
  }
  apply.disabled = true;
  apply.textContent = "Redacting...";
  setStatus("Redacting the selected findings.");
  try {
    const response = await fetch("/api/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job: state.job, selected: digests, ocr: ocr.value }),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Server returned ${response.status}`);
    }
    renderFinal(await response.json());
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    apply.disabled = false;
    apply.textContent = "Redact selected";
  }
}

go.addEventListener("click", scan);
apply.addEventListener("click", applySelection);
selectAll.addEventListener("change", () => {
  findingsBody.querySelectorAll(".finding-check").forEach((item) => { item.checked = selectAll.checked; });
});
findingsBody.addEventListener("change", (event) => {
  if (!event.target.classList.contains("finding-check")) return;
  const checks = Array.from(findingsBody.querySelectorAll(".finding-check"));
  const checked = checks.filter((item) => item.checked);
  selectAll.checked = checked.length === checks.length;
  selectAll.indeterminate = checked.length > 0 && checked.length < checks.length;
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
    event.preventDefault();
    if (state.job && !apply.hidden) applySelection();
    else scan();
  }
});
