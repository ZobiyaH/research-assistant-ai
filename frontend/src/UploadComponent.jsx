import React, { useState } from "react";
import ReactMarkdown from "react-markdown";

export default function DocumentAssistant() {
  const [file, setFile] = useState(null);
  const [brief, setBrief] = useState("");
  const [loading, setLoading] = useState(false);

  const handleUpload = async () => {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("http://localhost:8000/api/upload/", {
      method: "POST",
      body: formData,
    });
    const { task_id } = await res.json();
    pollStatus(task_id);
  };

  const pollStatus = (taskId) => {
    setLoading(true);
    const interval = setInterval(async () => {
      const res = await fetch(`http://localhost:8000/api/status/${taskId}/`);
      const data = await res.json();
      if (data.status === "SUCCESS") {
        setBrief(data.result);
        setLoading(false);
        clearInterval(interval);
      }
    }, 3000); // Poll every 3 seconds
  };

  return (
    <div className="glass-container">
      <h1>Research Assistant</h1>
      <input type="file" onChange={(e) => setFile(e.target.files[0])} />
      <button onClick={handleUpload} disabled={loading}>
        {loading ? "AI is thinking..." : "Generate Brief"}
      </button>
      <div className="markdown-view">
        <ReactMarkdown>{brief}</ReactMarkdown>
      </div>
    </div>
  );
}
