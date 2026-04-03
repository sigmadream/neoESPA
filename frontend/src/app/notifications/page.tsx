'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Bell, CheckCheck, ExternalLink, Calendar } from 'lucide-react';

import AuthGate from '@/components/AuthGate';
import { useAuth } from '@/components/AuthProvider';
import {
  getNotifications,
  markNotificationsRead,
  type NotificationApi,
} from '@/lib/api';

function NotificationPageContent() {
  const { token } = useAuth();
  const [notifications, setNotifications] = useState<NotificationApi[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (!token) return;
    let isMounted = true;
    async function loadNotifications() {
      setIsLoading(true);
      try {
        const response = await getNotifications(token);
        if (isMounted) setNotifications(response);
      } catch (error) {
        if (isMounted) setErrorMessage(error instanceof Error ? error.message : 'Failed to load notifications.');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    void loadNotifications();
    return () => { isMounted = false; };
  }, [token]);

  async function handleMarkVisibleAsRead() {
    if (!token) return;
    const unreadIds = notifications.filter((n) => !n.is_read).map((n) => n.id);
    if (unreadIds.length === 0) return;
    try {
      const updated = await markNotificationsRead(unreadIds, token);
      const updatedIds = new Set(updated.map((n) => n.id));
      setNotifications((current) =>
        current.map((n) => updatedIds.has(n.id) ? { ...n, is_read: true } : n)
      );
    } catch { /* ignore */ }
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-10">
      <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
            <Bell className="text-accent" size={24} />
            Notifications
          </h1>
          <p className="text-slate-500 text-sm font-medium">Stay updated with course announcements and grading events.</p>
        </div>
        <button
          onClick={() => void handleMarkVisibleAsRead()}
          className="btn-outline inline-flex items-center gap-2 text-xs h-10 px-4 bg-white dark:bg-transparent"
        >
          <CheckCheck size={14} />
          Mark all as read
        </button>
      </header>

      <section className="space-y-4">
        {isLoading ? (
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-24 w-full bg-slate-50 dark:bg-slate-900 animate-pulse rounded-md border border-slate-100 dark:border-slate-800" />
            ))}
          </div>
        ) : errorMessage ? (
          <div className="card-simple border-rose-100 bg-rose-50 dark:bg-rose-950/20 text-rose-600 dark:text-rose-400 text-sm font-medium">{errorMessage}</div>
        ) : notifications.length === 0 ? (
          <div className="card-simple text-center py-16 border-dashed">
            <p className="text-slate-400 text-sm italic">No notifications yet.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {notifications.map((n) => (
              <div
                key={n.id}
                className={`card-simple group transition-all ${n.is_read ? 'opacity-70 grayscale-[0.5]' : 'border-l-4 border-l-accent'}`}
              >
                <div className="flex items-start justify-between gap-6">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">{n.kind}</span>
                      {!n.is_read && <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />}
                    </div>
                    <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 mb-1">{n.title}</h2>
                    <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed mb-3">{n.message}</p>
                    <div className="flex items-center gap-3 text-[11px] text-slate-400 font-medium">
                      <Calendar size={12} /> {new Date(n.created_at).toLocaleString()}
                    </div>
                  </div>
                  
                  {n.reference_id && (
                    <Link
                      href={n.reference_type === 'notice' ? `/notice/${n.reference_id}` : `/homework/result?id=${n.reference_id}`}
                      className="btn-outline text-[11px] h-9 px-3 flex items-center gap-1.5 whitespace-nowrap bg-white dark:bg-transparent shrink-0"
                    >
                      <ExternalLink size={12} />
                      View {n.reference_type === 'notice' ? 'Notice' : 'Result'}
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default function NotificationPage() {
  return (
    <AuthGate>
      <NotificationPageContent />
    </AuthGate>
  );
}
