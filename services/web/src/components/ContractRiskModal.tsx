import React, { useState, useEffect } from 'react';
import { ShieldAlert, AlertTriangle, CheckCircle, ChevronRight, FileText, ArrowRight, X } from 'lucide-react';
import { getAuthHeaders, API_BASE } from '../store/authStore';

export interface ContractRiskItem {
  id: number;
  clause_type: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  excerpt: string;
  page_number: number;
  reasoning: string;
  recommendation: string;
}

export interface DocumentRiskReport {
  document_id: string;
  risk_tier: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  total_risks_flagged: number;
  risks: ContractRiskItem[];
}

interface ContractRiskModalProps {
  docId: string;
  filename: string;
  onClose: () => void;
  onSelectClause?: (page: number, excerpt: string) => void;
}

export const ContractRiskModal: React.FC<ContractRiskModalProps> = ({
  docId,
  filename,
  onClose,
  onSelectClause,
}) => {
  const [report, setReport] = useState<DocumentRiskReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedRisk, setSelectedRisk] = useState<ContractRiskItem | null>(null);

  useEffect(() => {
    const fetchRisks = async () => {
      try {
        const res = await fetch(`${API_BASE}/ingest/risks/${docId}`, {
          headers: getAuthHeaders(),
        });
        if (res.ok) {
          const data = await res.json();
          setReport(data);
          if (data.risks?.length > 0) {
            setSelectedRisk(data.risks[0]);
          }
        }
      } catch (e) {
        console.error('Failed to load risk report:', e);
      } finally {
        setLoading(false);
      }
    };
    fetchRisks();
  }, [docId]);

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'CRITICAL':
        return 'text-rose-400 bg-rose-500/10 border-rose-500/30';
      case 'HIGH':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
      case 'MEDIUM':
        return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
      default:
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fade-in">
      <div className="bg-[#0F172A] border border-slate-700/60 rounded-3xl max-w-4xl w-full max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-rose-500/10 rounded-xl text-rose-400">
              <ShieldAlert size={22} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                Clause Risk & Deviation Audit
                {report && (
                  <span className={`text-xs px-2.5 py-0.5 rounded-full border font-semibold ${getTierColor(report.risk_tier)}`}>
                    {report.risk_tier} RISK
                  </span>
                )}
              </h2>
              <p className="text-xs text-slate-400 font-mono mt-0.5">{filename}</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-2 rounded-xl hover:bg-slate-800 transition-colors">
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="p-16 flex flex-col items-center justify-center text-slate-400">
            <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-4" />
            <p className="text-sm">Evaluating contract clauses against institutional playbook...</p>
          </div>
        ) : !report || report.risks.length === 0 ? (
          <div className="p-16 text-center text-slate-400">
            <CheckCircle size={48} className="mx-auto text-emerald-400 mb-3" />
            <h3 className="text-base font-semibold text-white">No Critical Deviations Flagged</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
              All scanned clauses adhere to standard bilateral commercial thresholds with no asymmetric liability caps.
            </p>
          </div>
        ) : (
          <div className="flex-1 grid grid-cols-1 md:grid-cols-12 min-h-0 overflow-hidden">
            {/* Left Column: Risk Cards */}
            <div className="md:col-span-5 border-r border-slate-800 overflow-y-auto p-4 space-y-2.5">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider px-2 mb-1">
                Detected Clause Exposures ({report.risks.length})
              </div>
              {report.risks.map((r) => {
                const isSelected = selectedRisk?.id === r.id;
                return (
                  <div
                    key={r.id}
                    onClick={() => setSelectedRisk(r)}
                    className={`p-3.5 rounded-2xl border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-blue-600/10 border-blue-500/50 shadow-md ring-1 ring-blue-500/30'
                        : 'bg-slate-800/40 border-slate-700/40 hover:bg-slate-800 hover:border-slate-600'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-bold text-white capitalize">{r.clause_type.replace('_', ' ')}</span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getTierColor(r.risk_level)}`}>
                        {r.risk_level}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">{r.reasoning}</p>
                    <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500">
                      <span>Page {r.page_number}</span>
                      <ChevronRight size={14} className={isSelected ? 'text-blue-400' : 'text-slate-600'} />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Right Column: Deep Analysis & Action Plan */}
            <div className="md:col-span-7 overflow-y-auto p-6 bg-slate-900/30">
              {selectedRisk ? (
                <div className="space-y-5 animate-fade-in">
                  <div>
                    <div className="flex items-center justify-between">
                      <h3 className="text-base font-bold text-white capitalize">{selectedRisk.clause_type.replace('_', ' ')} Clause</h3>
                      <span className={`text-xs px-2.5 py-1 rounded-lg border font-bold ${getTierColor(selectedRisk.risk_level)}`}>
                        {selectedRisk.risk_level} SEVERITY
                      </span>
                    </div>
                    <div className="mt-1 flex items-center text-xs text-slate-400">
                      <FileText size={13} className="mr-1 text-blue-400" />
                      Document Anchor: Page {selectedRisk.page_number}
                    </div>
                  </div>

                  {/* Excerpt */}
                  <div className="bg-slate-950/60 border border-slate-800 rounded-2xl p-4">
                    <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Original Contract Excerpt</div>
                    <p className="text-xs text-slate-300 font-mono leading-relaxed italic">"{selectedRisk.excerpt}"</p>
                  </div>

                  {/* Legal Exposure Reasoning */}
                  <div className="bg-rose-500/5 border border-rose-500/20 rounded-2xl p-4">
                    <div className="flex items-center text-xs font-bold text-rose-300 mb-1.5">
                      <AlertTriangle size={15} className="mr-1.5 text-rose-400" /> Legal & Commercial Exposure
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">{selectedRisk.reasoning}</p>
                  </div>

                  {/* Recommendation Playbook */}
                  <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-2xl p-4">
                    <div className="flex items-center text-xs font-bold text-emerald-300 mb-1.5">
                      <CheckCircle size={15} className="mr-1.5 text-emerald-400" /> Recommended Counter-Proposal (Playbook)
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">{selectedRisk.recommendation}</p>
                  </div>

                  {/* Action */}
                  {onSelectClause && (
                    <button
                      onClick={() => onSelectClause(selectedRisk.page_number, selectedRisk.excerpt)}
                      className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold transition-all shadow-lg shadow-blue-500/20 flex items-center justify-center space-x-2"
                    >
                      <span>Jump to Page {selectedRisk.page_number} in Viewer</span>
                      <ArrowRight size={14} />
                    </button>
                  )}
                </div>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                  Select a flagged clause to view exposure analysis
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
