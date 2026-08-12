'use client';

import { useEffect, useRef, useState } from 'react';
import { FileText, Plus, Save, RefreshCw, ExternalLink, Eye, EyeOff, User, LayoutList, Paperclip } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import {
  createAdminMaterial,
  getMaterials,
  uploadMaterialAttachment,
  type LectureMaterialApi,
  type LectureMaterialPayload,
} from '@/lib/api';

const INITIAL_FORM: LectureMaterialPayload = {
  title: '',
  description: '',
  url: '',
  content: '',
  is_published: true,
};

export default function AdminMaterialManager() {
  const { token } = useAuth();
  const [materials, setMaterials] = useState<LectureMaterialApi[]>([]);
  const [form, setForm] = useState<LectureMaterialPayload>(INITIAL_FORM);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const attachmentInputRef = useRef<HTMLInputElement>(null);

  const loadMaterials = async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      const response = await getMaterials(token);
      setMaterials(response);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Load failed.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { void loadMaterials(); }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setIsSaving(true);
    setErrorMessage('');
    try {
      let created = await createAdminMaterial(form, token);
      const attachment = attachmentInputRef.current?.files?.[0];
      if (attachment) {
        created = await uploadMaterialAttachment(created.id, attachment, token);
      }
      setMaterials(prev => [created, ...prev]);
      setForm(INITIAL_FORM);
      if (attachmentInputRef.current) {
        attachmentInputRef.current.value = '';
      }
      setSuccessMessage('Material registered successfully.');
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Registration failed.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
      <section className="xl:col-span-1">
        <form onSubmit={(e) => void handleSubmit(e)} className="card-simple space-y-6">
          <header className="mb-2">
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400">새 강의자료 등록</h2>
            <p className="text-[11px] text-slate-500 mt-1">수강생을 위한 강의 슬라이드, 예제 코드 및 참고 문서를 게시합니다.</p>
          </header>

          <div className="space-y-4">
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">자료 제목</label>
              <input value={form.title} onChange={e => setForm({...form, title: e.target.value})} required className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent" placeholder="예: 5주차 재귀함수 실습 강의 자료" />
            </div>
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">참고 URL 링크 (선택 사항)</label>
              <input value={form.url} onChange={e => setForm({...form, url: e.target.value})} className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent font-mono" placeholder="https://drive.google.com/..." />
            </div>
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">요약 설명</label>
              <textarea value={form.description} onChange={e => setForm({...form, description: e.target.value})} rows={4} required className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent resize-none" placeholder="강의자료에 대한 요약 설명을 입력하세요..." />
            </div>
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">상세 문서 본문 (선택 사항, 마크다운 지원)</label>
              <textarea value={form.content ?? ''} onChange={e => setForm({...form, content: e.target.value})} rows={6} className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent resize-none" placeholder="자료 게시판에 노출될 전체 본문 내용을 입력하세요..." />
            </div>
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">첨부파일 (선택 사항)</label>
              <input ref={attachmentInputRef} type="file" className="block w-full text-xs text-slate-500 file:mr-3 file:rounded file:border-0 file:bg-slate-100 dark:file:bg-slate-800 file:px-3 file:py-1.5 file:text-xs file:font-medium" />
            </div>
          </div>

          <label className="flex items-center gap-2 text-xs font-medium cursor-pointer group py-1">
            <input type="checkbox" checked={form.is_published} onChange={e => setForm({...form, is_published: e.target.checked})} className="rounded border-slate-300 text-accent focus:ring-accent" />
            <span className="text-slate-600 dark:text-slate-400 group-hover:text-slate-900 transition-colors">등록 즉시 공개 게시</span>
          </label>

          {(errorMessage || successMessage) && (
            <div className={`p-3 rounded text-[11px] font-medium border ${errorMessage ? 'bg-rose-50 border-rose-100 text-rose-600 dark:bg-rose-950/20' : 'bg-emerald-50 border-emerald-100 text-emerald-600 dark:bg-emerald-950/20'}`}>
              {errorMessage || successMessage}
            </div>
          )}

          <button type="submit" disabled={isSaving} className="btn-flat w-full h-11 flex items-center justify-center gap-2 shadow-sm disabled:opacity-50">
            {isSaving ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Plus size={16} />}
            <span>강의자료 등록하기</span>
          </button>
        </form>
      </section>

      <section className="xl:col-span-2">
        <div className="card-simple h-full">
          <header className="flex items-center justify-between mb-6">
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2">
              <LayoutList size={14} />
              등록된 강의자료 목록
            </h2>
            <button onClick={() => void loadMaterials()} className="p-1.5 rounded hover:bg-slate-50 dark:hover:bg-slate-900 text-slate-400 transition-all"><RefreshCw size={14} /></button>
          </header>

          <div className="space-y-4">
            {isLoading ? (
              <div className="py-12 text-center text-xs text-slate-400 animate-pulse">강의자료 목록을 동기화 중입니다...</div>
            ) : materials.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-400 border border-dashed rounded italic">등록된 강의자료가 없습니다.</div>
            ) : (
              materials.map(m => (
                <div key={m.id} className={`group p-4 rounded border border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-950/20 hover:border-accent transition-all ${!m.is_published ? 'opacity-60 grayscale-[0.5]' : ''}`}>
                  <div className="flex items-start justify-between gap-6">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className={`text-[9px] px-2 py-0.5 rounded-full font-bold uppercase tracking-tighter ${m.is_published ? 'text-emerald-600 bg-emerald-50 dark:bg-emerald-950/20' : 'text-slate-400 bg-slate-50 dark:bg-slate-900'}`}>
                          {m.is_published ? '공개됨' : '비공개(초안)'}
                        </span>
                        <span className="text-xs font-bold text-slate-900 dark:text-slate-100">{m.title}</span>
                      </div>
                      <p className="text-[11px] text-slate-500 leading-relaxed line-clamp-2">{m.description}</p>
                      <div className="flex items-center gap-3 mt-3 text-[10px] text-slate-400 font-medium">
                        <span className="flex items-center gap-1"><User size={10} /> {m.created_by}</span>
                        <span className="w-1 h-1 rounded-full bg-slate-200" />
                        <span className="truncate max-w-[200px] font-mono">{m.url}</span>
                      </div>
                    </div>
                    {m.url && (
                      <a href={m.url} target="_blank" rel="noreferrer" className="btn-outline h-9 px-3 text-[11px] flex items-center gap-1.5 whitespace-nowrap bg-white dark:bg-transparent hover:text-accent">
                        <ExternalLink size={12} /> 링크 열기
                      </a>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
