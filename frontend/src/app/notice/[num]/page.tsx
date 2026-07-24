'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { User, Calendar, Pin, ChevronLeft, LayoutList } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import MarkdownContent from '@/components/MarkdownContent';
import { getNotice, type NoticeApi } from '@/lib/api';

export default function NoticeDetailPage() {
  const { token } = useAuth();
  const params = useParams();
  const numParam = params.num;
  const noticeNum = Array.isArray(numParam) ? Number(numParam[0]) : Number(numParam);
  const [notice, setNotice] = useState<NoticeApi | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    let isMounted = true;
    async function loadNotice() {
      if (!Number.isFinite(noticeNum)) {
        setErrorMessage('Invalid notice number.');
        setIsLoading(false);
        return;
      }
      setIsLoading(true);
      try {
        const response = await getNotice(noticeNum, token);
        if (isMounted) setNotice(response);
      } catch (error) {
        if (isMounted) setErrorMessage(error instanceof Error ? error.message : 'Failed to load notice.');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    void loadNotice();
    return () => { isMounted = false; };
  }, [noticeNum, token]);

  if (isLoading) return (
    <div className="max-w-4xl mx-auto py-12 animate-pulse">
      <div className="h-4 w-32 bg-slate-100 dark:bg-slate-800 rounded mb-8" />
      <div className="h-10 w-2/3 bg-slate-100 dark:bg-slate-800 rounded mb-4" />
      <div className="h-4 w-1/3 bg-slate-100 dark:bg-slate-800 rounded mb-12" />
      <div className="space-y-3">
        <div className="h-4 w-full bg-slate-50 dark:bg-slate-900 rounded" />
        <div className="h-4 w-full bg-slate-50 dark:bg-slate-900 rounded" />
        <div className="h-4 w-2/3 bg-slate-50 dark:bg-slate-900 rounded" />
      </div>
    </div>
  );

  if (errorMessage || !notice) return (
    <div className="max-w-4xl mx-auto py-12 text-center">
      <div className="card-simple border-rose-100 bg-rose-50 dark:bg-rose-950/20">
        <p className="text-rose-600 dark:text-rose-400 font-medium">{errorMessage || 'Notice not found.'}</p>
        <Link href="/notice" className="mt-4 inline-block text-sm font-medium text-accent hover:underline">&larr; Back to list</Link>
      </div>
    </div>
  );

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <header className="mb-10">
        <Link href="/notice" className="inline-flex items-center text-sm text-slate-500 hover:text-accent mb-6 transition-colors group">
          <ChevronLeft size={16} className="mr-1 group-hover:-translate-x-0.5 transition-transform" />
          Back to Notices
        </Link>
        
        <div className="flex items-center gap-3 mb-3">
          {notice.is_pinned && (
            <span className="flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400">
              <Pin size={10} /> Pinned
            </span>
          )}
          <span className="text-[10px] font-mono font-bold text-slate-400 bg-slate-50 dark:bg-slate-900 px-2 py-0.5 rounded">
            NOTICE #{notice.num}
          </span>
        </div>
        
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white leading-tight mb-4">
          {notice.title}
        </h1>
        
        <div className="flex items-center gap-6 text-xs text-slate-400 font-medium border-b border-slate-100 dark:border-slate-800 pb-6">
          <span className="flex items-center gap-1.5">
            <User size={14} className="text-slate-300" /> 
            Posted by <span className="text-slate-600 dark:text-slate-300">{notice.author}</span>
          </span>
          <span className="flex items-center gap-1.5">
            <Calendar size={14} className="text-slate-300" /> 
            {new Date(notice.date || '').toLocaleString()}
          </span>
        </div>
      </header>

      <article className="mb-16">
        <MarkdownContent content={notice.content} />
      </article>

      <footer className="pt-8 border-t border-slate-100 dark:border-slate-800">
        <Link href="/notice" className="btn-outline inline-flex items-center gap-2 text-sm bg-white dark:bg-transparent">
          <LayoutList size={16} />
          View All Notices
        </Link>
      </footer>
    </div>
  );
}
