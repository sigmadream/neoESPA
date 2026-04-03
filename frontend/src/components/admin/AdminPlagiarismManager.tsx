'use client';

import { useEffect, useState } from 'react';
import { ShieldAlert, Search, Play, FileCode, Users, ArrowRightLeft, RefreshCw, ChevronRight, History } from 'lucide-react';
import Link from 'next/link';

import { useAuth } from '@/components/AuthProvider';
import {
  getAdminHomeworks,
  getPlagiarismPairDetail,
  getPlagiarismPairs,
  runHomeworkPlagiarismScan,
  type HomeworkAdminApi,
  type PlagiarismPairApi,
} from '@/lib/api';

export default function AdminPlagiarismManager() {
  const { token } = useAuth();
  const [homeworks, setHomeworks] = useState<HomeworkAdminApi[]>([]);
  const [selectedHomeworkNum, setSelectedHomeworkNum] = useState<string>('');
  const [pairs, setPairs] = useState<PlagiarismPairApi[]>([]);
  const [selectedPair, setSelectedPair] = useState<PlagiarismPairApi | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const loadInitialData = async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      const [hwRes, pRes] = await Promise.all([getAdminHomeworks(token), getPlagiarismPairs(token)]);
      setHomeworks(hwRes);
      setPairs(pRes);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Load failed.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { void loadInitialData(); }, [token]);

  const handleRunScan = async () => {
    if (!token || !selectedHomeworkNum) return;
    setIsRunning(true);
    setErrorMessage('');
    try {
      const run = await runHomeworkPlagiarismScan(Number(selectedHomeworkNum), token);
      const updatedPairs = await getPlagiarismPairs(token, { homework_num: Number(selectedHomeworkNum) });
      setPairs(updatedPairs);
      setSuccessMessage(`Scan complete: ${run.flagged_pair_count} pairs flagged.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Scan failed.');
    } finally {
      setIsRunning(false);
    }
  };

  const handleSelectPair = async (pairId: number) => {
    if (!token) return;
    try {
      const detail = await getPlagiarismPairDetail(pairId, token);
      setSelectedPair(detail);
    } catch { /* ignore */ }
  };

  if (isLoading) return <div className="py-20 text-center animate-pulse text-slate-400 font-medium">Loading plagiarism tools...</div>;

  return (
    <div className="space-y-8">
      <section className="card-simple">
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-2">
              <ShieldAlert size={16} className="text-rose-500" />
              Plagiarism Review
            </h2>
            <p className="text-slate-500 text-sm font-medium leading-relaxed">Run similarity checks across student submissions and compare source code.</p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={selectedHomeworkNum}
              onChange={e => setSelectedHomeworkNum(e.target.value)}
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
            >
              <option value="">Select Homework</option>
              {homeworks.map(h => <option key={h.num} value={h.num}>#{h.num} {h.title}</option>)}
            </select>
            <button
              onClick={() => void handleRunScan()}
              disabled={isRunning || !selectedHomeworkNum}
              className="btn-flat text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
            >
              {isRunning ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
              Run Scan
            </button>
          </div>
        </header>

        {(errorMessage || successMessage) && (
          <div className={`p-3 rounded text-[11px] font-medium border mb-6 ${errorMessage ? 'bg-rose-50 border-rose-100 text-rose-600 dark:bg-rose-950/20' : 'bg-emerald-50 border-emerald-100 text-emerald-600 dark:bg-emerald-950/20'}`}>
            {errorMessage || successMessage}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-1 space-y-4">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">Flagged Pairs</h3>
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
              {pairs.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-400 border border-dashed rounded italic">No pairs detected.</div>
              ) : (
                pairs.map(p => (
                  <button
                    key={p.id}
                    onClick={() => void handleSelectPair(p.id)}
                    className={`w-full text-left p-3 rounded border transition-all ${selectedPair?.id === p.id ? 'border-rose-500 bg-rose-50/10' : 'border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900'}`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <span className="text-[11px] font-bold truncate">{p.left_user_id} vs {p.right_user_id}</span>
                      <span className="text-[10px] font-black text-rose-600 dark:text-rose-400">{(p.similarity_score * 100).toFixed(1)}%</span>
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-slate-400 font-medium">
                      <span>HW #{p.homework_num}</span>
                      <ChevronRight size={12} />
                    </div>
                  </button>
                ))
              )}
          <div className="lg:col-span-2 space-y-4">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">Source Comparison</h3>
            {selectedPair ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  { user: selectedPair.left_user_id, code: selectedPair.left_code },
                  { user: selectedPair.right_user_id, code: selectedPair.right_code },
                ].map((side, idx) => (
                  <div key={idx} className="space-y-2">
                    <div className="flex items-center justify-between px-2">
                      <div className="flex items-center gap-2">
                        <FileCode size={12} className="text-slate-400" />
                        <span className="text-[11px] font-bold text-slate-600 dark:text-slate-300">{side.user}</span>
                      </div>
                      <Link 
                        href={`/admin/snapshots/${selectedPair.homework_num}/${side.user}`} 
                        className="text-[10px] font-bold text-accent hover:underline flex items-center gap-1"
                      >
                        <History size={10} /> View Timeline
                      </Link>
                    </div>
                    <div className="rounded-md bg-slate-950 p-4 font-mono text-[11px] text-emerald-400/90 leading-relaxed overflow-auto max-h-[500px] min-h-[300px] border border-slate-800 shadow-inner">
                      <pre>{side.code || '// No code available'}</pre>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-[400px] flex flex-col items-center justify-center border border-dashed rounded-md bg-slate-50/30 dark:bg-slate-900/10">
                <ArrowRightLeft size={32} className="text-slate-200 mb-4" />
                <p className="text-xs text-slate-400 font-medium">Select a pair to compare source side-by-side.</p>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
