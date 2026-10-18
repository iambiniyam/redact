const fileInput = document.getElementById("file");
const drop = document.getElementById("drop");
const selected = document.getElementById("selected");
const ocr = document.getElementById("ocr");
const go = document.getElementById("go");
const statusLine = document.getElementById("status");
const result = document.getElementById("result");
const resultTitle = document.getElementById("result-title");
const timing = document.getElementById("timing");
const preview = document.getElementById("preview");
const countNote = document.getElementById("count-note");
const findingsBody = document.getElementById("findings");
const warnings = document.getElementById("warnings");
const download = document.getElementById("download");
const report = document.getElementById("report");

const state = { file: null };
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
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setStatus(message, isError = false) {
  statusLine.textContent = message;
  statusLine.classList.toggle("is-error", isError);
}

function setFile(file) {
  if (!file) return;
  if (file.size > MAX_BYTES) {
    setStatus("That file is larger than 12 MB. Choose a smaller file.", true);
    return;
  }
  state.file = file;
  selected.hidden = false;
  selected.textContent = `${file.name} · ${formatBytes(file.size)}`;
  result.hidden = true;
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
        setStatus("Image pasted. Click Redact to scan it.");
      }
      break;
    }
  }
});

function renderFindings(findings) {
  if (!findings.length) {
    findingsBody.innerHTML = '<tr><td colspan="5">No matches. Review the file manually.</td></tr>';
    return;
  }
  findingsBody.innerHTML = findings
    .map(
      (finding) => `<tr>
        <td data-label="Type">${escapeHtml(String(finding.kind).replaceAll("_", " "))}</td>
        <td data-label="Page">${Number(finding.page) + 1}</td>
        <td data-label="Preview">${escapeHtml(finding.preview)}</td>
        <td data-label="Source">${escapeHtml(finding.source)}</td>
        <td data-label="Confidence">${(Number(finding.confidence) * 100).toFixed(0)}%</td>
      </tr>`
    )
    .join("");
}

function render(data) {
  result.hidden = false;
  timing.textContent = `${data.took_ms} ms`;
  const total = data.counts_total || 0;
  countNote.textContent = total
    ? `${total} item${total === 1 ? "" : "s"} redacted.`
    : "No personal information was detected. Review the file manually.";

  preview.innerHTML = data.is_pdf
    ? `<iframe src="${data.preview}" title="Redacted PDF preview"></iframe>`
    : `<img src="${data.preview}" alt="Redacted document preview">`;

  renderFindings(data.findings || []);
  warnings.innerHTML = (data.warnings || [])
    .map((warning) => `<p class="warning">${escapeHtml(warning)}</p>`)
    .join("");

  download.href = data.download;
  report.href = data.report;
  resultTitle.focus();
}

async function submit() {
  if (!state.file) {
    setStatus("Choose a PDF or photo first.", true);
    return;
  }
  go.disabled = true;
  go.textContent = "Redacting...";
  setStatus("Scanning locally. This can take a moment for a long PDF.");
  result.hidden = true;
  document.querySelector("main").setAttribute("aria-busy", "true");

  const body = new FormData();
  body.append("file", state.file);
  body.append("ocr", ocr.value);

  try {
    const response = await fetch("/api/redact", { method: "POST", body });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Server returned ${response.status}`);
    }
    const data = await response.json();
    render(data);
    setStatus("Done. Review the redacted copy before sharing it.");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    go.disabled = false;
    go.textContent = "Redact";
    document.querySelector("main").setAttribute("aria-busy", "false");
  }
}

go.addEventListener("click", submit);

document.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
    event.preventDefault();
    submit();
  }
});
