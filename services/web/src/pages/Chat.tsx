import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, Bot, User, FileText, ChevronRight, FileSearch, Sparkles } from 'lucide-react';
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
  const [expandedCitations, setExpandedCitations] = useState<Record<number, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const toggleCitations = (msgIndex: number) => {
    setExpandedCitations(prev => ({ ...prev, [msgIndex]: !prev[msgIndex] }));
  };

  const handleSend = async () => {
    const query = input.trim();
    if (!query || isStreaming) return;

    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    setMessages((prev) => [...prev, { role: 'user', content: query }]);
    setIsStreaming(true);

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

              if (event.error) {
                setMessages((prev) => {
                  const updated = [...prev];
                  updated[updated.length - 1].content = `❌ Service error: ${event.error}. Graceful degradation active.`;
                  return updated;
                });
                continue;
              }

              if (event.citations && event.citations.length > 0) {
                citations = event.citations;
              }
              if (event.cached) {
                isCached = true;
              }

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

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 150)}px`;
  };

  return (
    <div className="flex flex-col h-full bg-transparent">
      {/* Header */}
      <div className="px-8 py-5 border-b border-slate-800/50 bg-[#0F172A]/40 backdrop-blur-md flex items-center justify-between sticky top-0 z-20">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-blue-500/10 rounded-lg text-blue-400">
            <Sparkles size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">Copilot Chat</h1>
            <p className="text-[13px] text-slate-400 font-medium">Privacy-first. Local models. Zero external APIs.</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 md:px-8 py-8 space-y-6">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 animate-fade-in">
            <div className="w-16 h-16 rounded-2xl bg-blue-500/10 flex items-center justify-center mb-6 ring-1 ring-blue-500/20 shadow-[0_0_30px_rgba(59,130,246,0.15)]">
              <Bot size={32} className="text-blue-400" />
            </div>
            <p className="text-2xl font-bold text-white mb-2 tracking-tight">How can I help you today?</p>
            <p className="text-sm text-slate-400 max-w-md text-center leading-relaxed">
              Upload legal documents in the Ingest tab, then ask questions about them here. All processing runs locally on your infrastructure.
            </p>
          </div>
        )}

        {messages.map((msg, i) => {
          const isUser = msg.role === 'user';
          const isStreamingThis = isStreaming && i === messages.length - 1;
          const hasCitations = msg.citations && msg.citations.length > 0;
          const isExpanded = expandedCitations[i];

          return (
            <div key={i} className={`flex w-full animate-slide-up ${isUser ? 'justify-end' : 'justify-start'}`}>
              <div className={`flex max-w-[85%] md:max-w-[75%] ${isUser ? 'flex-row-reverse' : 'flex-row'} items-start gap-3`}>
                {/* Avatar */}
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1 ${isUser ? 'bg-indigo-600' : 'bg-slate-800 ring-1 ring-slate-700'}`}>
                  {isUser ? <User size={16} className="text-white" /> : <Bot size={16} className="text-blue-400" />}
                </div>

                {/* Bubble */}
                <div className="flex flex-col min-w-0">
                  <div
                    className={`px-5 py-4 rounded-2xl text-[15px] leading-relaxed shadow-sm ${
                      isUser
                        ? 'bg-blue-600 text-white rounded-tr-sm'
                        : 'bg-[#1E293B]/80 backdrop-blur-md border border-slate-700/50 text-slate-200 rounded-tl-sm'
                    }`}
                  >
                    {isUser ? (
                      <div className="whitespace-pre-wrap">{msg.content}</div>
                    ) : (
                      <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-800">
                        {msg.content === '' && isStreamingThis ? (
                          <div className="flex items-center space-x-1.5 h-6">
                            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce-delay-1" />
                            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce-delay-2" />
                            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce-delay-3" />
                          </div>
                        ) : (
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {msg.content + (isStreamingThis ? ' ▍' : '')}
                          </ReactMarkdown>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Citations & Meta */}
                  {!isUser && (
                    <div className="mt-2.5 flex flex-col gap-2 pl-1">
                      {msg.isCached && (
                        <div className="inline-flex items-center text-[11px] font-semibold text-emerald-400 uppercase tracking-wider">
                          <Sparkles size={12} className="mr-1" /> Served from Semantic Cache
                        </div>
                      )}

                      {hasCitations && (
                        <div className="w-full">
                          <button
                            onClick={() => toggleCitations(i)}
                            className="flex items-center space-x-1.5 text-xs font-semibold text-slate-400 hover:text-slate-300 transition-colors"
                          >
                            <FileSearch size={14} />
                            <span>{msg.citations!.length} Sources Cited</span>
                            <ChevronRight size={14} className={`transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`} />
                          </button>

                          {isExpanded && (
                            <div className="mt-3 grid grid-cols-1 gap-2 animate-fade-in pr-4">
                              {msg.citations!.map((citation, idx) => (
                                <div key={idx} className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-3 hover:bg-slate-800 hover:border-slate-600 transition-colors cursor-default group">
                                  <div className="flex items-center text-xs font-semibold text-blue-400 mb-1.5">
                                    <FileText size={12} className="mr-1.5" />
                                    {citation.doc_id}
                                    <span className="text-slate-500 mx-2">•</span>
                                    <span className="text-slate-400 font-medium">Page {citation.page}</span>
                                  </div>
                                  <div className="text-[13px] text-slate-300 italic line-clamp-3 leading-relaxed group-hover:line-clamp-none transition-all">
                                    "{citation.preview}"
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} className="h-4" />
      </div>

      {/* Input */}
      <div className="p-4 md:p-6 bg-gradient-to-t from-[#0B1120] via-[#0B1120] to-transparent">
        <div className="max-w-4xl mx-auto relative flex items-end gap-3 p-2 bg-[#1E293B]/80 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-2xl focus-within:border-blue-500/50 focus-within:ring-1 focus-within:ring-blue-500/50 transition-all">
          <textarea
            ref={textareaRef}
            id="chat-query-input"
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your legal documents... (Shift+Enter for new line)"
            disabled={isStreaming}
            rows={1}
            className="flex-1 max-h-[150px] py-2.5 px-3 bg-transparent text-[15px] text-white placeholder-slate-400 focus:outline-none disabled:opacity-50 resize-none overflow-y-auto"
          />
          <button
            id="chat-send-btn"
            onClick={handleSend}
            disabled={isStreaming || !input.trim()}
            className="p-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-xl transition-all shadow-md flex-shrink-0 mb-0.5"
          >
            <Send size={18} className={isStreaming ? "animate-pulse" : ""} />
          </button>
        </div>
        <div className="text-center mt-3">
          <p className="text-[11px] text-slate-500">LocalMind AI can make mistakes. Check important information against the original documents.</p>
        </div>
      </div>
    </div>
  );
};

export default Chat;
