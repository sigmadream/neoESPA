'use client';

import { useCallback, useEffect, useState } from 'react';
import { Megaphone, Pin, Plus, Save, Trash2, RefreshCw, X, Calendar, User, Eye, LayoutList } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import {
  createAdminNotice,
  deleteAdminNotice,
  getAdminNotices,
  updateAdminNotice,
  type NoticeAdminPayload,
  type NoticeApi,
} from '@/lib/api';

function createEmptyForm(defaultAuthor: string): NoticeAdminPayload {
  return { title: '', author: defaultAuthor, content: '', date: '', is_pinned: false, is_published: true };
}

function getNoticeStatus(notice: NoticeApi) {
  if (!notice.is_published) return { label: 'Draft', className: 'text-slate-400 bg-slate-50 dark:bg-slate-900' };
  const publishAt = new Date(notice.date.replace(' ', 'T')).getTime();
  if (!Number.isNaN(publishAt) && publishAt > Date.now()) return { label: 'Scheduled', className: 'text-amber-600 bg-amber-50 dark:bg-amber-950/20' };
  return { label: 'Published', className: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-950/20' };
}

export default function AdminNoticeManager() {
  const { token, user } = useAuth();
  const [notices, setNotices] = useState<NoticeApi[]>([]);
  const [form, setForm] = useState<NoticeAdminPayload>(() => createEmptyForm(''));
  const [editingNoticeNum, setEditingNoticeNum] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    if (user && editingNoticeNum === null) {
      setForm(prev => ({ ...prev, author: prev.author || user.name || user.id }));
    }
  }, [editingNoticeNum, user]);

  const loadNotices = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      const response = await getAdminNotices(token);
      setNotices(response);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Load failed.');
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => { void loadNotices(); }, [loadNotices]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setIsSaving(true);
    setErrorMessage('');
    try {
      if (editingNoticeNum === null) {
        await createAdminNotice(form, token);
        setSuccessMessage('Notice created.');
      } else {
        await updateAdminNotice(editingNoticeNum, form, token);
        setSuccessMessage('Notice updated.');
      }
      setEditingNoticeNum(null);
      setForm(createEmptyForm(user?.name || user?.id || ''));
      await loadNotices();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Save failed.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (num: number) => {
    if (!token || !window.confirm('Delete notice?')) return;
    try {
      await deleteAdminNotice(num, token);
      setSuccessMessage('Deleted.');
      await loadNotices();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Delete failed.');
    }
  };

  const handleEdit = (n: NoticeApi) => {
    setEditingNoticeNum(n.num);
    setForm({ ...n });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: '총 공지사항 수', value: `${notices.length}개`, icon: Megaphone },
          { label: '공개됨', value: `${notices.filter(n => n.is_published).length}개`, icon: Eye },
          { label: '고정 공지', value: `${notices.filter(n => n.is_pinned).length}개`, icon: Pin },
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
              {editingNoticeNum ? '공지사항 수정하기' : '새 공지사항 작성하기'}
            </h2>
            {editingNoticeNum && (
              <button onClick={() => { setEditingNoticeNum(null); setForm(createEmptyForm(user?.name || '')); }} className="text-xs font-bold text-slate-400 hover:text-rose-500 flex items-center gap-1 transition-colors">
                <X size={14} /> 취소
              </button>
            )}
          </header>

          <form onSubmit={(e) => void handleSubmit(e)} className="space-y-5">
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">공지 제목</label>
              <input value={form.title} onChange={e => setForm({...form, title: e.target.value})} required className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent" placeholder="예: 2026학년도 중간고사 일정 안내" />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 flex items-center gap-1.5"><User size={10} /> 작성자</label>
                <input value={form.author} onChange={e => setForm({...form, author: e.target.value})} className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none" />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 flex items-center gap-1.5"><Calendar size={10} /> Publish Date</label>
                <input value={form.date ?? ''} onChange={e => setForm({...form, date: e.target.value})} className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none" placeholder="YYYY-MM-DD HH:MM:SS" />
              </div>
            </div>

            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Notice Body</label>
              <textarea value={form.content} onChange={e => setForm({...form, content: e.target.value})} rows={10} required className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent resize-none" placeholder="Enter content here..." />
            </div>

            <div className="flex gap-6 py-2">
              <label className="flex items-center gap-2 text-xs font-medium cursor-pointer group">
                <input type="checkbox" checked={form.is_pinned} onChange={e => setForm({...form, is_pinned: e.target.checked})} className="rounded border-slate-300 text-accent focus:ring-accent" />
                <span className="text-slate-600 dark:text-slate-400 group-hover:text-slate-900 transition-colors">Pin to Top</span>
              </label>
              <label className="flex items-center gap-2 text-xs font-medium cursor-pointer group">
                <input type="checkbox" checked={form.is_published} onChange={e => setForm({...form, is_published: e.target.checked})} className="rounded border-slate-300 text-accent focus:ring-accent" />
                <span className="text-slate-600 dark:text-slate-400 group-hover:text-slate-900 transition-colors">Published</span>
              </label>
            </div>

            {(errorMessage || successMessage) && (
              <div className={`p-3 rounded text-[11px] font-medium border ${errorMessage ? 'bg-rose-50 border-rose-100 text-rose-600 dark:bg-rose-950/20' : 'bg-emerald-50 border-emerald-100 text-emerald-600 dark:bg-emerald-950/20'}`}>
                {errorMessage || successMessage}
              </div>
            )}

            <button type="submit" disabled={isSaving} className="btn-flat w-full h-11 flex items-center justify-center gap-2 shadow-sm">
              {isSaving ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Save size={16} />}
              <span>{editingNoticeNum ? '공지 수정 내용 저장' : '공지사항 게시하기'}</span>
            </button>
          </form>
        </section>

        <section className="card-simple">
          <header className="flex items-center justify-between mb-6">
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2">
              <LayoutList size={14} />
              등록된 공지사항 목록
            </h2>
            <button onClick={() => void loadNotices()} className="p-1.5 rounded hover:bg-slate-50 dark:hover:bg-slate-900 text-slate-400 transition-all"><RefreshCw size={14} /></button>
          </header>

          <div className="space-y-3">
            {isLoading ? (
              <div className="py-12 text-center text-xs text-slate-400 animate-pulse">공지사항 목록을 동기화 중입니다...</div>
            ) : notices.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-400 border border-dashed rounded italic">등록된 공지사항이 없습니다.</div>
            ) : (
              notices.map(n => {
                const status = getNoticeStatus(n);
                return (
                  <div key={n.num} className={`group p-4 rounded border border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-950/20 hover:border-accent transition-all ${n.is_pinned ? 'bg-amber-50/5 border-amber-100/50' : ''}`}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-1.5">
                          {n.is_pinned && <span className="p-1 rounded bg-amber-100 text-amber-600 dark:bg-amber-900/20"><Pin size={10} /></span>}
                          <span className={`text-[9px] px-2 py-0.5 rounded-full font-bold uppercase tracking-tighter ${status.className}`}>{status.label}</span>
                          <span className="text-xs font-bold text-slate-900 dark:text-slate-100 truncate">{n.title}</span>
                        </div>
                        <p className="text-[10px] text-slate-400 font-medium mb-2 flex items-center gap-3">
                          <span>By {n.author}</span>
                          <span className="w-1 h-1 rounded-full bg-slate-200" />
                          <span>{n.date}</span>
                        </p>
                        <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">{n.content}</p>
                      </div>
                      <div className="flex flex-col gap-2">
                        <button onClick={() => handleEdit(n)} className="p-2 rounded bg-slate-50 dark:bg-slate-900 text-slate-400 hover:text-accent transition-all hover:bg-white border border-transparent hover:border-slate-100"><Plus size={14} /></button>
                        <button onClick={() => void handleDelete(n.num)} className="p-2 rounded bg-slate-50 dark:bg-slate-900 text-slate-400 hover:text-rose-500 transition-all hover:bg-white border border-transparent hover:border-slate-100"><Trash2 size={14} /></button>
                      </div>
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
