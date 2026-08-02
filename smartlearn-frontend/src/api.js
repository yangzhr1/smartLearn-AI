const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const CHAT_ID = "day2-demo";

async function request(url, options, fallback) {
  let res;
  try {
    res = await fetch(url, options);
  } catch {
    throw new Error("Cannot reach the server — check your connection or CORS configuration");
  }
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || fallback);
  return data;
}

export function uploadPDF(file) {
  const form = new FormData();
  form.append("file", file);
  return request(
    `${BASE}/upload?chat_id=${encodeURIComponent(CHAT_ID)}`,
    { method: "POST", body: form },
    "Upload failed",
  );
}

export function askQuestion(message) {
  return request(
    `${BASE}/chat`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: CHAT_ID, message }),
    },
    "Chat failed",
  );
}
