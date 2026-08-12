'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { BookOpen, FileCode, Bell, User, Clock, CheckCircle2 } from 'lucide-react';
import { useAuth } from '@/components/AuthProvider';
import { useTranslation } from '@/i18n/LanguageContext';
import { getStudentDashboard, type StudentDashboardApi } from '@/lib/api';

export default function Home() {
  const { isAuthenticated, token, user } = useAuth();
  const { t } = useTranslation();
  const [recentSubmissions, setRecentSubmissions] = useState<StudentDashboardApi['recent_submissions']>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!token || !isAuthenticated) {
      setRecentSubmissions([]);
      return;
    }

    let isMounted = true;
    async function loadRecentActivity() {
      setIsLoading(true);
      try {
        const dashboard = await getStudentDashboard(token!);
        if (isMounted) {
          setRecentSubmissions(dashboard.recent_submissions);
        }
      } catch {
        if (isMounted) {
          setRecentSubmissions([]);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadRecentActivity();
    return () => {
      isMounted = false;
    };
  }, [token, isAuthenticated]);

  return (
    <div className="max-w-5xl mx-auto py-12 px-4">
      <header className="mb-12">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100 mb-2">
          대시보드
        </h1>
        <p className="text-slate-500 dark:text-slate-400">
          {user?.name ? `안녕하세요, ${user.name}님! ` : ''}{t.home.welcome}
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Link href="/homework" className="card-simple hover:border-accent transition-colors group">
          <div className="flex items-start space-x-4">
            <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg group-hover:bg-blue-100 transition-colors">
              <BookOpen className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold mb-1">{t.home.homeworksTitle}</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {t.home.homeworksDesc}
              </p>
            </div>
          </div>
        </Link>

        <Link href="/notice" className="card-simple hover:border-accent transition-colors group">
          <div className="flex items-start space-x-4">
            <div className="p-2 bg-amber-50 dark:bg-amber-900/20 rounded-lg group-hover:bg-amber-100 transition-colors">
              <Bell className="w-6 h-6 text-amber-600 dark:text-amber-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold mb-1">{t.home.noticesTitle}</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {t.home.noticesDesc}
              </p>
            </div>
          </div>
        </Link>

        <Link href="/profile" className="card-simple hover:border-accent transition-colors group">
          <div className="flex items-start space-x-4">
            <div className="p-2 bg-slate-100 dark:bg-slate-800 rounded-lg group-hover:bg-slate-200 transition-colors">
              <User className="w-6 h-6 text-slate-600 dark:text-slate-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold mb-1">{t.home.profileTitle}</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {t.home.profileDesc}
              </p>
            </div>
          </div>
        </Link>

        <Link href="/materials" className="card-simple hover:border-accent transition-colors group">
          <div className="flex items-start space-x-4">
            <div className="p-2 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg group-hover:bg-emerald-100 transition-colors">
              <FileCode className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold mb-1">{t.home.materialsTitle}</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {t.home.materialsDesc}
              </p>
            </div>
          </div>
        </Link>
      </div>

      <section className="mt-16 pt-12 border-t border-slate-100 dark:border-slate-800">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">{t.home.recentActivity}</h2>
          {isAuthenticated && (
            <Link href="/dashboard" className="text-xs font-medium text-accent hover:underline">
              {t.home.goToFullDashboard} &rarr;
            </Link>
          )}
        </div>

        {isAuthenticated ? (
          isLoading ? (
            <div className="py-8 text-center text-slate-400 text-sm animate-pulse">
              {t.common.loading}
            </div>
          ) : recentSubmissions.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {recentSubmissions.map((sub) => (
                <Link
                  key={sub.id}
                  href={`/homework/result?id=${sub.id}`}
                  className="card-simple hover:border-accent transition-all p-4 block"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                      <span className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate">
                        #{sub.homework_num} {sub.homework_title}
                      </span>
                    </div>
                    <span className="text-xs font-mono font-bold text-accent px-2 py-0.5 bg-blue-50 dark:bg-blue-900/20 rounded">
                      {sub.total_score.toFixed(1)} pts
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>{t.common.status}: {sub.status}</span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(sub.submitted_at).toLocaleDateString()}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-8 text-center border border-dashed border-slate-200 dark:border-slate-800">
              <p className="text-slate-500 dark:text-slate-400 text-sm">
                {t.home.noRecentActivity}
              </p>
              <div className="mt-4">
                <Link href="/homework" className="text-sm font-medium text-accent hover:underline">
                  {t.home.viewHomeworks} &rarr;
                </Link>
              </div>
            </div>
          )
        ) : (
          <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-8 text-center border border-dashed border-slate-200 dark:border-slate-800">
            <p className="text-slate-500 dark:text-slate-400 text-sm">
              {t.home.signInPrompt}
            </p>
            <div className="mt-4">
              <Link href="/login" className="text-sm font-medium text-accent hover:underline">
                {t.home.signInBtn} &rarr;
              </Link>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

