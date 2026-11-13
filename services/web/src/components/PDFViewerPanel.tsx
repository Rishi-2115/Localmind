import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, FileText, X } from 'lucide-react';
import { API_BASE } from '../store/authStore';

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
  const [currentPage, setCurrentPage] = useState<number>(initialPage);
  const [zoom, setZoom] = useState<number>(100);

  const token = localStorage.getItem('localmind_token') || '';
  // Direct streaming URL from LocalMind API with token parameter for iframe authorization
  const fileUrl = `${API_BASE}/ingest/file/${docId}?token=${encodeURIComponent(token)}#page=${currentPage}`;

  return (
    <div className="flex flex-col h-full bg-[#0B1120] border-l border-slate-800 animate-slide-left w-full md:w-[480px] lg:w-[580px] flex-shrink-0 z-30">
      {/* Top Controls Toolbar */}
      <div className="px-4 py-3 bg-[#0F172A] border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 bg-blue-500/10 text-blue-400 rounded-lg">
            <FileText size={16} />
          </div>
          <span className="text-xs font-semibold text-slate-200">Interactive PDF Viewer</span>
        </div>

        {/* Page navigation */}
        <div className="flex items-center space-x-2 bg-slate-800/80 px-2 py-1 rounded-lg border border-slate-700/60">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-700 transition-colors"
            title="Previous Page"
          >
            <ChevronLeft size={14} />
          </button>
          <span className="text-xs text-slate-300 font-mono font-medium">Page {currentPage}</span>
          <button
            onClick={() => setCurrentPage((p) => p + 1)}
            className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-700 transition-colors"
            title="Next Page"
          >
            <ChevronRight size={14} />
          </button>
        </div>

        {/* Zoom & Close */}
        <div className="flex items-center space-x-1">
          <button
            onClick={() => setZoom((z) => Math.max(60, z - 10))}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
            title="Zoom Out"
          >
            <ZoomOut size={15} />
          </button>
          <button
            onClick={() => setZoom((z) => Math.min(180, z + 10))}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
            title="Zoom In"
          >
            <ZoomIn size={15} />
          </button>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors ml-1"
            title="Close Viewer"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Contextual Citation Anchor banner */}
      {highlightText && (
        <div className="px-4 py-2 bg-blue-500/10 border-b border-blue-500/20 text-xs text-blue-300 flex items-start gap-2">
          <span className="font-bold uppercase tracking-wider text-[10px] bg-blue-500/20 px-1.5 py-0.5 rounded text-blue-200 mt-0.5">
            Anchor
          </span>
          <p className="line-clamp-2 italic leading-relaxed">"{highlightText}"</p>
        </div>
      )}

      {/* PDF Content Frame */}
      <div className="flex-1 bg-slate-900 overflow-hidden relative">
        <iframe
          src={`${fileUrl}&zoom=${zoom}`}
          title="Document PDF Viewer"
          className="w-full h-full border-0"
        />
      </div>
    </div>
  );
};
