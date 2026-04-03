'use client';

import { useEffect, useState, useCallback } from 'react';
import { Plus, Trash2, RefreshCw, BookOpen, Clock, ShieldCheck, CheckCircle2, X, LayoutList, History } from 'lucide-react';
import Link from 'next/link';

import { useAuth } from '@/components/AuthProvider';
import {
  createAdminHomework,
  deleteAdminHomework,
  getAdminHomeworks,
  updateAdminHomework,
  type HomeworkAdminApi,
  type HomeworkAdminPayload,
  type HomeworkTestCaseApi,
} from '@/lib/api';

const LANGUAGE_OPTIONS = ['c', 'cpp', 'python', 'java'] as const;

function createEmptyHomeworkForm(): HomeworkAdminPayload {
  return {
    title: '', intro: '', deadline: '', codeName: '', filename: '',
    ratedatanum: 0, sec: 1, sbnum: 10, starttime: '',
    isDetected: false, vitalSpace: false, disorderedOutput: false, isLint: false,
    allowed_languages: [...LANGUAGE_OPTIONS], testcases: [], lint_week: '',
  };
}

function getHomeworkStatus(homework: HomeworkAdminApi) {
  if (homework.schedule_status === 'upcoming') return { label: 'Upcoming', className: 'text-amber-600 bg-amber-50 dark:bg-amber-950/20' };
  if (homework.schedule_status === 'closed') return { label: 'Closed', className: 'text-rose-600 bg-rose-50 dark:bg-rose-950/20' };
  return { label: 'Open', className: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-950/20' };
}

export default function AdminHomeworkManager() {
  const { token } = useAuth();
  const [homeworks, setHomeworks] = useState<HomeworkAdminApi[]>([]);
  const [form, setForm] = useState<HomeworkAdminPayload>(() => createEmptyHomeworkForm());
  const [editingHomeworkNum, setEditingHomeworkNum] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const loadHomeworks = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      const response = await getAdminHomeworks(token);
      setHomeworks(response);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Load failed.');
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => { void loadHomeworks(); }, [loadHomeworks]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setIsSaving(true);
    setErrorMessage('');
    try {
      if (editingHomeworkNum === null) {
        await createAdminHomework(form, token);
        setSuccessMessage('Created successfully.');
      } else {
        await updateAdminHomework(editingHomeworkNum, form, token);
        setSuccessMessage('Updated successfully.');
      }
      setEditingHomeworkNum(null);
      setForm(createEmptyHomeworkForm());
      await loadHomeworks();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Save failed.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (num: number) => {
    if (!token || !window.confirm('Delete homework?')) return;
    try {
      await deleteAdminHomework(num, token);
      setSuccessMessage('Deleted.');
      await loadHomeworks();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Delete failed.');
    }
  };

  const handleEdit = (hw: HomeworkAdminApi) => {
    setEditingHomeworkNum(hw.num);
    setForm({ ...hw, deadline: hw.deadline ?? '', starttime: hw.starttime ?? '', filename: hw.filename ?? '', lint_week: hw.lint_week ?? '' });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: 'Total Tasks', value: homeworks.length, icon: BookOpen },
          { label: 'Active', value: homeworks.filter(h => ['open', 'closing_soon'].includes(h.schedule_status)).length, icon: CheckCircle2 },
          { label: 'Lint Enabled', value: homeworks.filter(h => h.isLint).length, icon: ShieldCheck },
        ].map((stat) => (
          <div key={stat.label} className="card-simple py-4 px-5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 flex items-center justify-between mb-1">
              {stat.label}
              <stat.icon size={12} className="opacity-50" />
            </span>
            <span className="text-2xl font-black text-slate-900 dark:text-white">{stat.value}</span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        <section className="card-simple">
          <header className="flex items-center justify-between mb-6">
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400">
              {editingHomeworkNum ? 'Edit Homework' : 'Create Homework'}
            </h2>
            {editingHomeworkNum && (
              <button onClick={() => { setEditingHomeworkNum(null); setForm(createEmptyHomeworkForm()); }} className="text-xs font-bold text-slate-400 hover:text-rose-500 flex items-center gap-1 transition-colors">
                <X size={14} /> Cancel Edit
              </button>
            )}
          </header>

          <form onSubmit={(e) => void handleSubmit(e)} className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Title</label>
                <input value={form.title} onChange={e => setForm({...form, title: e.target.value})} required className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent" placeholder="e.g. Recursion Lab" />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Code Name</label>
                <input value={form.codeName} onChange={e => setForm({...form, codeName: e.target.value})} required className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent font-mono" placeholder="recursion" />
              </div>
            </div>

            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Description (Intro)</label>
              <textarea value={form.intro} onChange={e => setForm({...form, intro: e.target.value})} rows={5} required className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent resize-none" placeholder="Task requirements..." />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 flex items-center gap-1.5"><Clock size={10} /> Start Time</label>
                <input value={form.starttime ?? ''} onChange={e => setForm({...form, starttime: e.target.value})} className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none" placeholder="YYYY-MM-DD HH:MM:SS" />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 flex items-center gap-1.5"><Clock size={10} /> Deadline</label>
                <input value={form.deadline ?? ''} onChange={e => setForm({...form, deadline: e.target.value})} className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none" placeholder="YYYY-MM-DD HH:MM:SS" />
              </div>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              {[
                { label: 'Limit (s)', key: 'sec' as keyof HomeworkAdminPayload },
                { label: 'Cases', key: 'ratedatanum' as keyof HomeworkAdminPayload },
                { label: 'Max Attempts', key: 'sbnum' as keyof HomeworkAdminPayload },
                { label: 'Lint Week', key: 'lint_week' as keyof HomeworkAdminPayload },
              ].map(item => (
                <div key={item.key}>
                  <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">{item.label}</label>
                  <input type="text" value={String(form[item.key] ?? '')} onChange={e => setForm({...form, [item.key]: e.target.value})} className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none" />
                </div>
              ))}
            </div>

            <div className="p-4 rounded bg-slate-50 dark:bg-slate-900/50 border border-slate-100 dark:border-slate-800">
              <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3">Allowed Languages</h3>
              <div className="flex flex-wrap gap-4">
                {LANGUAGE_OPTIONS.map(lang => (
                  <label key={lang} className="flex items-center gap-2 text-xs font-medium cursor-pointer group">
                    <input type="checkbox" checked={form.allowed_languages.includes(lang)} onChange={() => {
                      const active = form.allowed_languages.includes(lang);
                      setForm({...form, allowed_languages: active ? form.allowed_languages.filter(l => l !== lang) : [...form.allowed_languages, lang]});
                    }} className="rounded border-slate-300 text-accent focus:ring-accent" />
                    <span className="text-slate-600 dark:text-slate-400 group-hover:text-slate-900 transition-colors">{lang.toUpperCase()}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap gap-4 pt-2">
              {[
                { label: 'Lint Score', key: 'isLint' as keyof HomeworkAdminPayload },
                { label: 'Whitespace Sensitive', key: 'vitalSpace' as keyof HomeworkAdminPayload },
                { label: 'Unordered Output', key: 'disorderedOutput' as keyof HomeworkAdminPayload },
              ].map(opt => (
                <label key={opt.key} className="flex items-center gap-2 text-xs font-medium cursor-pointer group">
                  <input type="checkbox" checked={Boolean(form[opt.key])} onChange={e => setForm({...form, [opt.key]: e.target.checked})} className="rounded border-slate-300 text-accent focus:ring-accent" />
                  <span className="text-slate-600 dark:text-slate-400 group-hover:text-slate-900 transition-colors">{opt.label}</span>
                </label>
              ))}
            </div>

            {(errorMessage || successMessage) && (
              <div className={`p-3 rounded text-[11px] font-medium border ${errorMessage ? 'bg-rose-50 border-rose-100 text-rose-600 dark:bg-rose-950/20' : 'bg-emerald-50 border-emerald-100 text-emerald-600 dark:bg-emerald-950/20'}`}>
                {errorMessage || successMessage}
              </div>
            )}

            <button type="submit" disabled={isSaving} className="btn-flat w-full h-11 flex items-center justify-center gap-2 shadow-sm disabled:opacity-50">
              {isSaving ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Plus size={16} />}
              <span>{editingHomeworkNum ? 'Update Assignment' : 'Create Assignment'}</span>
            </button>
          </form>
        </section>

        <section className="card-simple">
          <header className="flex items-center justify-between mb-6">
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2">
              <LayoutList size={14} />
              Homework Inventory
            </h2>
            <button onClick={() => void loadHomeworks()} className="p-1.5 rounded hover:bg-slate-50 dark:hover:bg-slate-900 text-slate-400 transition-all"><RefreshCw size={14} /></button>
          </header>

          <div className="space-y-3">
            {isLoading ? (
              <div className="py-12 text-center text-xs text-slate-400 animate-pulse">Syncing homeworks...</div>
            ) : homeworks.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-400 border border-dashed rounded italic">No assignments created yet.</div>
            ) : (
              homeworks.map(hw => {
                const status = getHomeworkStatus(hw);
                return (
                  <div key={hw.num} className="group p-4 rounded border border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-950/20 hover:border-accent transition-all">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-1.5">
                          <span className={`text-[9px] px-2 py-0.5 rounded-full font-bold uppercase tracking-tighter ${status.className}`}>{status.label}</span>
                          <span className="text-xs font-bold text-slate-900 dark:text-slate-100">#{hw.num} {hw.title}</span>
                        </div>
                        <p className="text-[10px] text-slate-400 font-mono mb-2">{hw.codeName} · Start: {hw.starttime ?? 'Now'} · End: {hw.deadline ?? 'None'}</p>
                        <div className="flex flex-wrap gap-1.5">
                          {hw.allowed_languages.map(l => <span key={l} className="text-[9px] font-bold text-slate-500 bg-slate-50 dark:bg-slate-900 px-1.5 py-0.5 rounded border border-slate-100 dark:border-slate-800">{l.toUpperCase()}</span>)}
                          {hw.isLint && <span className="text-[9px] font-bold text-lime-600 bg-lime-50 dark:bg-lime-900/20 px-1.5 py-0.5 rounded border border-lime-100 dark:border-lime-900/30">LINT</span>}
                        </div>
                      </div>
                      <div className="flex flex-col gap-2">
                        <button onClick={() => handleEdit(hw)} className="p-2 rounded bg-slate-50 dark:bg-slate-900 text-slate-400 hover:text-accent transition-all hover:bg-white border border-transparent hover:border-slate-100"><Plus size={14} /></button>
                        <button onClick={() => void handleDelete(hw.num)} className="p-2 rounded bg-slate-50 dark:bg-slate-900 text-slate-400 hover:text-rose-500 transition-all hover:bg-white border border-transparent hover:border-slate-100"><Trash2 size={14} /></button>
                      </div>
                    </div>
                    
                    <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <History size={12} className="text-slate-400" />
                        <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Snapshots</span>
                      </div>
                      <form 
                        onSubmit={(e) => {
                          e.preventDefault();
                          const input = e.currentTarget.elements.namedItem('userId') as HTMLInputElement;
                          if (input.value.trim()) {
                            window.location.href = `/admin/snapshots/${hw.num}/${input.value.trim()}`;
                          }
                        }} 
                        className="flex items-center gap-2"
                      >
                        <input 
                          type="text" 
                          name="userId" 
                          placeholder="Student ID" 
                          required
                          className="text-xs px-2 py-1 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 outline-none focus:border-accent w-28" 
                        />
                        <button type="submit" className="text-[10px] font-bold px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-accent hover:text-white transition-colors">
                          View
                        </button>
                      </form>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
