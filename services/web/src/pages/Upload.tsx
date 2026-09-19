import React, { useState, useCallback } from 'react';
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

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-800 mb-2">Document Ingestion</h1>
      <p className="text-slate-500 text-sm mb-6">Upload legal documents (PDF, DOCX, TXT) to index them for Q&A.</p>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-10 text-center transition cursor-pointer ${
          dragActive
            ? 'border-blue-500 bg-blue-50'
            : 'border-slate-300 bg-slate-50 hover:border-slate-400'
        }`}
      >
        <p className="text-slate-500 mb-3">Drag & drop files here, or click to browse</p>
        <label className="inline-block bg-slate-800 text-white px-5 py-2 rounded-lg text-sm font-medium cursor-pointer hover:bg-slate-700 transition">
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

      {/* Selected files */}
      {files.length > 0 && (
        <div className="mt-6">
          <h2 className="text-sm font-semibold text-slate-700 mb-2">Selected Files ({files.length})</h2>
          <ul className="space-y-2">
            {files.map((f, i) => (
              <li key={i} className="flex items-center justify-between bg-white border rounded-lg px-4 py-2 text-sm">
                <span className="text-slate-700 truncate">{f.name}</span>
                <button onClick={() => removeFile(i)} className="text-red-500 hover:text-red-700 text-xs font-medium">
                  Remove
                </button>
              </li>
            ))}
          </ul>
          <button
            id="start-upload-btn"
            onClick={handleUpload}
            disabled={isUploading}
            className="mt-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-6 py-2.5 rounded-lg text-sm font-semibold transition shadow-sm"
          >
            {isUploading ? 'Uploading…' : `Upload ${files.length} file(s)`}
          </button>
        </div>
      )}

      {/* Processing queue */}
      {tasks.length > 0 && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold text-slate-800 mb-3">Processing Queue</h2>
          <div className="bg-white border rounded-xl overflow-hidden shadow-sm">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="text-left px-4 py-3 font-medium">Filename</th>
                  <th className="text-left px-4 py-3 font-medium">Task ID</th>
                  <th className="text-left px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {tasks.map((t) => (
                  <tr key={t.taskId}>
                    <td className="px-4 py-3 text-slate-700">{t.filename}</td>
                    <td className="px-4 py-3 text-slate-400 font-mono text-xs">{t.taskId.slice(0, 12)}…</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          ['SUCCESS', 'indexed'].includes(t.status)
                            ? 'bg-green-100 text-green-700'
                            : ['FAILURE', 'failed'].includes(t.status)
                            ? 'bg-red-100 text-red-700'
                            : 'bg-yellow-100 text-yellow-700'
                        }`}
                      >
                        {t.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default Upload;
