import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";

function App() {
  const [files, setFiles] = useState([]);
  const [status, setStatus] = useState("idle");
  const [history, setHistory] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const scrollRef = useRef(null);

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/history/");
      const data = await response.json();
      setHistory(data || []);
    } catch (err) {
      console.error("Failed to fetch history");
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    alert("Copied to clipboard!");
  };

  const loadSession = async (id) => {
    setActiveSessionId(id);
    setStatus("success");
    try {
      const res = await fetch(`http://localhost:8000/api/session/${id}/`);
      const data = await res.json();
      setMessages(data.messages || []);
    } catch (err) {
      console.error("Error loading session");
    }
  };

  const handleUpload = async () => {
    if (files.length === 0) return;
    setStatus("processing");

    // 1. Create a local variable to track the session ID across the loop
    let currentSessionId = activeSessionId;

    for (const file of [...files]) {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("query", "Analyze this document.");

      // 2. If we already have a session, tell the backend to append to it
      if (currentSessionId) {
        formData.append("session_id", currentSessionId);
      }

      try {
        const res = await fetch("http://localhost:8000/api/upload/", {
          method: "POST",
          body: formData,
        });
        const data = await res.json();

        // 3. Capture the ID from the very first upload if we didn't have one
        if (!currentSessionId) {
          currentSessionId = data.session_id;
          setActiveSessionId(data.session_id);
        }

        // 4. Only poll the status for the LAST file to move to the chat view
        if (file === files[files.length - 1]) {
          pollStatus(data.task_id, currentSessionId);
        }
      } catch (err) {
        console.error("Upload failed for", file.name);
      }
    }
    setFiles([]); // Clear the staging area
  };

  const pollStatus = (taskId, sessionId) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/status/${taskId}/`);
        const data = await res.json();
        if (data.status === "SUCCESS") {
          clearInterval(interval);
          loadSession(sessionId);
          fetchHistory();
        } else if (data.status === "FAILURE") {
          setStatus("error");
          clearInterval(interval);
        }
      } catch (err) {
        clearInterval(interval);
        setStatus("error");
      }
    }, 2000);
  };

  const handleChat = async () => {
    if (!input || !activeSessionId) return;

    const userMsg = { role: "user", text: input };
    setMessages((prev) => [...prev, userMsg]);
    const currentInput = input;
    setInput("");

    try {
      const res = await fetch("http://localhost:8000/api/chat/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: activeSessionId,
          query: currentInput,
        }),
      });
      const data = await res.json();
      setMessages((prev) => [...prev, { role: "ai", text: data.answer }]);
    } catch (err) {
      console.error("Chat error");
    }
  };

  const deleteSession = async (e, id) => {
    e.stopPropagation();
    if (window.confirm("Delete this research?")) {
      await fetch(`http://localhost:8000/api/history/${id}/`, {
        method: "DELETE",
      });
      if (activeSessionId === id) {
        setStatus("idle");
        setActiveSessionId(null);
        setMessages([]);
      }
      fetchHistory();
    }
  };

  const renameSession = async (e, id) => {
    e.stopPropagation();
    const newTitle = prompt("Enter new title:");
    if (newTitle) {
      await fetch(`http://localhost:8000/api/history/${id}/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTitle }),
      });
      fetchHistory();
    }
  };

  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h3>History</h3>
          <button
            onClick={() => {
              setStatus("idle");
              setMessages([]);
              setActiveSessionId(null);
              setFiles([]);
            }}
            className="new-chat-btn"
          >
            + New
          </button>
        </div>
        <div className="history-list">
          {history.map((item) => (
            <div
              key={item.id}
              className={`history-item ${activeSessionId === item.id ? "active" : ""}`}
              onClick={() => loadSession(item.id)}
            >
              <div className="history-text">
                <span className="icon">📄</span>
                <span className="text">{item.title}</span>
              </div>
              <div className="history-actions">
                <button onClick={(e) => renameSession(e, item.id)}>✏️</button>
                <button onClick={(e) => deleteSession(e, item.id)}>❌</button>
              </div>
            </div>
          ))}
        </div>
      </aside>

      <main className="main-content">
        <div className="glass-card">
          <header className="glass-header">
            <h1>Research Assistant</h1>
            <div className="badge">Gemini-2.5-flash-lite</div>
          </header>

          <div className="view-port">
            {status === "idle" && (
              <div className="upload-container">
                <input
                  type="file"
                  multiple
                  onChange={(e) => {
                    const newFiles = Array.from(e.target.files);
                    setFiles((prev) => [...prev, ...newFiles]);
                  }}
                  accept=".pdf"
                  id="pdf-upload"
                  hidden
                />
                <label htmlFor="pdf-upload" className="drop-zone">
                  {files.length > 0 ? "+ Add More Files" : "Select PDFs"}
                </label>

                {files.length > 0 && (
                  <div className="file-preview-container">
                    <h4>Selected Documents ({files.length})</h4>
                    <ul className="selected-files-list">
                      {files.map((f, index) => (
                        <li key={index} className="file-item-pill">
                          <span className="file-icon">📄</span>
                          <span className="file-name">{f.name}</span>
                          <button
                            className="remove-file-btn"
                            onClick={() =>
                              setFiles(files.filter((_, i) => i !== index))
                            }
                          >
                            ✕
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <button
                  className="primary-action-btn"
                  onClick={handleUpload}
                  disabled={files.length === 0}
                >
                  Initialize AI Agent
                </button>
              </div>
            )}

            {status === "processing" && (
              <div className="loader-container">
                <div className="spinner"></div>
                <p>Agent is extracting knowledge...</p>
              </div>
            )}

            {status === "success" && (
              <div className="chat-container">
                <div className="chat-scroll-area" ref={scrollRef}>
                  {messages.map((m, i) => (
                    <div key={i} className={`message-wrapper ${m.role}`}>
                      <div className="message-bubble">
                        <ReactMarkdown>{m.text}</ReactMarkdown>
                        {m.role === "ai" && (
                          <button
                            className="copy-btn"
                            onClick={() => copyToClipboard(m.text)}
                          >
                            Copy Brief
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="chat-input-row">
                  <input
                    type="file"
                    id="attach-more"
                    multiple
                    onChange={(e) => {
                      const nextFiles = Array.from(e.target.files);
                      setFiles(nextFiles);
                    }}
                    hidden
                  />
                  <label
                    htmlFor="attach-more"
                    className="attachment-btn"
                    onClick={() => {
                      if (files.length > 0) handleUpload();
                    }}
                  >
                    {files.length > 0 ? "⬆️" : "🔗"}
                  </label>
                  <input
                    type="text"
                    placeholder="Ask a question about your documents..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleChat()}
                  />
                  <button onClick={handleChat} className="send-btn">
                    Send
                  </button>
                </div>
              </div>
            )}

            {status === "error" && (
              <div className="error-container">
                <p>⚠️ Connection failed. Check Backend/Docker.</p>
                <button
                  className="primary-action-btn"
                  onClick={() => setStatus("idle")}
                >
                  Try Again
                </button>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
