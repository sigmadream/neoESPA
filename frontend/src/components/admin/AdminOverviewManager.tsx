'use client';

import { useEffect, useState } from 'react';
import { Users, BookOpen, Send, ListChecks, AlertTriangle, Activity } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import { getAdminDashboard, type AdminDashboardApi } from '@/lib/api';

export default function AdminOverviewManager() {
  const { token } = useAuth();
  const [dashboard, setDashboard] = useState<AdminDashboardApi | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (!token) return;
    let isMounted = true;
    async function loadDashboard() {
      setIsLoading(true);
      try {
        const response = await getAdminDashboard(token);
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

  if (isLoading) return <div className="py-20 text-center animate-pulse text-slate-400 font-medium">Loading system metrics...</div>;
  if (errorMessage) return <div className="card-simple border-rose-100 bg-rose-50 dark:bg-rose-950/20 text-rose-600 dark:text-rose-400 text-sm font-medium p-6">{errorMessage}</div>;
  if (!dashboard) return null;

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Active Students', value: dashboard.active_students, icon: Users },
          { label: 'Total Homeworks', value: dashboard.total_homeworks, icon: BookOpen },
          { label: 'Total Submissions', value: dashboard.total_submissions, icon: Send },
          { label: 'Queue Size', value: dashboard.queue.queue_size, icon: ListChecks },
        ].map((stat) => (
          <div key={stat.label} className="card-simple flex flex-col justify-between py-4 px-5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 flex items-center justify-between">
              {stat.label}
              <stat.icon size={12} className="opacity-50" />
            </span>
            <span className="text-2xl font-black text-slate-900 dark:text-white mt-2">{stat.value}</span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <section className="card-simple">
            <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-6">Homework Metrics</h2>
            <div className="divide-y divide-slate-50 dark:divide-slate-900">
              {dashboard.homework_metrics.map((m) => (
                <div key={m.homework_num} className="py-4 first:pt-0 last:pb-0 grid grid-cols-1 md:grid-cols-4 gap-4 items-center">
                  <div className="md:col-span-2 min-w-0">
                    <p className="text-sm font-bold text-slate-900 dark:text-white truncate">#{m.homework_num} {m.title}</p>
                    <p className="text-[11px] text-slate-500 font-medium">Submission Rate: {m.submission_rate.toFixed(1)}%</p>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter">Participation</span>
                    <span className="text-xs font-bold text-slate-700 dark:text-slate-300">{m.submitted_students} / {m.total_students}</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter">Failure / Pending</span>
                    <span className="text-xs font-bold text-rose-600 dark:text-rose-400">{m.failed_submission_count} / {m.pending_submission_count}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>

        <aside className="space-y-8">
          <section className="card-simple">
            <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-5 flex items-center gap-2">
              <AlertTriangle size={14} className="text-rose-500" />
              Failure Types
            </h2>
            <div className="space-y-2">
              {dashboard.failure_metrics.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No failures recorded.</p>
              ) : (
                dashboard.failure_metrics.map((m) => (
                  <div key={m.failure_type} className="flex items-center justify-between text-xs p-2.5 rounded bg-slate-50 dark:bg-slate-900/50 border border-slate-100 dark:border-slate-800">
                    <span className="text-slate-600 dark:text-slate-400 font-medium">{m.failure_type}</span>
                    <span className="font-bold text-slate-900 dark:text-white">{m.count}</span>
                  </div>
                ))
              )}
            </div>
          </section>

          <section className="card-simple">
            <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-5 flex items-center gap-2">
              <Activity size={14} className="text-accent" />
              System Events
            </h2>
            <div className="space-y-3">
              {dashboard.recent_events.slice(0, 5).map((e) => (
                <div key={e.id} className="text-[11px] leading-relaxed">
                  <p className="font-bold text-slate-700 dark:text-slate-300">{e.event_type}</p>
                  <p className="text-slate-500 dark:text-slate-500">{e.message}</p>
                  <p className="text-[9px] text-slate-400 mt-0.5">{new Date(e.created_at).toLocaleTimeString()}</p>
                </div>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
