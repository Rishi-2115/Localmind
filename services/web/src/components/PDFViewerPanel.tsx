import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, FileText, X, Loader2 } from 'lucide-react';
import { API_BASE, getAuthHeaders } from '../store/authStore';
import { useThemeStore } from '../store/themeStore';

interface PDFViewerPanelProps {
  docId: string;
  initialPage?: number;
  highlightText?: string;
  onClose: () => void;
}

export const PDFViewerPanel: React.FC<PDFViewerPanelProps> = ({
  docId,
  initialPage = 1,
  highlightText,
  onClose,
}) => {
  const { theme } = useThemeStore();
  const isDark = theme === 'dark';

  const [currentPage, setCurrentPage] = useState<number>(initialPage);
  const [zoom, setZoom] = useState<number>(100);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Fetch document with Authorization header and convert to local Blob URL (Zero JWT in URLs)
  useEffect(() => {
    let active = true;
    let currentBlobUrl: string | null = null;

    const fetchPdfBlob = async () => {
      setLoading(true);
      setLoadError(null);
      try {
        const highlightParam = highlightText ? `&highlight=${encodeURIComponent(highlightText.slice(0, 80))}` : '';
        const endpoint = `${API_BASE}/ingest/file/${docId}?page=${currentPage}${highlightParam}`;
        
        const response = await fetch(endpoint, {
          headers: getAuthHeaders(),
        });

        if (!response.ok) {
          throw new Error(`Failed to load document (${response.status})`);
        }

        const blob = await response.blob();
        if (active) {
          currentBlobUrl = URL.createObjectURL(blob);
          setBlobUrl(currentBlobUrl);
        }
      } catch (err: any) {
        if (active) {
          setLoadError(err.message || 'Error loading document');
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    fetchPdfBlob();

    return () => {
      active = false;
      if (currentBlobUrl) {
        URL.revokeObjectURL(currentBlobUrl);
      }
    };
  }, [docId, currentPage, highlightText]);

  return (
    <div className={`flex flex-col h-full border-l animate-slide-left w-full md:w-[500px] lg:w-[620px] flex-shrink-0 z-30 transition-all ${
      isDark 
        ? 'bg-[#030712] border-orange-500/20 shadow-[-10px_0_30px_rgba(0,0,0,0.8)]' 
        : 'bg-white border-zinc-200 shadow-xl'
    }`}>
      {/* Top Toolbar */}
      <div className={`px-4 py-3 border-b flex items-center justify-between ${
        isDark ? 'bg-[#0B132B] border-orange-500/15' : 'bg-zinc-50 border-zinc-200'
      }`}>
        <div className="flex items-center space-x-2.5">
          <div className={`p-1.5 rounded-lg ${
            isDark ? 'bg-orange-500/15 text-[#FF6B00]' : 'bg-black text-white'
          }`}>
            <FileText size={16} />
          </div>
          <span className={`text-xs font-black ${isDark ? 'text-white' : 'text-black'}`}>
            Interactive Document Viewer
          </span>
        </div>

        {/* Page navigation */}
        <div className={`flex items-center space-x-2 px-2 py-1 rounded-xl border ${
          isDark ? 'bg-[#030712] border-slate-700' : 'bg-white border-zinc-200'
        }`}>
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            className="p-1 rounded hover:opacity-75 transition-opacity"
            title="Previous Page"
          >
            <ChevronLeft size={14} />
          </button>
          <span className={`text-xs font-mono font-bold ${isDark ? 'text-orange-400' : 'text-black'}`}>
            Page {currentPage}
          </span>
          <button
            onClick={() => setCurrentPage((p) => p + 1)}
            className="p-1 rounded hover:opacity-75 transition-opacity"
            title="Next Page"
          >
            <ChevronRight size={14} />
          </button>
        </div>

        {/* Zoom & Close */}
        <div className="flex items-center space-x-1">
          <button
            onClick={() => setZoom((z) => Math.max(60, z - 10))}
            className={`p-1.5 rounded-lg border transition-all ${
              isDark ? 'bg-slate-900 border-slate-700 text-slate-300' : 'bg-zinc-100 border-zinc-200 text-black'
            }`}
            title="Zoom Out"
          >
            <ZoomOut size={14} />
          </button>
          <button
            onClick={() => setZoom((z) => Math.min(180, z + 10))}
            className={`p-1.5 rounded-lg border transition-all ${
              isDark ? 'bg-slate-900 border-slate-700 text-slate-300' : 'bg-zinc-100 border-zinc-200 text-black'
            }`}
            title="Zoom In"
          >
            <ZoomIn size={14} />
          </button>
          <button
            onClick={onClose}
            className={`p-1.5 rounded-lg border ml-1 transition-all ${
              isDark ? 'bg-rose-500/10 border-rose-500/20 text-rose-400' : 'bg-zinc-100 border-zinc-200 text-black hover:bg-zinc-200'
            }`}
            title="Close Viewer"
          >
            <X size={15} />
          </button>
        </div>
      </div>

      {/* Anchor Quotation */}
      {highlightText && (
        <div className={`px-4 py-2.5 border-b text-xs flex items-start gap-2.5 ${
          isDark 
            ? 'bg-orange-500/10 border-orange-500/20 text-orange-200' 
            : 'bg-yellow-50 border-yellow-200 text-zinc-900'
        }`}>
          <span className={`font-black text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded mt-0.5 ${
            isDark ? 'bg-[#FF6B00] text-black font-extrabold' : 'bg-yellow-300 text-black'
          }`}>
            Citation Anchor
          </span>
          <p className="line-clamp-2 italic leading-relaxed font-mono">"{highlightText}"</p>
        </div>
      )}

      {/* PDF Frame */}
      <div className={`flex-1 overflow-hidden relative flex items-center justify-center ${isDark ? 'bg-[#0B132B]' : 'bg-zinc-100'}`}>
        {loading && (
          <div className="flex flex-col items-center justify-center space-y-3 z-10">
            <Loader2 size={28} className="animate-spin text-orange-500" />
            <span className={`text-xs font-semibold ${isDark ? 'text-slate-400' : 'text-zinc-600'}`}>
              Streaming document securely...
            </span>
          </div>
        )}

        {loadError && !loading && (
          <div className="p-6 text-center z-10">
            <p className="text-sm font-bold text-rose-500 mb-1">Failed to load document</p>
            <p className="text-xs text-zinc-500 dark:text-slate-400">{loadError}</p>
          </div>
        )}

        {blobUrl && !loading && (
          <iframe
            src={`${blobUrl}#page=${currentPage}&zoom=${zoom}`}
            title="Document PDF Viewer"
            className="w-full h-full border-0 absolute inset-0"
          />
        )}
      </div>
    </div>
  );
};
