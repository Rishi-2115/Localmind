import React, { useState, useCallback, useEffect } from 'react';
import { 
  UploadCloud, 
  FileText, 
  X, 
  CheckCircle2, 
  Loader2, 
  AlertCircle, 
  Files, 
  ShieldAlert, 
  RefreshCw,
  FolderOpen
} from 'lucide-react';
import { getAuthHeaders, API_BASE } from '../store/authStore';
import { useThemeStore } from '../store/themeStore';
import { ContractRiskModal } from '../components/ContractRiskModal';

interface UploadTask {
  filename: string;
  taskId: string;
  status: string;
  createdAt?: string;
}

const Upload: React.FC = () => {
  const { theme } = useThemeStore();
  const isDark = theme === 'dark';

  const [files, setFiles] = useState<File[]>([]);
  const [tasks, setTasks] = useState<UploadTask[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [activeRiskDoc, setActiveRiskDoc] = useState<{ docId: string; filename: string } | null>(null);

  const fetchExistingDocuments = useCallback(async () => {
    setIsLoadingDocs(true);
    try {
      const res = await fetch(`${API_BASE}/ingest/documents`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const docs = await res.json();
        const mapped: UploadTask[] = docs.map((d: any) => ({
          filename: d.filename,
          taskId: d.id,
          status: d.status,
          createdAt: d.created_at,
        }));
        setTasks(mapped);
      }
    } catch (e) {
      console.error('Failed to fetch existing documents:', e);
    } finally {
      setIsLoadingDocs(false);
    }
  }, []);

  useEffect(() => {
    fetchExistingDocuments();
  }, [fetchExistingDocuments]);

  const handleFiles = (newFiles: FileList | null) => {
    if (!newFiles) return;
    const accepted = Array.from(newFiles).filter((f) =>
      ['.pdf', '.docx', '.txt'].some((ext) => f.name.toLowerCase().endsWith(ext))
    );
    setFiles((prev) => [...prev, ...accepted]);
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    handleFiles(e.dataTransfer.files);
  }, []);

  const handleUpload = async () => {
    if (files.length === 0) return;
    setIsUploading(true);

    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));

    try {
      const res = await fetch(`${API_BASE}/ingest/upload`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        alert(`Upload failed: ${err.detail || res.statusText}`);
        setIsUploading(false);
        return;
      }

      const data = await res.json();
      const newTasks: UploadTask[] = (data.tasks || []).map((t: any) => ({
        filename: t.filename,
        taskId: t.doc_id || t.task_id,
        status: 'queued',
      }));

      setTasks((prev) => [...newTasks, ...prev]);
      setFiles([]);

      // Start polling
      newTasks.forEach((t) => pollStatus(t.taskId));
    } catch (err: any) {
      alert(`Upload error: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const pollStatus = (docId: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/ingest/status/${docId}`, {
          headers: getAuthHeaders(),
        });
        if (res.ok) {
          const data = await res.json();
          setTasks((prev) =>
            prev.map((t) => (t.taskId === docId ? { ...t, status: data.status } : t))
          );
          if (['indexed', 'failed', 'SUCCESS', 'FAILURE'].includes(data.status)) {
            clearInterval(interval);
            fetchExistingDocuments();
          }
        }
      } catch (err) {
        console.error('Polling error:', err);
        clearInterval(interval);
      }
    }, 2000);
  };

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const getStatusBadge = (status: string) => {
    const isSuccess = ['indexed', 'SUCCESS'].includes(status);
    const isFailed = ['failed', 'FAILURE'].includes(status);

    if (isSuccess) {
      return (
        <div className={`flex items-center space-x-1.5 px-3 py-1 rounded-xl text-xs font-black uppercase border ${
          isDark ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400' : 'bg-emerald-50 border-emerald-200 text-emerald-800'
        }`}>
          <CheckCircle2 size={13} />
          <span>Indexed & Ready</span>
        </div>
      );
    }

    if (isFailed) {
      return (
        <div className="flex items-center space-x-1.5 px-3 py-1 rounded-xl text-xs font-black uppercase bg-rose-500/15 border border-rose-500/30 text-rose-500">
          <AlertCircle size={13} />
          <span>Failed</span>
        </div>
      );
    }

    return (
      <div className={`flex items-center space-x-1.5 px-3 py-1 rounded-xl text-xs font-black uppercase border ${
        isDark ? 'bg-orange-500/15 border-orange-500/30 text-[#FF8533]' : 'bg-yellow-50 border-yellow-200 text-black'
      }`}>
        <Loader2 size={13} className="animate-spin" />
        <span>Processing...</span>
      </div>
    );
  };

  return (
    <div className={`flex flex-col h-full overflow-y-auto ${isDark ? 'bg-[#030712]' : 'bg-[#FAFAFA]'}`}>
      {/* Header */}
      <div className={`px-8 py-5 border-b flex items-center justify-between sticky top-0 z-20 backdrop-blur-xl ${
        isDark ? 'bg-[#0B132B]/80 border-orange-500/15' : 'bg-white/90 border-zinc-200 shadow-sm'
      }`}>
        <div className="flex items-center space-x-3.5">
          <div className={`p-2.5 rounded-xl border ${
            isDark ? 'bg-orange-500/10 border-orange-500/30 text-[#FF6B00]' : 'bg-black text-white border-black'
          }`}>
            <Files size={18} />
          </div>
          <div>
            <h1 className={`text-base font-black tracking-tight ${isDark ? 'text-white' : 'text-black'}`}>
              Documents & Ingestion Engine
            </h1>
            <p className={`text-xs font-semibold ${isDark ? 'text-slate-400' : 'text-zinc-500'}`}>
              Upload corporate agreements, NDAs, and briefs to parse, chunk, and index into FAISS
            </p>
          </div>
        </div>

        <button
          onClick={fetchExistingDocuments}
          disabled={isLoadingDocs}
          className={`flex items-center space-x-1.5 px-3 py-1.5 text-xs font-bold rounded-xl border transition-all ${
            isDark 
              ? 'bg-[#030712] border-slate-700 text-slate-300 hover:border-orange-500/40 hover:text-[#FF8533]' 
              : 'bg-zinc-100 border-zinc-200 text-zinc-800 hover:bg-zinc-200'
          }`}
        >
          <RefreshCw size={13} className={isLoadingDocs ? "animate-spin text-orange-500" : ""} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="p-8 max-w-4xl mx-auto w-full space-y-8 animate-fade-in">
        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          className={`relative border-2 border-dashed rounded-3xl p-12 text-center transition-all cursor-pointer ${
            dragActive
              ? isDark 
                ? 'border-[#FF6B00] bg-orange-500/10 scale-[1.01]' 
                : 'border-black bg-zinc-100 scale-[1.01]'
              : isDark
                ? 'border-orange-500/30 hover:border-[#FF6B00] bg-[#0B132B]/50 hover:bg-[#0B132B]/80'
                : 'border-zinc-300 hover:border-black bg-white'
          }`}
        >
          <div className="flex flex-col items-center">
            <div className={`p-4 rounded-3xl mb-4 transition-all ${
              isDark 
                ? 'bg-orange-500/10 text-[#FF6B00] border border-orange-500/30 shadow-[0_0_20px_rgba(255,107,0,0.2)]' 
                : 'bg-black text-white'
            }`}>
              <UploadCloud size={38} className={dragActive ? 'animate-bounce' : ''} />
            </div>
            <p className={`text-lg font-black mb-1.5 ${isDark ? 'text-white' : 'text-black'}`}>
              Drag & Drop Confidential Contracts
            </p>
            <p className={`text-xs mb-6 ${isDark ? 'text-slate-400' : 'text-zinc-500'}`}>
              Supported formats: <strong>PDF, DOCX, TXT</strong> • Maximum size 50 MB
            </p>

            <label className={`inline-flex items-center justify-center px-6 py-2.5 rounded-2xl text-xs font-black cursor-pointer transition-all shadow-md active:scale-95 ${
              isDark 
                ? 'bg-gradient-to-r from-orange-500 to-[#FF4500] text-black shadow-orange-500/25 hover:brightness-110' 
                : 'bg-black text-white hover:bg-zinc-800'
            }`}>
              Browse Local Files
              <input
                id="file-upload-input"
                type="file"
                multiple
                accept=".pdf,.docx,.txt"
                className="hidden"
                onChange={(e) => handleFiles(e.target.files)}
              />
            </label>
          </div>
        </div>

        {/* Selected files awaiting upload */}
        {files.length > 0 && (
          <div className="animate-slide-up">
            <div className="flex items-center justify-between mb-3">
              <h2 className={`text-sm font-black ${isDark ? 'text-white' : 'text-black'}`}>
                Ready for Ingestion ({files.length})
              </h2>
              <button
                id="start-upload-btn"
                onClick={handleUpload}
                disabled={isUploading}
                className={`px-5 py-2 rounded-xl text-xs font-black transition-all shadow-md flex items-center space-x-2 ${
                  isDark 
                    ? 'bg-gradient-to-r from-orange-500 to-[#FF4500] text-black shadow-orange-500/20' 
                    : 'bg-black text-white hover:bg-zinc-800'
                }`}
              >
                {isUploading && <Loader2 size={14} className="animate-spin" />}
                <span>{isUploading ? 'Ingesting...' : `Start Ingestion`}</span>
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
              {files.map((f, i) => (
                <div 
                  key={i} 
                  className={`flex items-center justify-between p-3.5 rounded-2xl border ${
                    isDark ? 'bg-[#0B132B] border-slate-800' : 'bg-white border-zinc-200'
                  }`}
                >
                  <div className="flex items-center space-x-3 overflow-hidden">
                    <FileText size={17} className={isDark ? "text-[#FF6B00]" : "text-black"} />
                    <span className={`text-xs font-semibold truncate ${isDark ? 'text-slate-200' : 'text-zinc-800'}`}>
                      {f.name}
                    </span>
                  </div>
                  <button 
                    onClick={() => removeFile(i)} 
                    className="text-slate-400 hover:text-rose-500 p-1 rounded-lg transition-colors"
                  >
                    <X size={15} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Contract Registry / Ingested Documents List */}
        <div>
          <div className="flex items-center justify-between mb-3.5">
            <div>
              <h2 className={`text-sm font-black ${isDark ? 'text-white' : 'text-black'}`}>
                Contract Library & Compliance Registry
              </h2>
              <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-zinc-500'}`}>
                Indexed files in this tenant partition available for RAG search and automated risk audits.
              </p>
            </div>
          </div>

          {tasks.length === 0 ? (
            <div className={`p-8 text-center rounded-2xl border text-xs font-medium ${
              isDark ? 'bg-[#0B132B]/40 border-slate-800 text-slate-500' : 'bg-white border-zinc-200 text-zinc-400'
            }`}>
              No contracts ingested yet. Upload an agreement above to begin.
            </div>
          ) : (
            <div className={`border rounded-3xl overflow-hidden shadow-sm divide-y ${
              isDark ? 'bg-[#0B132B]/80 border-orange-500/15 divide-slate-800/80' : 'bg-white border-zinc-200 divide-zinc-100'
            }`}>
              {tasks.map((t) => {
                const isSuccess = ['indexed', 'SUCCESS'].includes(t.status);
                return (
                  <div key={t.taskId} className="p-4 md:px-6 flex items-center justify-between hover:bg-slate-500/5 transition-colors">
                    <div className="flex flex-col min-w-0 pr-4">
                      <div className="flex items-center space-x-2">
                        <FolderOpen size={16} className={isDark ? "text-[#FF8533]" : "text-black"} />
                        <span className={`text-xs font-bold truncate ${isDark ? 'text-white' : 'text-black'}`}>
                          {t.filename}
                        </span>
                      </div>
                      <div className="flex items-center space-x-2 mt-1">
                        <span className="text-[11px] font-mono text-slate-500">ID: {t.taskId.slice(0, 12)}…</span>
                        {t.createdAt && (
                          <span className="text-[10px] text-slate-500">
                            • {new Date(t.createdAt).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center space-x-2.5 flex-shrink-0">
                      {getStatusBadge(t.status)}

                      {isSuccess && (
                        <button
                          onClick={() => setActiveRiskDoc({ docId: t.taskId, filename: t.filename })}
                          className={`flex items-center space-x-1.5 px-3 py-1 rounded-xl text-xs font-black border transition-all ${
                            isDark 
                              ? 'bg-orange-500/15 hover:bg-orange-500 text-[#FF8533] hover:text-black border-orange-500/30' 
                              : 'bg-black hover:bg-zinc-800 text-white border-black'
                          }`}
                          title="Open Clause Risk & Deviation Audit"
                        >
                          <ShieldAlert size={13} />
                          <span>Risk Audit</span>
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Contract Risk Audit Modal */}
      {activeRiskDoc && (
        <ContractRiskModal
          docId={activeRiskDoc.docId}
          filename={activeRiskDoc.filename}
          onClose={() => setActiveRiskDoc(null)}
        />
      )}
    </div>
  );
};

export default Upload;
