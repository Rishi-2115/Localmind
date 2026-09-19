import React, { useState, useRef, useEffect } from 'react';
import { getAuthHeaders, API_BASE } from '../store/authStore';

interface Citation {
  doc_id: string;
  page: number | string;
  chunk_index: number;
  preview: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  isCached?: boolean;
}

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const query = input.trim();
    if (!query || isStreaming) return;

    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: query }]);
    setIsStreaming(true);

    // Add empty assistant message that we'll stream into
    setMessages((prev) => [...prev, { role: 'assistant', content: '', citations: [] }]);

    try {
      const res = await fetch(`${API_BASE}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },
        body: JSON.stringify({ query }),
      });

      if (!res.ok) {
        const err = await res.json();
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1].content = `❌ Error: ${err.detail || res.statusText}`;
          return updated;
        });
        setIsStreaming(false);
        return;
      }

      // Read SSE stream with JSON parsing
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) return;

      let buffer = '';
      let citations: Citation[] = [];
      let isCached = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data:')) {
            const jsonStr = line.slice(5).trim();
            if (!jsonStr) continue;

            try {
              const event = JSON.parse(jsonStr);

              // Handle error responses
              if (event.error) {
                setMessages((prev) => {
                  const updated = [...prev];
                  updated[updated.length - 1].content =
                    `❌ Service error: ${event.error}. Graceful degradation active.`;
                  return updated;
                });
                continue;
              }

              // Track citations
              if (event.citations && event.citations.length > 0) {
                citations = event.citations;
              }

              // Track if response came from cache
              if (event.cached) {
                isCached = true;
              }

              // Append token to message
              if (event.token) {
                setMessages((prev) => {
                  const updated = [...prev];
                  updated[updated.length - 1] = {
                    ...updated[updated.length - 1],
                    content: updated[updated.length - 1].content + event.token,
                    citations,
                    isCached,
                  };
                  return updated;
                });
              }
            } catch (e) {
              console.error('Failed to parse SSE JSON:', jsonStr, e);
            }
          }
        }
      }
    } catch (err: any) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1].content = `🔌 Connection error: ${err.message}`;
        return updated;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Header */}
      <div className="px-6 py-4 border-b bg-white">
        <h1 className="text-xl font-bold text-slate-800">⚖️ Legal AI Copilot</h1>
        <p className="text-sm text-slate-500">Privacy-first. Local models. Zero external APIs.</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-20 text-slate-400">
            <p className="text-lg font-medium">Welcome to LocalMind</p>
            <p className="text-sm mt-1">
              Upload legal documents, then ask questions about them here. All processing runs locally.
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className="max-w-[85%]">
              <div
                className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white rounded-br-md'
                    : 'bg-white border border-slate-200 text-slate-800 rounded-bl-md shadow-sm'
                }`}
              >
                {msg.content || (isStreaming && i === messages.length - 1 ? '▍' : '')}
              </div>

              {/* Citations */}
              {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                <div className="mt-2 text-xs text-slate-500 space-y-1">
                  <div className="font-medium text-slate-600">Sources:</div>
                  {msg.citations.map((citation, idx) => (
                    <div key={idx} className="pl-2 border-l border-slate-300">
                      <div className="font-mono">
                        📄 {citation.doc_id} (Page {citation.page}, Chunk {citation.chunk_index})
                      </div>
                      <div className="text-slate-400 italic truncate">{citation.preview}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* Cache badge */}
              {msg.role === 'assistant' && msg.isCached && (
                <div className="mt-2 text-xs text-green-600 font-medium">💚 Cached response (instant)</div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t bg-white">
        <div className="flex gap-3">
          <textarea
            id="chat-query-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your legal documents… (Shift+Enter for new line)"
            disabled={isStreaming}
            rows={1}
            className="flex-1 px-4 py-3 border border-slate-300 rounded-xl bg-slate-50 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 disabled:opacity-50 transition resize-none"
            style={{
              minHeight: '44px',
              maxHeight: '120px',
              overflow: 'auto',
            }}
          />
          <button
            id="chat-send-btn"
            onClick={handleSend}
            disabled={isStreaming || !input.trim()}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white text-sm font-semibold rounded-xl transition shadow-sm flex-shrink-0"
          >
            {isStreaming ? '⏳' : '→'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Chat;
