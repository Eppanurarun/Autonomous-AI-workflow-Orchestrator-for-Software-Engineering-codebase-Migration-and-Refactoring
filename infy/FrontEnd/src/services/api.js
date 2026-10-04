const rawApiUrl = (import.meta.env.VITE_API_BASE_URL || "").trim().replace(/['"]/g, "");
const API_BASE_URL = (rawApiUrl || "http://localhost:8000").replace(/\/$/, "");

async function parseResponse(response) {
  if (response.status === 204) {
    return { success: true };
  }

  const text = await response.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = text;
  }

  if (!response.ok) {
    const message =
      typeof data === "object" && data?.detail
        ? data.detail
        : typeof data === "object" && data?.message
          ? data.message
          : typeof data === "string" && data
            ? data
            : `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  return data;
}

export async function submitCode({ language, code, filename }) {
  const response = await fetch(`${API_BASE_URL}/api/code/submit`, {
    method: "POST",
    headers: { ...getAuthHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({ language, code, filename: filename || undefined })
  });
  return parseResponse(response);
}

export async function uploadCodeFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/code/upload`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: formData
  });

  return parseResponse(response);
}

export async function getAnalysisHistory() {
  const response = await fetch(`${API_BASE_URL}/api/analysis`, {
    headers: getAuthHeaders()
  });
  return parseResponse(response);
}

export async function getAnalysisById(analysisId) {
  const response = await fetch(`${API_BASE_URL}/api/analysis/${encodeURIComponent(analysisId)}`);
  return parseResponse(response);
}

export async function deleteAnalysis(analysisId) {
  const response = await fetch(`${API_BASE_URL}/api/analysis/${encodeURIComponent(analysisId)}`, {
    method: "DELETE"
  });
  return parseResponse(response);
}

export async function generateRemediation(analysisId) {
  const response = await fetch(
    `${API_BASE_URL}/api/remediation/${encodeURIComponent(analysisId)}`,
    {
      method: "POST",
    }
  );

  return parseResponse(response);
}

export async function getPRSummary(analysisId) {
  const response = await fetch(
    `${API_BASE_URL}/api/summary/${encodeURIComponent(analysisId)}`,
    {
      method: "GET",
    }
  );

  return parseResponse(response);
}

export async function sendChatMessage({ query, analysisId, language, history }) {
  const response = await fetch(`${API_BASE_URL}/api/assistant/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      analysis_id: analysisId || null,
      language: language || "python",
      history: history || [],
    }),
  });

  return parseResponse(response);
}

export function getAuthToken() {
  return localStorage.getItem("codeguard_token") || "";
}

export function getAuthUser() {
  try {
    const data = localStorage.getItem("codeguard_user");
    return data ? JSON.parse(data) : null;
  } catch {
    return null;
  }
}

export function saveAuth(authData) {
  localStorage.setItem("codeguard_token", authData.token);
  localStorage.setItem("codeguard_user", JSON.stringify(authData));
}

export function clearAuth() {
  localStorage.removeItem("codeguard_token");
  localStorage.removeItem("codeguard_user");
}

function getAuthHeaders() {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function loginUser({ email, password }) {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });
  const data = await parseResponse(response);
  saveAuth(data);
  return data;
}

export async function signupUser({ email, password, full_name, role }) {
  const response = await fetch(`${API_BASE_URL}/api/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name, role: role || "developer" })
  });
  const data = await parseResponse(response);
  saveAuth(data);
  return data;
}

export async function getCurrentUser() {
  const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
    headers: getAuthHeaders()
  });
  return parseResponse(response);
}

export async function getAdminUsers() {
  const response = await fetch(`${API_BASE_URL}/api/admin/users`, {
    headers: getAuthHeaders()
  });
  return parseResponse(response);
}

export async function toggleUserStatus(userId) {
  const response = await fetch(`${API_BASE_URL}/api/admin/users/${encodeURIComponent(userId)}/status`, {
    method: "POST",
    headers: getAuthHeaders()
  });
  return parseResponse(response);
}

export async function getAdminStats() {
  const response = await fetch(`${API_BASE_URL}/api/admin/stats`, {
    headers: getAuthHeaders()
  });
  return parseResponse(response);
}

export function downloadPDFReportUrl(analysisId) {
  return `${API_BASE_URL}/api/report/pdf/${encodeURIComponent(analysisId)}`;
}

// ============================================================
// MIGRATION API — Java → Julia Migration Module
// ============================================================

export async function uploadMigrationFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/migration/upload`, {
    method: "POST",
    body: formData,
  });

  return parseResponse(response);
}

export async function runMigrationAnalysis(javaCode, filename) {
  const response = await fetch(`${API_BASE_URL}/api/migration/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ java_code: javaCode, filename }),
  });
  return parseResponse(response);
}

export async function runMigrationConvert(javaCode, analysis) {
  const response = await fetch(`${API_BASE_URL}/api/migration/convert`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ java_code: javaCode, analysis }),
  });
  return parseResponse(response);
}

export async function runMigrationRiskAnalysis(javaCode, juliaCode, analysis) {
  const response = await fetch(`${API_BASE_URL}/api/migration/risk-analysis`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ java_code: javaCode, julia_code: juliaCode, analysis }),
  });
  return parseResponse(response);
}

export async function runMigrationErrorDetection(juliaCode, javaCode) {
  const response = await fetch(`${API_BASE_URL}/api/migration/detect-errors`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ julia_code: juliaCode, java_code: javaCode }),
  });
  return parseResponse(response);
}

export async function runMigrationErrorCorrection(javaCode, juliaCode, errors, analysis, risks, iteration) {
  const response = await fetch(`${API_BASE_URL}/api/migration/correct-errors`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      java_code: javaCode,
      julia_code: juliaCode,
      errors,
      analysis,
      risks,
      iteration,
    }),
  });
  return parseResponse(response);
}

export async function runMigrationValidation(javaCode, juliaCode, analysis, errorsRemaining) {
  const response = await fetch(`${API_BASE_URL}/api/migration/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      java_code: javaCode,
      julia_code: juliaCode,
      analysis,
      errors_remaining: errorsRemaining,
    }),
  });
  return parseResponse(response);
}

export async function runCompleteMigration(javaCode, filename) {
  const response = await fetch(`${API_BASE_URL}/api/migration/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ java_code: javaCode, filename }),
  });
  return parseResponse(response);
}

export { API_BASE_URL };