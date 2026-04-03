'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Calendar, ChevronRight, Hash } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import { getHomeworks, type HomeworkApi } from '@/lib/api';

const STATUS_META: Record<
  HomeworkApi['schedule_status'],
  { label: string; className: string }
> = {
  upcoming: {
    label: '시작 전',
    className: 'text-slate-400 bg-slate-50 dark:bg-slate-900',
  },
  open: {
    label: '진행 중',
    className: 'text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-900/20',
  },
  closing_soon: {
    label: '마감 임박',
    className: 'text-amber-600 bg-amber-50 dark:text-amber-400 dark:bg-amber-900/20',
  },
  closed: {
    label: '마감 완료',
    className: 'text-rose-600 bg-rose-50 dark:text-rose-400 dark:bg-rose-900/20',
  },
};

export default function HomeworkListPage() {
  const { token } = useAuth();
  const [homeworks, setHomeworks] = useState<HomeworkApi[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    let isMounted = true;

    async function loadHomeworks() {
      setIsLoading(true);
      setErrorMessage('');

      try {
        // 백엔드 최적화에 맞춰 limit 적용
        const response = await getHomeworks(token, { limit: 50 });
        if (isMounted) {
          setHomeworks(response);
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(
            error instanceof Error ? error.message : 'Failed to load homework list.',
          );
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadHomeworks();

    return () => { isMounted = false; };
  }, [token]);

  return (
    <div className="max-w-5xl mx-auto py-8">
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-10 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-1">Homework Assignments</h1>
          <p className="text-slate-500 text-sm">Practice your coding skills with the following assignments.</p>
        </div>
        {!isLoading && (
          <div className="text-xs font-medium px-3 py-1 bg-slate-100 dark:bg-slate-800 text-slate-500 rounded-full">
            {homeworks.length} assignments found
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-24 w-full bg-slate-50 dark:bg-slate-900 animate-pulse rounded-lg border border-slate-100 dark:border-slate-800" />
          ))}
        </div>
      ) : errorMessage ? (
        <div className="card-simple border-rose-100 bg-rose-50 dark:bg-rose-950/20 dark:border-rose-900/30 text-center">
          <p className="text-rose-600 dark:text-rose-400 text-sm font-medium">{errorMessage}</p>
        </div>
      ) : homeworks.length === 0 ? (
        <div className="card-simple text-center py-16 border-dashed">
          <p className="text-slate-400 text-sm">No assignments available at the moment.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {homeworks.map((hw) => (
            <Link 
              key={hw.num} 
              href={`/homework/${hw.num}`}
              className="block card-simple hover:border-accent transition-all group relative overflow-hidden"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-5">
                  <div className="flex flex-col items-center justify-center w-10 h-10 rounded-md bg-slate-50 dark:bg-slate-800 text-slate-400 border border-slate-100 dark:border-slate-700">
                    <Hash size={14} className="mb-0.5" />
                    <span className="text-xs font-bold leading-none">{hw.num}</span>
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 group-hover:text-accent transition-colors">
                      {hw.title}
                    </h2>
                    <div className="flex items-center gap-4 mt-1 text-xs text-slate-500">
                      <span className="flex items-center gap-1.5 font-medium">
                        <Calendar size={12} />
                        {hw.deadline ? new Date(hw.deadline).toLocaleDateString() : 'No deadline'}
                      </span>
                      <span className="text-slate-300 dark:text-slate-700">|</span>
                      <span className="font-mono">{hw.codeName}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span className={`text-[10px] px-2.5 py-1 rounded-full font-bold uppercase tracking-wider ${STATUS_META[hw.schedule_status].className}`}>
                    {STATUS_META[hw.schedule_status].label}
                  </span>
                  <ChevronRight size={18} className="text-slate-300 group-hover:text-accent group-hover:translate-x-0.5 transition-all" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
