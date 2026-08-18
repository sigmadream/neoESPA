'use client';

import { useEffect, useState, useCallback } from 'react';
import { Plus, Trash2, RefreshCw, BookOpen, Clock, ShieldCheck, CheckCircle2, X, LayoutList, History, FileSpreadsheet, FileArchive, Upload, Link2 } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import {
  attachProblemToHomework,
  createAdminHomework,
  deleteAdminHomework,
  downloadHomeworkGrades,
  downloadHomeworkSubmissionArchive,
  getAdminHomeworks,
  importAdminHomework,
  updateAdminHomework,
  type HomeworkAdminApi,
  type HomeworkAdminPayload,
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
  const [isImporting, setIsImporting] = useState(false);
  const [downloadingKey, setDownloadingKey] = useState('');
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

  const handleDownload = async (
    homeworkNum: number,
    kind: 'grades' | 'archive',
  ) => {
    if (!token) return;
    setDownloadingKey(`${homeworkNum}:${kind}`);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      const filename =
        kind === 'grades'
          ? await downloadHomeworkGrades(homeworkNum, token)
          : await downloadHomeworkSubmissionArchive(homeworkNum, token);
      setSuccessMessage(`${filename} 파일을 내려받았습니다.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '내려받기에 실패했습니다.');
    } finally {
      setDownloadingKey('');
    }
  };

  const handleAttachProblem = async (homeworkNum: number, revisionId: string) => {
    if (!token) return;
    const parsed = Number(revisionId);
    if (!Number.isInteger(parsed) || parsed <= 0) {
      setErrorMessage('연결할 revision 번호를 정확히 입력하십시오.');
      return;
    }
    setErrorMessage('');
    setSuccessMessage('');
    try {
      const attached = await attachProblemToHomework(
        homeworkNum,
        { revision_id: parsed },
        token,
      );
      setSuccessMessage(
        `과제 #${homeworkNum}에 revision #${attached.revision_id}을(를) 연결했습니다.`,
      );
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '문제를 연결하지 못했습니다.',
      );
    }
  };

  const handleImport = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token) return;
    const formElement = event.currentTarget;
    const data = new FormData(formElement);
    const problemFile = data.get('problem_file');
    const inputZip = data.get('input_zip');
    const outputZip = data.get('output_zip');

    if (
      !(problemFile instanceof File) ||
      !(inputZip instanceof File) ||
      !(outputZip instanceof File)
    ) {
      setErrorMessage('문제 파일과 입력/출력 ZIP을 모두 선택하십시오.');
      return;
    }

    setIsImporting(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      const created = await importAdminHomework(
        {
          title: String(data.get('title') ?? ''),
          intro: String(data.get('intro') ?? ''),
          codeName: String(data.get('codeName') ?? ''),
          isLint: data.get('isLint') === 'on',
          problemFile,
          inputZip,
          outputZip,
          deadline: String(data.get('deadline') ?? '') || null,
          starttime: String(data.get('starttime') ?? '') || null,
          lintWeek: String(data.get('lint_week') ?? '') || null,
          allowedLanguages: LANGUAGE_OPTIONS.filter(
            (language) => data.get(`language_${language}`) === 'on',
          ),
        },
        token,
      );
      setSuccessMessage(
        `과제 #${created.num} "${created.title}"을(를) 가져왔습니다. (테스트케이스 ${created.testcases.length}개)`,
      );
      formElement.reset();
      await loadHomeworks();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : '과제 가져오기에 실패했습니다.');
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: '전체 과제 수', value: `${homeworks.length}개`, icon: BookOpen },
          { label: '진행 중 과제', value: `${homeworks.filter(h => ['open', 'closing_soon'].includes(h.schedule_status)).length}개`, icon: CheckCircle2 },
          { label: '코드 품질 검사 적용', value: `${homeworks.filter(h => h.isLint).length}개`, icon: ShieldCheck },
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
              {editingHomeworkNum ? '과제 정보 수정하기' : '새 과제 등록하기'}
            </h2>
            {editingHomeworkNum && (
              <button onClick={() => { setEditingHomeworkNum(null); setForm(createEmptyHomeworkForm()); }} className="text-xs font-bold text-slate-400 hover:text-rose-500 flex items-center gap-1 transition-colors">
                <X size={14} /> 수정 취소
              </button>
            )}
          </header>

          <form onSubmit={(e) => void handleSubmit(e)} className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="homework-title" className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">과제 제목</label>
                <input id="homework-title" value={form.title} onChange={e => setForm({...form, title: e.target.value})} required className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent" placeholder="예: 재귀함수 실습 과제" />
              </div>
              <div>
                <label htmlFor="homework-code-name" className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">코드 식별자 (Code Name)</label>
                <input id="homework-code-name" value={form.codeName} onChange={e => setForm({...form, codeName: e.target.value})} required className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent font-mono" placeholder="recursion" />
              </div>
            </div>

            <div>
              <label htmlFor="homework-intro" className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">과제 설명 및 요구사항 (마크다운 지원)</label>
              <textarea id="homework-intro" value={form.intro} onChange={e => setForm({...form, intro: e.target.value})} rows={5} required className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent resize-none" placeholder="과제 설명 및 작성 지침을 입력하세요..." />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="homework-starttime" className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 flex items-center gap-1.5"><Clock size={10} /> 제출 시작 일시</label>
                <input id="homework-starttime" value={form.starttime ?? ''} onChange={e => setForm({...form, starttime: e.target.value})} className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none" placeholder="YYYY-MM-DD HH:MM:SS" />
              </div>
              <div>
                <label htmlFor="homework-deadline" className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 flex items-center gap-1.5"><Clock size={10} /> 마감 일시</label>
                <input id="homework-deadline" value={form.deadline ?? ''} onChange={e => setForm({...form, deadline: e.target.value})} className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none" placeholder="YYYY-MM-DD HH:MM:SS" />
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
              등록된 과제 목록
            </h2>
            <button onClick={() => void loadHomeworks()} className="p-1.5 rounded hover:bg-slate-50 dark:hover:bg-slate-900 text-slate-400 transition-all"><RefreshCw size={14} /></button>
          </header>

          <div className="space-y-3">
            {isLoading ? (
              <div className="py-12 text-center text-xs text-slate-400 animate-pulse">과제 목록을 동기화 중입니다...</div>
            ) : homeworks.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-400 border border-dashed rounded italic">등록된 과제가 없습니다.</div>
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
                        <button aria-label="Edit homework" onClick={() => handleEdit(hw)} className="p-2 rounded bg-slate-50 dark:bg-slate-900 text-slate-400 hover:text-accent transition-all hover:bg-white border border-transparent hover:border-slate-100"><Plus size={14} /></button>
                        <button aria-label="Delete homework" onClick={() => void handleDelete(hw.num)} className="p-2 rounded bg-slate-50 dark:bg-slate-900 text-slate-400 hover:text-rose-500 transition-all hover:bg-white border border-transparent hover:border-slate-100"><Trash2 size={14} /></button>
                      </div>
                    </div>
                    
                    <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex flex-wrap items-center gap-2">
                      <button
                        onClick={() => void handleDownload(hw.num, 'grades')}
                        disabled={downloadingKey === `${hw.num}:grades`}
                        className="text-[10px] font-bold px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-accent hover:text-white transition-colors flex items-center gap-1.5 disabled:opacity-50"
                      >
                        <FileSpreadsheet size={11} />
                        성적 CSV
                      </button>
                      <button
                        onClick={() => void handleDownload(hw.num, 'archive')}
                        disabled={downloadingKey === `${hw.num}:archive`}
                        className="text-[10px] font-bold px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-accent hover:text-white transition-colors flex items-center gap-1.5 disabled:opacity-50"
                      >
                        <FileArchive size={11} />
                        제출물 ZIP
                      </button>
                      <form
                        onSubmit={(event) => {
                          event.preventDefault();
                          const input = event.currentTarget.elements.namedItem('revisionId') as HTMLInputElement;
                          void handleAttachProblem(hw.num, input.value);
                          input.value = '';
                        }}
                        className="flex items-center gap-1.5 ml-auto"
                        title="문제 뱅크의 게시된 revision 번호를 과제에 연결합니다."
                      >
                        <input
                          type="text"
                          name="revisionId"
                          inputMode="numeric"
                          required
                          placeholder="Revision"
                          className="text-[10px] px-2 py-1 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 outline-none focus:border-accent w-20"
                        />
                        <button
                          type="submit"
                          className="text-[10px] font-bold px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-accent hover:text-white transition-colors flex items-center gap-1.5"
                        >
                          <Link2 size={11} />
                          문제 연결
                        </button>
                      </form>
                    </div>

                    <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between gap-3">
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

      <section className="card-simple">
        <header className="mb-6">
          <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-2">
            <Upload size={14} />
            기존 과제 자료로 가져오기
          </h2>
          <p className="text-slate-500 text-sm font-medium leading-relaxed">
            문제 설명 파일과 입력/출력 ZIP을 올리면 테스트케이스까지 한 번에 등록됩니다. 두 ZIP의
            파일 이름이 서로 짝이 맞아야 합니다.
          </p>
        </header>

        <form onSubmit={(event) => void handleImport(event)} className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label htmlFor="import-title" className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">과제 제목</label>
              <input id="import-title" name="title" required className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent" placeholder="예: 2주차 배열 실습" />
            </div>
            <div>
              <label htmlFor="import-code-name" className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">코드 식별자</label>
              <input id="import-code-name" name="codeName" required className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent font-mono" placeholder="array" />
            </div>
            <div>
              <label htmlFor="import-lint-week" className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Lint Week</label>
              <input id="import-lint-week" name="lint_week" className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none" placeholder="예: 2" />
            </div>
          </div>

          <div>
            <label htmlFor="import-intro" className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">과제 설명</label>
            <textarea id="import-intro" name="intro" rows={3} required className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent resize-none" placeholder="과제 설명을 입력하세요..." />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="import-starttime" className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 flex items-center gap-1.5"><Clock size={10} /> 제출 시작 일시</label>
              <input id="import-starttime" name="starttime" className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none" placeholder="YYYY-MM-DD HH:MM:SS" />
            </div>
            <div>
              <label htmlFor="import-deadline" className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 flex items-center gap-1.5"><Clock size={10} /> 마감 일시</label>
              <input id="import-deadline" name="deadline" className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none" placeholder="YYYY-MM-DD HH:MM:SS" />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { name: 'problem_file', label: '문제 설명 파일', accept: '' },
              { name: 'input_zip', label: '입력 ZIP', accept: '.zip' },
              { name: 'output_zip', label: '출력 ZIP', accept: '.zip' },
            ].map((field) => (
              <div key={field.name}>
                <label htmlFor={`import-${field.name}`} className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">{field.label}</label>
                <input
                  id={`import-${field.name}`}
                  name={field.name}
                  type="file"
                  accept={field.accept || undefined}
                  required
                  className="block w-full text-[11px] rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none file:mr-3 file:rounded file:border-0 file:bg-slate-200 dark:file:bg-slate-800 file:px-2 file:py-1 file:text-[10px] file:font-bold"
                />
              </div>
            ))}
          </div>

          <div className="p-4 rounded bg-slate-50 dark:bg-slate-900/50 border border-slate-100 dark:border-slate-800">
            <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3">Allowed Languages</h3>
            <div className="flex flex-wrap gap-4">
              {LANGUAGE_OPTIONS.map((language) => (
                <label key={language} className="flex items-center gap-2 text-xs font-medium cursor-pointer group">
                  <input type="checkbox" name={`language_${language}`} defaultChecked className="rounded border-slate-300 text-accent focus:ring-accent" />
                  <span className="text-slate-600 dark:text-slate-400 group-hover:text-slate-900 transition-colors">{language.toUpperCase()}</span>
                </label>
              ))}
              <label className="flex items-center gap-2 text-xs font-medium cursor-pointer group">
                <input type="checkbox" name="isLint" className="rounded border-slate-300 text-accent focus:ring-accent" />
                <span className="text-slate-600 dark:text-slate-400 group-hover:text-slate-900 transition-colors">Lint Score</span>
              </label>
            </div>
          </div>

          <button type="submit" disabled={isImporting} className="btn-flat h-11 px-6 flex items-center justify-center gap-2 shadow-sm disabled:opacity-50">
            {isImporting ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Upload size={16} />}
            <span>과제 가져오기</span>
          </button>
        </form>
      </section>
    </div>
  );
}
