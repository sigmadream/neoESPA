'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Megaphone, Pin, Calendar, User, ChevronRight } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import { getNotices, type NoticeApi } from '@/lib/api';

export default function NoticeListPage() {
  const { token } = useAuth();
  const [notices, setNotices] = useState<NoticeApi[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    let isMounted = true;
    async function loadNotices() {
      setIsLoading(true);
      try {
        const response = await getNotices(token);
        if (isMounted) setNotices(response);
      } catch (error) {
        if (isMounted) setErrorMessage(error instanceof Error ? error.message : 'Failed to load notices.');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    void loadNotices();
    return () => { isMounted = false; };
  }, [token]);

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-10">
      <header>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
          <Megaphone className="text-accent" size={24} />
          Course Notices
        </h1>
        <p className="text-slate-500 text-sm font-medium">Important announcements and updates for the course.</p>
      </header>

      {isLoading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-24 w-full bg-slate-50 dark:bg-slate-900 animate-pulse rounded-md border border-slate-100 dark:border-slate-800" />
          ))}
        </div>
      ) : errorMessage ? (
        <div className="card-simple border-rose-100 bg-rose-50 dark:bg-rose-950/20 text-rose-600 dark:text-rose-400 text-sm font-medium">
          {errorMessage}
        </div>
      ) : notices.length === 0 ? (
        <div className="card-simple text-center py-16 border-dashed">
          <p className="text-slate-400 text-sm italic">No notices have been published yet.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {notices.map((notice) => (
            <Link 
              key={notice.num} 
              href={`/notice/${notice.num}`}
              className={`block card-simple hover:border-accent transition-all group relative ${notice.is_pinned ? 'border-amber-200 dark:border-amber-900/50 bg-amber-50/10' : ''}`}
            >
              <div className="flex items-center justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2">
                    {notice.is_pinned && (
                      <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400">
                        <Pin size={10} /> Pinned
                      </span>
                    )}
                    <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 group-hover:text-accent transition-colors truncate">
                      {notice.title}
                    </h2>
                  </div>
                  <div className="flex items-center gap-4 text-[11px] text-slate-400 font-medium">
                    <span className="flex items-center gap-1.5">
                      <User size={12} /> {notice.author}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Calendar size={12} /> {new Date(notice.date || '').toLocaleDateString()}
                    </span>
                  </div>
                </div>
                <ChevronRight size={18} className="text-slate-300 group-hover:text-accent group-hover:translate-x-0.5 transition-all shrink-0" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
