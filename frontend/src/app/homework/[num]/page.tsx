'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Calendar, Clock, FileText, Settings, ShieldCheck, ChevronLeft, Download } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import HomeworkSubmissionPanel from '@/components/homework/HomeworkSubmissionPanel';
import { getHomework, type HomeworkApi } from '@/lib/api';

const STATUS_META: Record<
  HomeworkApi['schedule_status'],
  { label: string; className: string }
> = {
  upcoming: {
    label: 'Starts soon',
    className: 'text-slate-400 bg-slate-50 dark:bg-slate-900',
  },
  open: {
    label: 'Open',
    className: 'text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-900/20',
  },
  closing_soon: {
    label: 'Closing soon',
    className: 'text-amber-600 bg-amber-50 dark:text-amber-400 dark:bg-amber-900/20',
  },
  closed: {
    label: 'Closed',
    className: 'text-rose-600 bg-rose-50 dark:text-rose-400 dark:bg-rose-900/20',
  },
};

export default function HomeworkDetailPage() {
  const { token } = useAuth();
  const params = useParams();
  const numParam = params.num;
  const homeworkNum = Array.isArray(numParam) ? Number(numParam[0]) : Number(numParam);
  const [homework, setHomework] = useState<HomeworkApi | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    let isMounted = true;
    async function loadHomework() {
      if (!Number.isFinite(homeworkNum)) {
        setErrorMessage('Invalid assignment number.');
        setIsLoading(false);
        return;
      }
      setIsLoading(true);
      try {
        const response = await getHomework(homeworkNum, token);
        if (isMounted) setHomework(response);
      } catch (error) {
        if (isMounted) setErrorMessage(error instanceof Error ? error.message : 'Failed to load assignment.');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    void loadHomework();
    return () => { isMounted = false; };
  }, [homeworkNum, token]);

  if (isLoading) return (
    <div className="max-w-4xl mx-auto py-12 animate-pulse">
      <div className="h-8 w-48 bg-slate-100 dark:bg-slate-800 rounded mb-8" />
      <div className="h-64 bg-slate-50 dark:bg-slate-900 rounded-lg" />
    </div>
  );

  if (errorMessage || !homework) return (
    <div className="max-w-4xl mx-auto py-12 text-center">
      <div className="card-simple border-rose-100 bg-rose-50 dark:bg-rose-950/20">
        <p className="text-rose-600 dark:text-rose-400 font-medium">{errorMessage || 'Assignment not found.'}</p>
        <Link href="/homework" className="mt-4 inline-block text-sm font-medium text-accent hover:underline">&larr; Back to list</Link>
      </div>
    </div>
  );

  const policyItems = [
    homework.isLint ? 'Lint enabled' : null,
    homework.vitalSpace ? 'Whitespace-sensitive' : null,
    homework.disorderedOutput ? 'Order-insensitive' : null,
  ].filter((item): item is string => Boolean(item));

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <header className="mb-10">
        <Link href="/homework" className="inline-flex items-center text-sm text-slate-500 hover:text-accent mb-6 transition-colors">
          <ChevronLeft size={16} className="mr-1" />
          Back to Assignments
        </Link>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="text-sm font-mono font-bold text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
                #{homework.num}
              </span>
              <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider ${STATUS_META[homework.schedule_status].className}`}>
                {STATUS_META[homework.schedule_status].label}
              </span>
            </div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-white leading-tight">
              {homework.title}
            </h1>
          </div>
          <div className="flex items-center gap-3">
            {homework.filename && (
              <button className="btn-outline flex items-center gap-2 text-sm">
                <Download size={16} />
                <span>Download Specs</span>
              </button>
            )}
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <section className="card-simple">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4 flex items-center gap-2">
              <FileText size={16} />
              Assignment Description
            </h2>
            <div className="prose dark:prose-invert max-w-none text-slate-600 dark:text-slate-300 leading-relaxed whitespace-pre-line">
              {homework.intro}
            </div>
          </section>

          <section id="submission-panel">
            <HomeworkSubmissionPanel homework={homework} />
          </section>
        </div>

        <aside className="space-y-6">
          <section className="card-simple bg-slate-50/50 dark:bg-slate-900/20">
            <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-5">Details</h2>
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <Calendar size={16} className="text-slate-400 mt-0.5" />
                <div>
                  <p className="text-xs text-slate-400 font-medium mb-0.5">Start Time</p>
                  <p className="text-sm font-semibold">{homework.starttime ? new Date(homework.starttime).toLocaleString() : 'Immediately'}</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <Clock size={16} className="text-slate-400 mt-0.5" />
                <div>
                  <p className="text-xs text-slate-400 font-medium mb-0.5">Deadline</p>
                  <p className="text-sm font-semibold text-rose-600 dark:text-rose-400">{homework.deadline ? new Date(homework.deadline).toLocaleString() : 'No deadline'}</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <ShieldCheck size={16} className="text-slate-400 mt-0.5" />
                <div>
                  <p className="text-xs text-slate-400 font-medium mb-0.5">Submissions</p>
                  <p className="text-sm font-semibold">{homework.sbnum} attempts max</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <Settings size={16} className="text-slate-400 mt-0.5" />
                <div>
                  <p className="text-xs text-slate-400 font-medium mb-0.5">Constraints</p>
                  <p className="text-sm font-semibold">{homework.sec}s limit, {homework.ratedatanum} cases</p>
                </div>
              </div>
            </div>
          </section>

          {policyItems.length > 0 && (
            <section className="card-simple border-slate-100 dark:border-slate-800">
              <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">Policies</h2>
              <ul className="space-y-2">
                {policyItems.map((item) => (
                  <li key={item} className="text-sm flex items-center gap-2 text-slate-600 dark:text-slate-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                    {item}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}
