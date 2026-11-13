import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  Send, 
  Bot, 
  User, 
  FileText, 
  ChevronRight, 
  FileSearch, 
  Sparkles, 
  Eye, 
  ShieldAlert,
  CheckCircle2,
  Trash2
} from 'lucide-react';
import { getAuthHeaders, API_BASE } from '../store/authStore';
import { useThemeStore } from '../store/themeStore';
import { PDFViewerPanel } from '../components/PDFViewerPanel';
import { ContractRiskModal } from '../components/ContractRiskModal';

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

const STORAGE_CHAT_KEY = 'localmind_chat_messages_v1';

const Chat: React.FC = () => {
  const { theme } = useThemeStore();
  const isDark = theme === 'dark';

  const [messages, setMessages] = useState<Message[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_CHAT_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [expandedCitations, setExpandedCitations] = useState<Record<number, boolean>>({});
  const [activeViewerDoc, setActiveViewerDoc] = useState<{ docId: string; page: number; snippet?: string } | null>(null);
  const [activeRiskDoc, setActiveRiskDoc] = useState<{ docId: string; filename: string } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_CHAT_KEY, JSON.stringify(messages));
    } catch (e) {
      console.warn('Failed to persist chat messages:', e);
    }
  }, [messages]);

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
      const response = await fetch(`${API_BASE}/query/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || `HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No readable stream available');

      const decoder = new TextDecoder('utf-8');
      let citations: Citation[] = [];
      let isCached = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunkStr = decoder.decode(value, { stream: true });
        const lines = chunkStr.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.replace('data: ', '').trim();
            if (!jsonStr) continue;

            try {
              const event = JSON.parse(jsonStr);

              if (event.is_cached !== undefined) {
                isCached = event.is_cached;
              }

              if (event.citations) {
                citations = event.citations;
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
        updated[updated.length - 1].content = `Connection error: ${err.message}`;
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
    <div className={`flex flex-col h-full ${isDark ? 'bg-[#030712]' : 'bg-[#FAFAFA]'}`}>
      {/* ─────────────────────────────────────────────────────────────
          HEADER
      ───────────────────────────────────────────────────────────── */}
      <div className={`px-8 py-4 border-b flex items-center justify-between sticky top-0 z-20 backdrop-blur-xl ${
        isDark 
          ? 'bg-[#0B132B]/80 border-orange-500/15 shadow-[0_4px_25px_rgba(0,0,0,0.5)]' 
          : 'bg-white/90 border-zinc-200 shadow-sm'
      }`}>
        <div className="flex items-center space-x-3.5">
          <div className={`p-2.5 rounded-xl border ${
            isDark 
              ? 'bg-orange-500/10 border-orange-500/30 text-[#FF6B00] shadow-[0_0_15px_rgba(255,107,0,0.25)]' 
              : 'bg-black text-white border-black'
          }`}>
            <Sparkles size={18} />
          </div>
          <div>
            <h1 className={`text-base font-black tracking-tight ${isDark ? 'text-white' : 'text-black'}`}>
              Legal Reasoning & RAG Copilot
            </h1>
            <p className={`text-xs font-semibold ${isDark ? 'text-slate-400' : 'text-zinc-500'}`}>
              Air-Gapped • llama3.2:3b • 768-dim Vectors • 100% Deterministic Citations
            </p>
          </div>
        </div>

        {messages.length > 0 && (
          <button
            onClick={() => {
              if (window.confirm('Reset conversation history?')) {
                setMessages([]);
                localStorage.removeItem(STORAGE_CHAT_KEY);
              }
            }}
            className={`flex items-center space-x-1.5 text-xs font-bold px-3 py-1.5 rounded-xl border transition-all ${
              isDark 
                ? 'bg-slate-900 border-slate-700 text-slate-300 hover:text-white hover:border-orange-500/40' 
                : 'bg-zinc-100 border-zinc-200 text-zinc-700 hover:bg-zinc-200'
            }`}
          >
            <Trash2 size={13} />
            <span>Clear Chat</span>
          </button>
        )}
      </div>

      {/* ─────────────────────────────────────────────────────────────
          MESSAGES THREAD
      ───────────────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 md:px-12 py-8 space-y-6">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center animate-fade-in text-center p-6">
            <div className={`w-20 h-20 rounded-3xl flex items-center justify-center mb-6 ring-1 transition-all ${
              isDark 
                ? 'bg-gradient-to-br from-orange-500/20 to-blue-900/30 text-[#FF6B00] ring-orange-500/30 shadow-[0_0_40px_rgba(255,107,0,0.2)]' 
                : 'bg-black text-white ring-zinc-900 shadow-xl'
            }`}>
              <Bot size={40} />
            </div>
            <h2 className={`text-2xl font-black mb-2 tracking-tight ${isDark ? 'text-white' : 'text-black'}`}>
              Local Legal Intelligence Ready
            </h2>
            <p className={`text-sm max-w-lg leading-relaxed ${isDark ? 'text-slate-400' : 'text-zinc-600'}`}>
              Upload contracts in the <strong className={isDark ? "text-[#FF8533]" : "text-black"}>Documents & Ingest</strong> tab. 
              Ask specific clause questions, compare liabilities, or audit covenants with zero cloud data transmission.
            </p>

            {/* Quick Action Badges */}
            <div className="flex flex-wrap gap-2 mt-6 max-w-md justify-center">
              {[
                "What is the limitation of liability cap?",
                "What are the termination notice windows?",
                "Are there unilateral indemnification terms?",
              ].map((suggestion, idx) => (
                <button
                  key={idx}
                  onClick={() => setInput(suggestion)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
                    isDark 
                      ? 'bg-[#0B132B] border-orange-500/20 text-slate-300 hover:border-orange-500 hover:text-[#FF8533]' 
                      : 'bg-white border-zinc-200 text-zinc-800 hover:border-black hover:bg-zinc-50'
                  }`}
                >
                  "{suggestion}"
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => {
          const isUser = msg.role === 'user';
          const isStreamingThis = isStreaming && i === messages.length - 1;
          const hasCitations = msg.citations && msg.citations.length > 0;
          const isExpanded = expandedCitations[i];

          return (
            <div key={i} className={`flex w-full animate-slide-up ${isUser ? 'justify-end' : 'justify-start'}`}>
              <div className={`flex max-w-[88%] md:max-w-[78%] ${isUser ? 'flex-row-reverse' : 'flex-row'} items-start gap-3.5`}>
                {/* Avatar Icon */}
                <div className={`w-9 h-9 rounded-2xl flex items-center justify-center flex-shrink-0 mt-0.5 shadow-md ${
                  isUser 
                    ? isDark ? 'bg-[#FF6B00] text-black font-black' : 'bg-black text-white' 
                    : isDark ? 'bg-[#0B132B] text-[#FF8533] border border-orange-500/30' : 'bg-zinc-100 text-black border border-zinc-300'
                }`}>
                  {isUser ? <User size={17} /> : <Bot size={18} />}
                </div>

                {/* Message Bubble */}
                <div className="flex flex-col min-w-0 flex-1">
                  <div className={`px-6 py-4 rounded-3xl text-[14.5px] leading-relaxed shadow-sm transition-all ${
                    isUser
                      ? isDark
                        ? 'bg-gradient-to-r from-orange-600 to-[#FF4500] text-white rounded-tr-sm shadow-[0_4px_20px_rgba(255,107,0,0.3)] font-medium'
                        : 'bg-black text-white rounded-tr-sm shadow-md'
                      : isDark
                        ? 'bg-[#0B132B]/90 backdrop-blur-xl border border-orange-500/20 text-slate-100 rounded-tl-sm shadow-[0_4px_25px_rgba(3,7,18,0.7)]'
                        : 'bg-white border border-zinc-200 text-zinc-900 rounded-tl-sm shadow-sm'
                  }`}>
                    {isUser ? (
                      <div className="whitespace-pre-wrap font-medium">{msg.content}</div>
                    ) : (
                      <div className={`prose text-sm max-w-none leading-relaxed ${
                        isDark ? 'prose-invert prose-p:text-slate-200' : 'prose-neutral prose-p:text-zinc-900'
                      }`}>
                        {msg.content === '' && isStreamingThis ? (
                          <div className="flex items-center space-x-2 h-6">
                            <div className={`w-2 h-2 rounded-full animate-bounce-delay-1 ${isDark ? 'bg-[#FF6B00]' : 'bg-black'}`} />
                            <div className={`w-2 h-2 rounded-full animate-bounce-delay-2 ${isDark ? 'bg-[#FF6B00]' : 'bg-black'}`} />
                            <div className={`w-2 h-2 rounded-full animate-bounce-delay-3 ${isDark ? 'bg-[#FF6B00]' : 'bg-black'}`} />
                          </div>
                        ) : (
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {msg.content + (isStreamingThis ? ' ▍' : '')}
                          </ReactMarkdown>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Metadata & Citations */}
                  {!isUser && (
                    <div className="mt-3 flex flex-col gap-2 pl-1">
                      {msg.isCached && (
                        <div className="inline-flex items-center text-[10px] font-black uppercase tracking-wider text-emerald-500">
                          <CheckCircle2 size={12} className="mr-1" /> Served from Redis Semantic Cache (&lt; 4ms)
                        </div>
                      )}

                      {hasCitations && (
                        <div className="w-full">
                          <button
                            onClick={() => toggleCitations(i)}
                            className={`flex items-center space-x-1.5 text-xs font-bold py-1 px-2.5 rounded-lg border transition-all ${
                              isDark 
                                ? 'bg-orange-500/10 border-orange-500/25 text-[#FF8533] hover:bg-orange-500/20' 
                                : 'bg-zinc-100 border-zinc-200 text-zinc-800 hover:bg-zinc-200'
                            }`}
                          >
                            <FileSearch size={14} />
                            <span>{msg.citations!.length} Contract Anchors Cited</span>
                            <ChevronRight size={14} className={`transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`} />
                          </button>

                          {isExpanded && (
                            <div className="mt-3 grid grid-cols-1 gap-2.5 animate-fade-in">
                              {msg.citations!.map((citation, idx) => (
                                <div 
                                  key={idx} 
                                  className={`rounded-2xl p-4 border transition-all ${
                                    isDark 
                                      ? 'bg-[#030712]/90 border-orange-500/20 hover:border-orange-500/50 shadow-md' 
                                      : 'bg-white border-zinc-200 hover:border-black shadow-sm'
                                  }`}
                                >
                                  <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center text-xs font-bold">
                                      <FileText size={14} className={isDark ? "text-[#FF6B00] mr-1.5" : "text-black mr-1.5"} />
                                      <span className="truncate max-w-[200px]">{citation.doc_id}</span>
                                      <span className="mx-2 text-slate-500">•</span>
                                      <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${
                                        isDark ? 'bg-orange-500/20 text-[#FF8533]' : 'bg-yellow-400 text-black'
                                      }`}>
                                        Page {citation.page}
                                      </span>
                                    </div>

                                    {/* Action buttons */}
                                    <div className="flex items-center space-x-2">
                                      <button
                                        onClick={() =>
                                          setActiveViewerDoc({
                                            docId: citation.doc_id,
                                            page: typeof citation.page === 'number' ? citation.page : parseInt(String(citation.page)) || 1,
                                            snippet: citation.preview,
                                          })
                                        }
                                        className={`inline-flex items-center space-x-1.5 text-[11px] font-black px-3 py-1 rounded-xl border transition-all ${
                                          isDark 
                                            ? 'bg-blue-600/20 hover:bg-blue-600 text-blue-300 hover:text-white border-blue-500/30' 
                                            : 'bg-black hover:bg-zinc-800 text-white border-black'
                                        }`}
                                      >
                                        <Eye size={12} />
                                        <span>View in PDF</span>
                                      </button>
                                      
                                      <button
                                        onClick={() =>
                                          setActiveRiskDoc({
                                            docId: citation.doc_id,
                                            filename: citation.doc_id,
                                          })
                                        }
                                        className={`inline-flex items-center space-x-1.5 text-[11px] font-black px-3 py-1 rounded-xl border transition-all ${
                                          isDark 
                                            ? 'bg-orange-500/20 hover:bg-orange-500 text-[#FF8533] hover:text-black border-orange-500/40' 
                                            : 'bg-zinc-100 hover:bg-zinc-200 text-black border-zinc-300'
                                        }`}
                                      >
                                        <ShieldAlert size={12} />
                                        <span>Risk Audit</span>
                                      </button>
                                    </div>
                                  </div>

                                  <div className={`text-xs italic leading-relaxed p-2.5 rounded-xl border ${
                                    isDark 
                                      ? 'bg-slate-900/60 border-slate-800 text-slate-300' 
                                      : 'bg-zinc-50 border-zinc-100 text-zinc-700'
                                  }`}>
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

      {/* ─────────────────────────────────────────────────────────────
          INPUT COMMAND BAR
      ───────────────────────────────────────────────────────────── */}
      <div className={`p-4 md:p-6 border-t ${
        isDark 
          ? 'bg-[#030712] border-orange-500/15' 
          : 'bg-white border-zinc-200'
      }`}>
        <div className={`max-w-4xl mx-auto relative flex items-end gap-3 p-2.5 rounded-3xl border shadow-2xl transition-all ${
          isDark 
            ? 'bg-[#0B132B]/95 border-orange-500/30 focus-within:border-[#FF6B00] shadow-[0_0_30px_rgba(255,107,0,0.15)]' 
            : 'bg-white border-zinc-300 focus-within:border-black shadow-lg'
        }`}>
          <textarea
            ref={textareaRef}
            id="chat-query-input"
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about your contracts... (Enter to query, Shift+Enter for newline)"
            disabled={isStreaming}
            rows={1}
            className={`flex-1 max-h-[140px] py-2 px-3 bg-transparent text-sm focus:outline-none disabled:opacity-50 resize-none overflow-y-auto ${
              isDark ? 'text-white placeholder-slate-500' : 'text-black placeholder-zinc-400'
            }`}
          />
          <button
            id="chat-send-btn"
            onClick={handleSend}
            disabled={isStreaming || !input.trim()}
            className={`p-3 rounded-2xl font-bold transition-all shadow-md flex-shrink-0 disabled:opacity-40 ${
              isDark 
                ? 'bg-gradient-to-r from-orange-500 to-[#FF4500] hover:brightness-110 text-black shadow-orange-500/25' 
                : 'bg-black hover:bg-zinc-800 text-white'
            }`}
          >
            <Send size={16} className={isStreaming ? "animate-pulse" : ""} />
          </button>
        </div>
        <div className="text-center mt-2.5">
          <p className={`text-[11px] font-medium ${isDark ? 'text-slate-500' : 'text-zinc-400'}`}>
            LocalMind Legal Copilot • Private On-Premises Neural Inference • DPDPA 2023 Compliant
          </p>
        </div>
      </div>

      {/* Side-by-Side Interactive PDF Viewer */}
      {activeViewerDoc && (
        <div className="fixed inset-y-0 right-0 z-40 flex shadow-2xl">
          <PDFViewerPanel
            docId={activeViewerDoc.docId}
            initialPage={activeViewerDoc.page}
            highlightText={activeViewerDoc.snippet}
            onClose={() => setActiveViewerDoc(null)}
          />
        </div>
      )}

      {/* Contract Risk Audit Modal */}
      {activeRiskDoc && (
        <ContractRiskModal
          docId={activeRiskDoc.docId}
          filename={activeRiskDoc.filename}
          onClose={() => setActiveRiskDoc(null)}
          onSelectClause={(page, snippet) => {
            setActiveRiskDoc(null);
            setActiveViewerDoc({
              docId: activeRiskDoc.docId,
              page,
              snippet,
            });
          }}
        />
      )}
    </div>
  );
};

export default Chat;
