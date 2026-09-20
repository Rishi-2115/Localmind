import React, { useState, useCallback } from 'react';
import { UploadCloud, FileText, X, CheckCircle2, Loader2, AlertCircle, Files } from 'lucide-react';
import { getAuthHeaders, API_BASE } from '../store/authStore';

interface UploadTask {
  filename: string;
  taskId: string;
  status: string;
}

const Upload: React.FC = () => {
  const [files, setFiles] = useState<File[]>([]);
  const [tasks, setTasks] = useState<UploadTask[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);

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
      const newTasks: UploadTask[] = data.tasks.map((t: any) => ({
        filename: t.filename,
        taskId: t.doc_id || t.task_id,
        status: 'processing',
      }));

      setTasks((prev) => [...newTasks, ...prev]);
      setFiles([]);

      // Poll statuses
      for (const task of newTasks) {
        pollStatus(task.taskId);
      }
    } catch (err: any) {
      alert(`Upload error: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const pollStatus = async (taskId: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/ingest/status/${taskId}`, {
          headers: getAuthHeaders(),
        });
        const data = await res.json();

        setTasks((prev) =>
          prev.map((t) => (t.taskId === taskId ? { ...t, status: data.status } : t))
        );

        if (['indexed', 'failed', 'SUCCESS', 'FAILURE'].includes(data.status)) {
          clearInterval(interval);
        }
      } catch {
        clearInterval(interval);
      }
    }, 2000);
  };

  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const getStatusIcon = (status: string) => {
    if (['indexed', 'SUCCESS'].includes(status)) return <CheckCircle2 size={16} className="text-emerald-400" />;
    if (['failed', 'FAILURE'].includes(status)) return <AlertCircle size={16} className="text-rose-400" />;
    return <Loader2 size={16} className="text-blue-400 animate-spin" />;
  };

  const getStatusText = (status: string) => {
    if (['indexed', 'SUCCESS'].includes(status)) return 'Indexed & Ready';
    if (['failed', 'FAILURE'].includes(status)) return 'Ingestion Failed';
    return 'Processing...';
  };

  return (
    <div className="flex flex-col h-full bg-transparent">
      {/* Header */}
      <div className="px-8 py-5 border-b border-slate-800/50 bg-[#0F172A]/40 backdrop-blur-md sticky top-0 z-20">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-400">
            <Files size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">Documents & Ingestion</h1>
            <p className="text-[13px] text-slate-400 font-medium">Upload legal documents to index them for Copilot Q&A.</p>
          </div>
        </div>
      </div>

      <div className="p-8 max-w-4xl mx-auto w-full animate-fade-in overflow-y-auto">
        
        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          className={`relative overflow-hidden border-2 border-dashed rounded-3xl p-12 text-center transition-all duration-300 ease-out cursor-pointer ${
            dragActive
              ? 'border-blue-500 bg-blue-500/10 scale-[1.02]'
              : 'border-slate-700 hover:border-slate-600 bg-[#1E293B]/40 hover:bg-[#1E293B]/60'
          }`}
        >
          {dragActive && <div className="absolute inset-0 bg-blue-500/5 backdrop-blur-sm z-0" />}
          
          <div className="relative z-10 flex flex-col items-center">
            <div className={`p-4 rounded-full mb-4 transition-colors duration-300 ${dragActive ? 'bg-blue-500/20 text-blue-400' : 'bg-slate-800/80 text-slate-400'}`}>
              <UploadCloud size={40} className={dragActive ? 'animate-bounce' : ''} />
            </div>
            <p className="text-lg font-semibold text-white mb-2">Drag & drop files here</p>
            <p className="text-sm text-slate-400 mb-6">Supported formats: PDF, DOCX, TXT</p>
            
            <label className="inline-flex items-center justify-center bg-blue-600 hover:bg-blue-500 text-white px-6 py-2.5 rounded-xl text-sm font-semibold cursor-pointer transition-all shadow-lg shadow-blue-500/20 active:scale-95">
              Browse Files
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

        {/* Selected files */}
        {files.length > 0 && (
          <div className="mt-8 animate-slide-up">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-[15px] font-semibold text-slate-200">Ready to Upload ({files.length})</h2>
              <button
                id="start-upload-btn"
                onClick={handleUpload}
                disabled={isUploading}
                className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 disabled:text-slate-500 text-white px-5 py-2 rounded-xl text-sm font-semibold transition-all shadow-lg shadow-indigo-500/20 flex items-center space-x-2"
              >
                {isUploading && <Loader2 size={16} className="animate-spin" />}
                <span>{isUploading ? 'Uploading...' : `Upload ${files.length} file(s)`}</span>
              </button>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {files.map((f, i) => (
                <div key={i} className="flex items-center justify-between bg-[#1E293B]/60 border border-slate-700/50 rounded-xl px-4 py-3 group hover:border-slate-600 transition-colors">
                  <div className="flex items-center space-x-3 overflow-hidden">
                    <FileText size={18} className="text-slate-400 flex-shrink-0" />
                    <span className="text-sm text-slate-300 font-medium truncate">{f.name}</span>
                  </div>
                  <button 
                    onClick={() => removeFile(i)} 
                    className="text-slate-500 hover:text-rose-400 p-1.5 rounded-lg hover:bg-rose-400/10 transition-colors flex-shrink-0 opacity-0 group-hover:opacity-100"
                  >
                    <X size={16} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Processing queue */}
        {tasks.length > 0 && (
          <div className="mt-12 animate-slide-up">
            <h2 className="text-[15px] font-semibold text-slate-200 mb-4">Ingestion Queue</h2>
            <div className="bg-[#1E293B]/40 border border-slate-700/50 rounded-2xl overflow-hidden backdrop-blur-sm">
              <div className="divide-y divide-slate-800/60">
                {tasks.map((t) => {
                  const isSuccess = ['indexed', 'SUCCESS'].includes(t.status);
                  const isFailed = ['failed', 'FAILURE'].includes(t.status);
                  
                  return (
                    <div key={t.taskId} className="px-6 py-4 flex items-center justify-between hover:bg-slate-800/30 transition-colors">
                      <div className="flex flex-col">
                        <span className="text-sm font-medium text-slate-200">{t.filename}</span>
                        <span className="text-xs text-slate-500 font-mono mt-0.5">ID: {t.taskId.slice(0, 12)}…</span>
                      </div>
                      
                      <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg border ${
                        isSuccess ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' :
                        isFailed ? 'bg-rose-500/10 border-rose-500/20 text-rose-400' :
                        'bg-blue-500/10 border-blue-500/20 text-blue-400'
                      }`}>
                        {getStatusIcon(t.status)}
                        <span className="text-xs font-semibold tracking-wide uppercase">
                          {getStatusText(t.status)}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Upload;
