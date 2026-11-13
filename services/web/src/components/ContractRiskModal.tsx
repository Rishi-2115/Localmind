import React, { useState, useEffect } from 'react';
import { ShieldAlert, AlertTriangle, CheckCircle, ChevronRight, FileText, ArrowRight, X } from 'lucide-react';
import { getAuthHeaders, API_BASE } from '../store/authStore';
import { useThemeStore } from '../store/themeStore';

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
  const { theme } = useThemeStore();
  const isDark = theme === 'dark';

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

  const getTierBadge = (tier: string) => {
    if (isDark) {
      switch (tier) {
        case 'CRITICAL':
          return 'text-rose-400 bg-rose-500/15 border-rose-500/40 shadow-[0_0_12px_rgba(244,63,94,0.3)]';
        case 'HIGH':
          return 'text-[#FF8533] bg-orange-500/15 border-orange-500/40 shadow-[0_0_12px_rgba(255,107,0,0.3)]';
        case 'MEDIUM':
          return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
        default:
          return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
      }
    } else {
      switch (tier) {
        case 'CRITICAL':
          return 'text-rose-700 bg-rose-50 border-rose-200';
        case 'HIGH':
          return 'text-black bg-yellow-300 border-yellow-400 font-black';
        case 'MEDIUM':
          return 'text-zinc-800 bg-zinc-100 border-zinc-300';
        default:
          return 'text-emerald-800 bg-emerald-50 border-emerald-200';
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className={`border rounded-3xl max-w-4xl w-full max-h-[88vh] flex flex-col shadow-2xl overflow-hidden transition-all ${
        isDark 
          ? 'bg-[#030712] border-orange-500/30 shadow-[0_0_50px_rgba(255,107,0,0.2)]' 
          : 'bg-white border-zinc-200 shadow-2xl'
      }`}>
        {/* Header */}
        <div className={`px-7 py-5 border-b flex items-center justify-between ${
          isDark ? 'bg-[#0B132B] border-orange-500/15' : 'bg-zinc-50 border-zinc-200'
        }`}>
          <div className="flex items-center space-x-3.5">
            <div className={`p-2.5 rounded-2xl border ${
              isDark 
                ? 'bg-orange-500/15 border-orange-500/30 text-[#FF6B00]' 
                : 'bg-black text-white border-black'
            }`}>
              <ShieldAlert size={22} />
            </div>
            <div>
              <h2 className={`text-lg font-black flex items-center gap-2.5 ${isDark ? 'text-white' : 'text-black'}`}>
                Contract Vulnerability & Risk Audit
                {report && (
                  <span className={`text-[11px] px-3 py-0.5 rounded-full border font-black uppercase ${getTierBadge(report.risk_tier)}`}>
                    {report.risk_tier} RISK
                  </span>
                )}
              </h2>
              <p className={`text-xs font-mono mt-0.5 ${isDark ? 'text-slate-400' : 'text-zinc-500'}`}>{filename}</p>
            </div>
          </div>
          <button 
            onClick={onClose} 
            className={`p-2 rounded-xl transition-colors ${
              isDark ? 'text-slate-400 hover:text-white hover:bg-slate-800' : 'text-zinc-500 hover:text-black hover:bg-zinc-200'
            }`}
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="p-16 flex flex-col items-center justify-center text-center">
            <div className={`w-8 h-8 border-3 border-t-transparent rounded-full animate-spin mb-4 ${
              isDark ? 'border-[#FF6B00]' : 'border-black'
            }`} />
            <p className={`text-xs font-bold ${isDark ? 'text-slate-400' : 'text-zinc-600'}`}>
              Auditing clauses against corporate playbook guidelines...
            </p>
          </div>
        ) : !report || report.risks.length === 0 ? (
          <div className="p-16 text-center">
            <CheckCircle size={48} className="mx-auto text-emerald-500 mb-3" />
            <h3 className={`text-base font-bold ${isDark ? 'text-white' : 'text-black'}`}>No High-Risk Clauses Flagged</h3>
            <p className={`text-xs mt-1 max-w-md mx-auto ${isDark ? 'text-slate-400' : 'text-zinc-500'}`}>
              The document meets standard bilateral commercial thresholds with reciprocal liability protection.
            </p>
          </div>
        ) : (
          <div className="flex-1 grid grid-cols-1 md:grid-cols-12 min-h-0 overflow-hidden">
            {/* Left Column: Risk List */}
            <div className={`md:col-span-5 border-r overflow-y-auto p-4 space-y-2.5 ${
              isDark ? 'border-orange-500/10 bg-[#0B132B]/40' : 'border-zinc-200 bg-zinc-50/50'
            }`}>
              <div className="text-[10px] font-black uppercase tracking-wider px-2 mb-1 text-slate-400">
                Identified Exposures ({report.risks.length})
              </div>
              {report.risks.map((r) => {
                const isSelected = selectedRisk?.id === r.id;
                return (
                  <div
                    key={r.id}
                    onClick={() => setSelectedRisk(r)}
                    className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                      isSelected
                        ? isDark
                          ? 'bg-[#FF6B00]/10 border-[#FF6B00] shadow-[0_0_20px_rgba(255,107,0,0.2)]'
                          : 'bg-black text-white border-black shadow-md'
                        : isDark
                          ? 'bg-[#030712] border-slate-800 hover:border-orange-500/40 text-slate-300'
                          : 'bg-white border-zinc-200 hover:border-black text-zinc-800'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-bold capitalize">{r.clause_type.replace('_', ' ')}</span>
                      <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full border ${getTierBadge(r.risk_level)}`}>
                        {r.risk_level}
                      </span>
                    </div>
                    <p className={`text-xs line-clamp-2 leading-relaxed ${
                      isSelected && !isDark ? 'text-zinc-300' : 'opacity-80'
                    }`}>
                      {r.reasoning}
                    </p>
                    <div className="mt-2.5 flex items-center justify-between text-[11px] font-semibold opacity-70">
                      <span>Anchor: Page {r.page_number}</span>
                      <ChevronRight size={14} />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Right Column: In-Depth Playbook Audit */}
            <div className={`md:col-span-7 overflow-y-auto p-6 ${
              isDark ? 'bg-[#030712]' : 'bg-white'
            }`}>
              {selectedRisk ? (
                <div className="space-y-5 animate-fade-in">
                  <div>
                    <div className="flex items-center justify-between">
                      <h3 className={`text-base font-black capitalize ${isDark ? 'text-white' : 'text-black'}`}>
                        {selectedRisk.clause_type.replace('_', ' ')} Exposure
                      </h3>
                      <span className={`text-xs px-3 py-1 rounded-xl border font-black uppercase ${getTierBadge(selectedRisk.risk_level)}`}>
                        {selectedRisk.risk_level} SEVERITY
                      </span>
                    </div>
                    <div className={`mt-1 flex items-center text-xs font-semibold ${isDark ? 'text-slate-400' : 'text-zinc-500'}`}>
                      <FileText size={13} className={`mr-1 ${isDark ? "text-[#FF6B00]" : "text-black"}`} />
                      Document Citation Anchor: Page {selectedRisk.page_number}
                    </div>
                  </div>

                  {/* Excerpt */}
                  <div className={`rounded-2xl p-4 border ${
                    isDark ? 'bg-[#0B132B]/80 border-slate-800' : 'bg-zinc-50 border-zinc-200'
                  }`}>
                    <div className="text-[10px] font-black uppercase tracking-wider mb-2 text-slate-400">Verbatim Contract Clause</div>
                    <p className={`text-xs font-mono leading-relaxed italic ${isDark ? 'text-slate-200' : 'text-zinc-900'}`}>
                      "{selectedRisk.excerpt}"
                    </p>
                  </div>

                  {/* Legal Exposure Reasoning */}
                  <div className={`rounded-2xl p-4 border ${
                    isDark ? 'bg-rose-500/10 border-rose-500/25' : 'bg-rose-50 border-rose-200'
                  }`}>
                    <div className="flex items-center text-xs font-black text-rose-500 mb-1.5">
                      <AlertTriangle size={15} className="mr-1.5" /> Legal & Commercial Exposure
                    </div>
                    <p className={`text-xs leading-relaxed ${isDark ? 'text-slate-200' : 'text-zinc-800'}`}>
                      {selectedRisk.reasoning}
                    </p>
                  </div>

                  {/* Playbook Edit Recommendation */}
                  <div className={`rounded-2xl p-4 border ${
                    isDark ? 'bg-orange-500/10 border-orange-500/30' : 'bg-yellow-50 border-yellow-200'
                  }`}>
                    <div className={`flex items-center text-xs font-black mb-1.5 ${isDark ? 'text-[#FF8533]' : 'text-black'}`}>
                      <CheckCircle size={15} className="mr-1.5" /> Recommended Playbook Counter-Proposal
                    </div>
                    <p className={`text-xs leading-relaxed ${isDark ? 'text-slate-200' : 'text-zinc-800'}`}>
                      {selectedRisk.recommendation}
                    </p>
                  </div>

                  {/* Action */}
                  {onSelectClause && (
                    <button
                      onClick={() => onSelectClause(selectedRisk.page_number, selectedRisk.excerpt)}
                      className={`w-full py-3 rounded-2xl text-xs font-black transition-all shadow-lg flex items-center justify-center space-x-2 ${
                        isDark 
                          ? 'bg-gradient-to-r from-orange-500 to-[#FF4500] text-black shadow-orange-500/25 hover:brightness-110' 
                          : 'bg-black text-white hover:bg-zinc-800 shadow-black/10'
                      }`}
                    >
                      <span>Jump to Page {selectedRisk.page_number} in Split-Screen</span>
                      <ArrowRight size={14} />
                    </button>
                  )}
                </div>
              ) : (
                <div className="h-full flex items-center justify-center text-xs text-slate-500">
                  Select a clause on the left to examine vulnerability audit
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
