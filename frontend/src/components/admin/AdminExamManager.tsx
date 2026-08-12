'use client';

import { useCallback, useEffect, useState } from 'react';
import { CalendarClock, Plus, RefreshCw, ScrollText } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import { parseServerDate } from '@/lib/datetime';
import { createAdminExam, getExams, type ExamApi } from '@/lib/api';

const LANGUAGE_OPTIONS = ['c', 'cpp', 'python', 'java'] as const;

function scheduleTone(status: string) {
  if (status === 'open' || status === 'closing_soon') {
    return 'text-emerald-600 dark:text-emerald-400';
  }
  if (status === 'upcoming') return 'text-amber-600 dark:text-amber-400';
  return 'text-slate-500 dark:text-slate-400';
}

function formatSchedule(value: string | null) {
  const parsed = parseServerDate(value);
  return parsed ? parsed.toLocaleString() : '-';
}

export default function AdminExamManager() {
  const { token } = useAuth();
  const [exams, setExams] = useState<ExamApi[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isWorking, setIsWorking] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const loadExams = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      setExams(await getExams(token));
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '시험 목록을 불러오지 못했습니다.',
      );
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadExams();
  }, [loadExams]);

  const handleCreate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token) return;
    const formElement = event.currentTarget;
    const data = new FormData(formElement);
    setIsWorking(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      const exam = await createAdminExam(
        {
          title: String(data.get('title') ?? ''),
          intro: String(data.get('intro') ?? ''),
          codeName: String(data.get('codeName') ?? ''),
          starttime: String(data.get('starttime') ?? '') || null,
          deadline: String(data.get('deadline') ?? '') || null,
          allowed_languages: LANGUAGE_OPTIONS.filter(
            (language) => data.get(`language_${language}`) === 'on',
          ),
        },
        token,
      );
      formElement.reset();
      setSuccessMessage(`시험 #${exam.id} "${exam.title}"을(를) 등록했습니다.`);
      await loadExams();
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '시험을 등록하지 못했습니다.',
      );
    } finally {
      setIsWorking(false);
    }
  };

  return (
    <div className="space-y-8">
      <section className="card-simple">
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-2">
              <ScrollText size={16} className="text-accent" />
              시험 관리
            </h2>
            <p className="text-slate-500 text-sm font-medium leading-relaxed">
              시험을 등록하고 응시 일정을 확인합니다. 학생은 시험 화면에서 응시합니다.
            </p>
          </div>
          <button
            onClick={() => void loadExams()}
            disabled={isWorking}
            className="btn-outline text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            새로고침
          </button>
        </header>

        {(errorMessage || successMessage) && (
          <div
            className={`p-3 rounded text-[11px] font-medium border mb-6 ${
              errorMessage
                ? 'bg-rose-50 border-rose-100 text-rose-600 dark:bg-rose-950/20'
                : 'bg-emerald-50 border-emerald-100 text-emerald-600 dark:bg-emerald-950/20'
            }`}
          >
            {errorMessage || successMessage}
          </div>
        )}

        {exams.length === 0 ? (
          <p className="text-xs text-slate-400 italic">등록된 시험이 없습니다.</p>
        ) : (
          <div className="divide-y divide-slate-50 dark:divide-slate-900">
            {exams.map((exam) => (
              <div
                key={exam.id}
                className="py-4 first:pt-0 last:pb-0 grid grid-cols-1 md:grid-cols-4 gap-4 items-center"
              >
                <div className="md:col-span-2 min-w-0">
                  <p className="text-sm font-bold text-slate-900 dark:text-white truncate">
                    #{exam.id} {exam.title}
                  </p>
                  <p className="text-[10px] text-slate-400 font-mono">
                    {exam.codeName} · {exam.allowed_languages.join(', ') || '언어 미지정'}
                  </p>
                </div>
                <div className="flex flex-col">
                  <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter flex items-center gap-1">
                    <CalendarClock size={10} />
                    응시 기간
                  </span>
                  <span className="text-[11px] font-medium text-slate-600 dark:text-slate-400">
                    {formatSchedule(exam.starttime)} ~ {formatSchedule(exam.deadline)}
                  </span>
                </div>
                <div className="flex flex-col md:items-end">
                  <span className={`text-[11px] font-black uppercase ${scheduleTone(exam.schedule_status)}`}>
                    {exam.schedule_status}
                  </span>
                  <span className="text-[10px] text-slate-400 font-medium">
                    출제자 {exam.created_by}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="card-simple">
        <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-6">
          <Plus size={16} />새 시험 등록
        </h2>
        <form onSubmit={(event) => void handleCreate(event)} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <label className="flex flex-col gap-1.5 sm:col-span-2">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">시험 제목</span>
              <input name="title" required placeholder="중간고사 실기" className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent" />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">코드 식별자</span>
              <input name="codeName" required placeholder="midterm" className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent font-mono" />
            </label>
          </div>

          <label className="flex flex-col gap-1.5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">시험 안내</span>
            <textarea name="intro" required rows={3} placeholder="응시 방법과 유의사항을 입력하세요." className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent resize-none" />
          </label>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">응시 시작</span>
              <input name="starttime" placeholder="YYYY-MM-DD HH:MM:SS" className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none" />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">응시 마감</span>
              <input name="deadline" placeholder="YYYY-MM-DD HH:MM:SS" className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none" />
            </label>
          </div>

          <div className="p-4 rounded bg-slate-50 dark:bg-slate-900/50 border border-slate-100 dark:border-slate-800">
            <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3">허용 언어</h3>
            <div className="flex flex-wrap gap-4">
              {LANGUAGE_OPTIONS.map((language) => (
                <label key={language} className="flex items-center gap-2 text-xs font-medium cursor-pointer">
                  <input type="checkbox" name={`language_${language}`} defaultChecked className="rounded border-slate-300 text-accent focus:ring-accent" />
                  <span className="text-slate-600 dark:text-slate-400">{language.toUpperCase()}</span>
                </label>
              ))}
            </div>
          </div>

          <button type="submit" disabled={isWorking} className="btn-flat h-10 px-6 text-xs flex items-center gap-2 disabled:opacity-50">
            <Plus size={14} />시험 등록
          </button>
        </form>
      </section>
    </div>
  );
}
