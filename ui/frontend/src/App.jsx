import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";

// Backend base URL
const API_BASE = "http://127.0.0.1:8000";

export default function App() {
  const [conversations, setConversations] = useState([]);
  const [activeConv, setActiveConv] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  // Fetch all conversations on load
  useEffect(() => {
    fetchConversations();
  }, []);

  // Fetch messages when active conversation changes
  useEffect(() => {
    if (activeConv?.id) fetchMessages(activeConv.id);
  }, [activeConv]);

  // Auto-scroll to bottom when new messages appear
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Fetch list of conversations
  async function fetchConversations() {
    try {
      const res = await axios.get(`${API_BASE}/conversations`);
      const data = res.data || [];
      setConversations(data);
      // Set default conversation if none selected
      if (data.length && !activeConv) setActiveConv(data[0]);
    } catch (err) {
      console.error("Error fetching conversations:", err);
    }
  }

  // Fetch messages for a conversation
  async function fetchMessages(id) {
    try {
      const res = await axios.get(`${API_BASE}/conversations/${id}/messages`);
      setMessages(res.data || []);
    } catch (err) {
      console.error("Error fetching messages:", err);
    }
  }

  // Create a new conversation
  async function createConversation() {
    try {
      const params = new URLSearchParams();
      params.append("title", "New Chat");
      const res = await axios.post(`${API_BASE}/conversations`, params);
      const newConv = res.data;
      setConversations((prev) => [newConv, ...prev]);
      setActiveConv(newConv);
      setMessages([]);
    } catch (err) {
      console.error("Error creating conversation:", err);
    }
  }

  // Send a prompt to backend
  // Send a prompt to backend
async function sendPrompt(e) {
  e.preventDefault();
  if (!input.trim()) return;
  setLoading(true);

  try {
    const params = new URLSearchParams();
    params.append("prompt", input);
    if (activeConv?.id) params.append("conversation_id", activeConv.id);

    const res = await axios.post(`${API_BASE}/query`, params);
    const { conversation_id, response } = res.data;

    // Add both messages locally without refetch delay
    const userMsg = {
      id: Date.now() + "_user",
      role: "user",
      content: input,
    };
    const botMsg = {
      id: Date.now() + "_assistant",
      role: "assistant",
      content: response || "Not Available",
    };

    setMessages((prev) => [...prev, userMsg, botMsg]);

    // Maintain conversation state
    if (!activeConv || activeConv.id !== conversation_id) {
      const conv = conversations.find((c) => c.id === conversation_id);
      if (conv) setActiveConv(conv);
      else await fetchConversations();
    }

    setInput("");
  } catch (err) {
    alert("Error sending message: " + err.message);
  } finally {
    setLoading(false);
  }
}


  // Handle file upload
  async function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      await axios.post(`${API_BASE}/ingest`, fd);
      alert("✅ File uploaded and processed successfully!");
    } catch (err) {
      alert("❌ Upload failed: " + err.message);
    }
  }

  return (
    <div className="container">
      {/* Sidebar Section */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2>College-GPT</h2>
          <button onClick={createConversation}>＋</button>
        </div>

        {/* Conversations List */}
        <div className="conversation-list">
          {conversations.map((conv) => (
            <div
              key={conv.id || conv.title + Math.random()} // ✅ unique key fallback
              className={`conversation-item ${
                activeConv?.id === conv.id ? "active" : ""
              }`}
              onClick={() => setActiveConv(conv)}
            >
              <div className="conv-title">{conv.title}</div>
              <div className="conv-time">
                {conv.created_at
                  ? new Date(conv.created_at).toLocaleString()
                  : ""}
              </div>
            </div>
          ))}
        </div>

        {/* File Upload */}
        <div className="file-upload">
          <label>Upload file:</label>
          <input type="file" onChange={handleFileUpload} />
        </div>
      </aside>

      {/* Chat Area */}
      <main className="chat-area">
        <div className="messages">
          {messages.length === 0 && (
            <div className="empty-msg">No messages yet. Start chatting!</div>
          )}
          {messages.map((m, index) => (
            <div
              key={m.id || index} // ✅ fix missing key warning
              className={`msg ${m.role === "user" ? "user" : "assistant"}`}
            >
              <div className="msg-content">
                <ReactMarkdown>{m.content}</ReactMarkdown>
              </div>
            </div>
          ))}
          <div ref={endRef}></div>
        </div>

        {/* Input Box */}
        <form className="input-box" onSubmit={sendPrompt}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your question..."
          />
          <button disabled={loading}>{loading ? "..." : "Send"}</button>
        </form>
      </main>
    </div>
  );
}
