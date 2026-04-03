'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { LayoutDashboard, CheckCircle2, Clock, BarChart3, AlertCircle, ChevronRight, ArrowUpRight } from 'lucide-react';

import AuthGate from '@/components/AuthGate';
import { useAuth } from '@/components/AuthProvider';
import {
  getStudentDashboard,
  type StudentDashboardApi,
  type StudentDashboardHomeworkItemApi,
} from '@/lib/api';

const STATUS_META: Record<
  StudentDashboardHomeworkItemApi['schedule_status'],
  { label: string; className: string }
> = {
  upcoming: {
    label: 'Starts Soon',
    className: 'text-slate-400 bg-slate-50 dark:bg-slate-900',
  },
  open: {
    label: 'Open',
    className: 'text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-900/20',
  },
  closing_soon: {
    label: 'Closing Soon',
    className: 'text-amber-600 bg-amber-50 dark:text-amber-400 dark:bg-amber-900/20',
  },
  closed: {
    label: 'Closed',
    className: 'text-rose-600 bg-rose-50 dark:text-rose-400 dark:bg-rose-900/20',
  },
};

function formatDate(value: string | null) {
  if (!value) return '-';
  const normalized = value.includes(' ') ? value.replace(' ', 'T') : value;
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString() + ' ' + parsed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatRemainingTime(seconds: number | null, status: string) {
  if (seconds === null || status === 'closed' || seconds <= 0) return 'Expired';
  const days = Math.floor(seconds / 86_400);
  const hours = Math.floor((seconds % 86_400) / 3_600);
  if (days > 0) return `${days}d ${hours}h left`;
  const minutes = Math.floor((seconds % 3_600) / 60);
  return `${hours}h ${minutes}m left`;
}

function DashboardContent() {
  const { token, user } = useAuth();
  const [dashboard, setDashboard] = useState<StudentDashboardApi | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (!token) return;
    let isMounted = true;
    async function loadDashboard() {
      setIsLoading(true);
      try {
        const response = await getStudentDashboard(token);
        if (isMounted) setDashboard(response);
      } catch (error) {
        if (isMounted) setErrorMessage(error instanceof Error ? error.message : 'Failed to load dashboard.');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    void loadDashboard();
    return () => { isMounted = false; };
  }, [token]);

  if (isLoading) return <div className="py-20 text-center animate-pulse text-slate-400 font-medium">Loading your dashboard...</div>;
  if (errorMessage) return <div className="max-w-5xl mx-auto py-10"><div className="card-simple border-rose-100 bg-rose-50 dark:bg-rose-950/20 text-rose-600 dark:text-rose-400 text-sm font-medium">{errorMessage}</div></div>;
  if (!dashboard) return null;

  const nextDeadline = dashboard.homework_items
    .filter((item) => item.schedule_status !== 'closed' && item.remaining_seconds !== null)
    .sort((left, right) => (left.remaining_seconds ?? 0) - (right.remaining_seconds ?? 0))[0] ?? null;

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-10">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
            <LayoutDashboard className="text-accent" size={24} />
            Student Dashboard
          </h1>
          <p className="text-slate-500 text-sm font-medium">Welcome back, <span className="text-slate-900 dark:text-slate-200">{user?.name}</span>. Here is your current progress.</p>
        </div>
        {nextDeadline && (
          <div className="inline-flex items-center gap-3 px-4 py-2 bg-amber-50 dark:bg-amber-950/20 border border-amber-100 dark:border-amber-900/30 rounded-lg">
            <Clock className="text-amber-600 dark:text-amber-400" size={16} />
            <div className="text-xs">
              <p className="text-amber-800 dark:text-amber-300 font-bold uppercase tracking-tighter">Next Deadline</p>
              <p className="text-amber-600 dark:text-amber-400 font-medium">{nextDeadline.title} · {formatRemainingTime(nextDeadline.remaining_seconds, nextDeadline.schedule_status)}</p>
            </div>
          </div>
        )}
      </header>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Assigned', value: dashboard.overview.total_homeworks, icon: BarChart3 },
          { label: 'Submitted', value: dashboard.overview.submitted_homeworks, icon: CheckCircle2 },
          { label: 'Pending', value: dashboard.overview.pending_homeworks, icon: Clock },
          { label: 'Avg Score', value: dashboard.overview.average_latest_score?.toFixed(1) ?? '-', icon: ArrowUpRight },
        ].map((stat) => (
          <div key={stat.label} className="card-simple flex flex-col justify-between py-4 px-5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 flex items-center justify-between">
              {stat.label}
              <stat.icon size={12} className="opacity-50" />
            </span>
            <span className="text-2xl font-bold text-slate-900 dark:text-white mt-2">{stat.value}</span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <section className="card-simple">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400">Current Homeworks</h2>
              <Link href="/homework" className="text-xs font-medium text-accent hover:underline">View All &rarr;</Link>
            </div>
            <div className="divide-y divide-slate-50 dark:divide-slate-900">
              {dashboard.homework_items.length === 0 ? (
                <p className="py-10 text-center text-sm text-slate-400">No active assignments found.</p>
              ) : (
                dashboard.homework_items.map((item) => (
                  <div key={item.homework_num} className="py-4 first:pt-0 last:pb-0 flex items-center justify-between group">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Link href={`/homework/${item.homework_num}`} className="text-sm font-bold text-slate-900 dark:text-white hover:text-accent transition-colors truncate">
                          #{item.homework_num} {item.title}
                        </Link>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-tighter ${STATUS_META[item.schedule_status].className}`}>
                          {STATUS_META[item.schedule_status].label}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 font-medium">
                        Deadline: {formatDate(item.deadline)} · {item.submission_count} attempts
                      </p>
                    </div>
                    <div className="flex items-center gap-4 ml-4">
                      <div className="text-right hidden sm:block">
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">Latest Score</p>
                        <p className={`text-sm font-bold ${item.latest_score !== null ? 'text-slate-900 dark:text-slate-100' : 'text-slate-300'}`}>
                          {item.latest_score !== null ? item.latest_score.toFixed(1) : (item.latest_submission_status ? 'Grading' : 'None')}
                        </p>
                      </div>
                      <Link href={`/homework/${item.homework_num}#submission-panel`} className="p-2 rounded-md hover:bg-slate-50 dark:hover:bg-slate-900 text-slate-300 hover:text-accent transition-all">
                        <ChevronRight size={20} />
                      </Link>
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>

        <aside className="space-y-8">
          <section className="card-simple">
            <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-5">Recent Submissions</h2>
            <div className="space-y-4">
              {dashboard.recent_submissions.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No recent history.</p>
              ) : (
                dashboard.recent_submissions.map((sub) => (
                  <Link key={sub.id} href={`/homework/result?id=${sub.id}`} className="block p-3 rounded border border-transparent hover:border-slate-100 dark:hover:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900/50 transition-all">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-xs font-bold truncate">#{sub.homework_num} {sub.homework_title}</p>
                      <span className="text-xs font-mono font-bold text-accent">{sub.total_score.toFixed(1)}</span>
                    </div>
                    <p className="text-[10px] text-slate-400 font-medium">{sub.status} · {new Date(sub.submitted_at).toLocaleDateString()}</p>
                  </Link>
                ))
              )}
            </div>
          </section>

          <section className="card-simple border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-900/10">
            <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">Attention Required</h2>
            <div className="space-y-3">
              {[
                { label: 'Closing Soon', value: dashboard.overview.closing_soon_homeworks, color: 'text-amber-600' },
                { label: 'Missing (Past)', value: dashboard.overview.missing_homeworks, color: 'text-rose-600' },
                { label: 'Graded', value: dashboard.overview.graded_homeworks, color: 'text-blue-600' },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between text-xs font-medium">
                  <span className="text-slate-500">{item.label}</span>
                  <span className={`font-bold ${item.color}`}>{item.value}</span>
                </div>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <AuthGate>
      <DashboardContent />
    </AuthGate>
  );
}
