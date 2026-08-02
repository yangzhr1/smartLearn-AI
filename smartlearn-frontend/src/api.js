const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
export const CHAT_ID = "day2-demo";

async function handleResponse(response) {
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(`Request failed with status ${response.status}`);
  }
  if (!response.ok) {
    throw new Error(data.detail || `Request failed with status ${response.status}`);
  }
  return data;
}

export async function uploadPDF(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(
    `${API}/upload?chat_id=${encodeURIComponent(CHAT_ID)}`,
    { method: "POST", body: formData }
  );
  return handleResponse(response);
}

export async function askQuestion(message) {
  const response = await fetch(`${API}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, chat_id: CHAT_ID }),
  });
  return handleResponse(response);
}
