const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const CHAT_ID = "day2-demo";

export async function uploadPDF(file) {
  const fd = new FormData();
  fd.append("file", file);

  const res = await fetch(
    `${API}/upload?chat_id=${encodeURIComponent(CHAT_ID)}`,
    { method: "POST", body: fd },
  );

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || "Upload failed");
  }

  return data;
}

export async function askQuestion(message) {
  const res = await fetch(`${API}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, chat_id: CHAT_ID }),
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || "Chat failed");
  }

  return data;
}
