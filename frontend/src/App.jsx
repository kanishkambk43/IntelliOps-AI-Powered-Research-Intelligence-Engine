import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000/api/v1";

function App() {
  const [query, setQuery] = useState("");
  const [history, setHistory] = useState([]);
  const [selectedTask, setSelectedTask] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchHistory() {
      try {
        const res = await fetch(`${API_BASE_URL}/research`);
        if (!res.ok) throw new Error("Failed to load research history");
        const data = await res.json();
        setHistory(data);
      } catch {
        setError("Backend offline. Make sure FastAPI is running on port 8000.");
      }
    }
    fetchHistory();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE_URL}/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim() }),
      });

      if (!res.ok) {
        throw new Error(`API error (${res.status})`);
      }

      const newTask = await res.json();
      setSelectedTask(newTask);
      setHistory((prev) => [newTask, ...prev]);
      setQuery("");
    } catch (err) {
      setError(err.message || "Research request failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (e, taskId) => {
    e.stopPropagation();
    try {
      const res = await fetch(`${API_BASE_URL}/research/${taskId}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete report");

      setHistory((prev) => prev.filter((item) => item.id !== taskId));
      if (selectedTask?.id === taskId) {
        setSelectedTask(null);
      }
    } catch (err) {
      setError(err.message || "Could not delete report.");
    }
  };

  return (
    <div className="app-layout">
      {/* Sidebar: History */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2>IntelliOps</h2>
          <span className="subtitle">Research Engine</span>
        </div>

        <button
          className="new-btn"
          onClick={() => {
            setSelectedTask(null);
            setError("");
          }}
        >
          + New Research
        </button>

        <div className="history-label">PAST REPORTS</div>
        <div className="history-list">
          {history.length === 0 ? (
            <p className="empty-text">No reports yet.</p>
          ) : (
            history.map((task) => (
              <div
                key={task.id}
                className={`history-item ${
                  selectedTask?.id === task.id ? "active" : ""
                }`}
                onClick={() => setSelectedTask(task)}
              >
                <span className="history-title">{task.query}</span>
                <button
                  className="delete-btn"
                  title="Delete report"
                  onClick={(e) => handleDelete(e, task.id)}
                >
                  ×
                </button>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <header className="main-header">
          <h1>Engineering Research Assistant</h1>
          <p>Query internal pgvector documents and live DuckDuckGo search</p>
        </header>

        <form className="search-form" onSubmit={handleSubmit}>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask an engineering question or search live web data..."
            disabled={loading}
          />
          <button type="submit" disabled={loading || !query.trim()}>
            {loading ? "Researching..." : "Run Research"}
          </button>
        </form>

        {error && <div className="error-banner">{error}</div>}

        {loading && (
          <div className="loading-card">
            <div className="spinner"></div>
            <p>
              Retrieving vector chunks, checking relevance, searching the web,
              and synthesizing report...
            </p>
          </div>
        )}

        {!loading && selectedTask && (
          <section className="report-card">
            <h2 className="report-query">{selectedTask.query}</h2>

            <div className="meta-bar">
              <span className="badge status">
                {selectedTask.status?.toUpperCase() || "COMPLETED"}
              </span>
              {selectedTask.execution_time_seconds != null && (
                <span className="badge">
                  ⏱ {selectedTask.execution_time_seconds.toFixed(2)}s
                </span>
              )}
              {selectedTask.rewritten_query &&
                selectedTask.rewritten_query !== selectedTask.query && (
                  <span className="badge">
                    🔍 Keywords: {selectedTask.rewritten_query}
                  </span>
                )}
            </div>

            <div className="report-body">
  <ReactMarkdown
    components={{
      a: ({ ...props }) => (
        <a {...props} target="_blank" rel="noopener noreferrer" />
      ),
    }}
  >
    {selectedTask.result}
  </ReactMarkdown>
</div>

            {selectedTask.sources && selectedTask.sources.length > 0 && (
              <div className="sources-section">
                <h3>Sources & Citations</h3>
                <ul>
                  {selectedTask.sources.map((src, idx) => (
                    <li key={idx}>
                      {src.startsWith("http") ? (
                        <a href={src} target="_blank" rel="noreferrer">
                          {src}
                        </a>
                      ) : (
                        <span className="doc-source">📄 {src}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}

export default App;