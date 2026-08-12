'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Calendar, ChevronRight, Hash, ShieldAlert } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import { getExams, type ExamApi } from '@/lib/api';
import { parseServerDate } from '@/lib/datetime';

const STATUS_META: Record<
  ExamApi['schedule_status'],
  { label: string; className: string }
> = {
  upcoming: {
    label: '대기 중',
    className: 'text-slate-400 bg-slate-50 dark:bg-slate-900',
  },
  open: {
    label: '시험 진행 중',
    className: 'text-emerald-600 bg-emerald-50 dark:text-emerald-400 dark:bg-emerald-900/20',
  },
  closing_soon: {
    label: '종료 임박',
    className: 'text-amber-600 bg-amber-50 dark:text-amber-400 dark:bg-amber-900/20',
  },
  closed: {
    label: '시험 종료',
    className: 'text-rose-600 bg-rose-50 dark:text-rose-400 dark:bg-rose-900/20',
  },
};

export default function ExamListPage() {
  const { token } = useAuth();
  const [exams, setExams] = useState<ExamApi[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    let isMounted = true;

    async function loadExams() {
      setIsLoading(true);
      setErrorMessage('');

      try {
        const response = await getExams(token);
        if (isMounted) {
          setExams(response);
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(
            error instanceof Error ? error.message : 'Failed to load exam list.',
          );
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadExams();

    return () => {
      isMounted = false;
    };
  }, [token]);

  return (
    <div className="max-w-5xl mx-auto py-8">
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-10 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-1">
            Exams & Assessments
          </h1>
          <p className="text-slate-500 text-sm">
            Take timed coding examinations under monitored test conditions.
          </p>
        </div>
        {!isLoading && (
          <div className="text-xs font-medium px-3 py-1 bg-slate-100 dark:bg-slate-800 text-slate-500 rounded-full">
            {exams.length} exams available
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="h-24 w-full bg-slate-50 dark:bg-slate-900 animate-pulse rounded-lg border border-slate-100 dark:border-slate-800"
            />
          ))}
        </div>
      ) : errorMessage ? (
        <div className="card-simple border-rose-100 bg-rose-50 dark:bg-rose-950/20 dark:border-rose-900/30 text-center">
          <p className="text-rose-600 dark:text-rose-400 text-sm font-medium">{errorMessage}</p>
        </div>
      ) : exams.length === 0 ? (
        <div className="card-simple text-center py-16 border-dashed">
          <ShieldAlert className="mx-auto mb-2 text-slate-400" size={32} />
          <p className="text-slate-400 text-sm">No scheduled exams at the moment.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {exams.map((exam) => (
            <Link
              key={exam.id}
              href={`/exam/${exam.id}`}
              className="block card-simple hover:border-accent transition-all group relative overflow-hidden"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-5">
                  <div className="flex flex-col items-center justify-center w-10 h-10 rounded-md bg-slate-50 dark:bg-slate-800 text-slate-400 border border-slate-100 dark:border-slate-700">
                    <Hash size={14} className="mb-0.5" />
                    <span className="text-xs font-bold leading-none">{exam.id}</span>
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 group-hover:text-accent transition-colors">
                      {exam.title}
                    </h2>
                    <div className="flex items-center gap-4 mt-1 text-xs text-slate-500">
                      <span className="flex items-center gap-1.5 font-medium">
                        <Calendar size={12} />
                        {parseServerDate(exam.deadline)?.toLocaleDateString() ?? 'No deadline'}
                      </span>
                      <span className="text-slate-300 dark:text-slate-700">|</span>
                      <span className="font-mono">{exam.codeName}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span
                    className={`text-[10px] px-2.5 py-1 rounded-full font-bold uppercase tracking-wider ${STATUS_META[exam.schedule_status].className}`}
                  >
                    {STATUS_META[exam.schedule_status].label}
                  </span>
                  <ChevronRight
                    size={18}
                    className="text-slate-300 group-hover:text-accent group-hover:translate-x-0.5 transition-all"
                  />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
