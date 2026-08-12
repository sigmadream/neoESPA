'use client';

import { useState, useEffect, use } from 'react';
import { ChevronLeft, Clock, History, FileCode, CheckCircle2, Save, Play, User as UserIcon, Loader2 } from 'lucide-react';
import Link from 'next/link';
import dynamic from 'next/dynamic';

import { useAuth } from '@/components/AuthProvider';
import { getStudentSnapshots, type CodeSnapshotApi } from '@/lib/api';
import AuthGate from '@/components/AuthGate';

const DiffEditor = dynamic(
  () => import('@monaco-editor/react').then((mod) => mod.DiffEditor),
  { 
    ssr: false,
    loading: () => (
      <div className="h-full w-full flex items-center justify-center bg-slate-900 text-slate-500 text-xs gap-2">
        <Loader2 size={14} className="animate-spin" />
        Loading Editor...
      </div>
    )
  }
);

export default function StudentSnapshotHistoryPage({
  params,
}: {
  params: Promise<{ homework_num: string; user_id: string }>;
}) {
  const { homework_num, user_id } = use(params);
  const { token } = useAuth();
  
  const [snapshots, setSnapshots] = useState<CodeSnapshotApi[]>([]);
  const [selectedSnapshotIndex, setSelectedSnapshotIndex] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadSnapshots() {
      if (!token) return;
      setIsLoading(true);
      try {
        const data = await getStudentSnapshots(Number(homework_num), user_id, token);
        setSnapshots(data);
        if (data.length > 0) {
          setSelectedSnapshotIndex(data.length - 1); // Select the oldest snapshot first, or newest? Let's default to newest (0 index) if sorted descending.
          // Wait, the backend returns order_by(created_at.desc()), so index 0 is newest.
          setSelectedSnapshotIndex(0);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load snapshots.');
      } finally {
        setIsLoading(false);
      }
    }

    void loadSnapshots();
  }, [homework_num, user_id, token]);

  const currentSnapshot = selectedSnapshotIndex !== null ? snapshots[selectedSnapshotIndex] : null;
  // If we are at index i, the previous snapshot in time is at index i+1 (since it's sorted desc)
  const previousSnapshot = selectedSnapshotIndex !== null && selectedSnapshotIndex < snapshots.length - 1 
    ? snapshots[selectedSnapshotIndex + 1] 
    : null;

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'auto_save': return <Save size={12} className="text-slate-400" />;
      case 'run': return <Play size={12} className="text-accent" />;
      case 'manual_save': return <CheckCircle2 size={12} className="text-emerald-500" />;
      default: return <History size={12} className="text-slate-400" />;
    }
  };

  return (
    <AuthGate roles={['admin', 'instructor', 'ta']}>
      <div className="max-w-7xl mx-auto py-8 px-4 space-y-6">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/admin" className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-900 text-slate-500 transition-all">
              <ChevronLeft size={20} />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                <History className="text-accent" size={20} />
                Code Evolution
              </h1>
              <p className="text-slate-500 text-xs font-medium flex items-center gap-2 mt-1">
                <UserIcon size={12} /> {user_id} · Homework #{homework_num}
              </p>
            </div>
          </div>
        </header>

        {isLoading ? (
          <div className="py-20 text-center animate-pulse text-slate-400 font-medium">Syncing student history...</div>
        ) : error ? (
          <div className="card-simple border-rose-100 bg-rose-50 dark:bg-rose-950/20 text-rose-600 dark:text-rose-400 text-sm font-medium p-6">{error}</div>
        ) : snapshots.length === 0 ? (
          <div className="py-20 text-center text-slate-400 border border-dashed rounded italic bg-slate-50/50 dark:bg-slate-900/10">
            No code snapshots found for this student.
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8 h-[700px]">
            {/* Timeline Sidebar */}
            <aside className="lg:col-span-1 border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden flex flex-col bg-white dark:bg-slate-950">
              <div className="p-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
                <h2 className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Snapshot Timeline</h2>
              </div>
              <div className="flex-1 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-900">
                {snapshots.map((snap, idx) => (
                  <button
                    key={snap.id}
                    onClick={() => setSelectedSnapshotIndex(idx)}
                    className={`w-full text-left p-3 hover:bg-slate-50 dark:hover:bg-slate-900/50 transition-all ${
                      selectedSnapshotIndex === idx ? 'bg-accent/10 border-l-4 border-accent' : 'border-l-4 border-transparent'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      {getTypeIcon(snap.snapshot_type)}
                      <span className={`text-[10px] font-bold uppercase ${
                        selectedSnapshotIndex === idx ? 'text-accent' : 'text-slate-500'
                      }`}>
                        {snap.snapshot_type.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs font-bold text-slate-900 dark:text-slate-100">
                      <Clock size={10} className="text-slate-400" />
                      {new Date(snap.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </div>
                    <div className="text-[10px] text-slate-400 mt-1">
                      {new Date(snap.created_at).toLocaleDateString()}
                    </div>
                  </button>
                ))}
              </div>
            </aside>

            {/* Code Viewer Area */}
            <section className="lg:col-span-3 border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden flex flex-col bg-[#1e1e1e]">
              <div className="p-3 border-b border-slate-800 bg-[#1e1e1e] flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <FileCode size={14} className="text-accent" />
                  <span className="text-xs font-mono text-slate-300">
                    Snapshot {currentSnapshot?.id} · {currentSnapshot?.language.toUpperCase()}
                  </span>
                  {previousSnapshot && (
                    <span className="text-[10px] font-mono text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full ml-2">
                      Comparing with Snapshot {previousSnapshot.id}
                    </span>
                  )}
                </div>
                <div className="text-[10px] text-slate-500 font-mono">
                  {currentSnapshot?.code_text.length.toLocaleString()} characters
                </div>
              </div>
              <div className="flex-1 overflow-hidden relative">
                <DiffEditor
                  height="100%"
                  language={currentSnapshot?.language === 'python' ? 'python' : currentSnapshot?.language === 'java' ? 'java' : 'cpp'}
                  theme="vs-dark"
                  original={previousSnapshot?.code_text || ''}
                  modified={currentSnapshot?.code_text || ''}
                  options={{
                    readOnly: true,
                    renderSideBySide: true,
                    minimap: { enabled: false },
                    fontSize: 13,
                    wordWrap: 'on',
                    scrollBeyondLastLine: false,
                    padding: { top: 16, bottom: 16 }
                  }}
                />
              </div>
            </section>
          </div>
        )}
      </div>
    </AuthGate>
  );
}
