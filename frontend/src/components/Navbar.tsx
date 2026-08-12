'use client';

import { useEffect, useState, useSyncExternalStore } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import { Sun, Moon, Monitor, LogOut } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import { useTranslation } from '@/i18n/LanguageContext';
import { getNotifications } from '@/lib/api';

const subscribeToNothing = () => () => {};

const Navbar = () => {
  const { theme, setTheme } = useTheme();
  const { token, user, isAuthenticated, isLoading, logout } = useAuth();
  const { t } = useTranslation();
  const router = useRouter();

  const isThemeMounted = useSyncExternalStore(
    subscribeToNothing,
    () => true,
    () => false,
  );
  const [unreadNotificationCount, setUnreadNotificationCount] = useState(0);
  const displayedNotificationCount = token ? unreadNotificationCount : 0;

  useEffect(() => {
    if (!token) return;
    let isMounted = true;
    void getNotifications(token)
      .then((notifications) => {
        if (isMounted) {
          setUnreadNotificationCount(
            notifications.filter((n) => !n.is_read).length,
          );
        }
      })
      .catch(() => {
        if (isMounted) setUnreadNotificationCount(0);
      });
    return () => { isMounted = false; };
  }, [token]);

  const activeTheme = isThemeMounted ? theme : undefined;

  return (
    <nav className="border-b border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-slate-950/90 backdrop-blur-sm sticky top-0 z-50 transition-base">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-10">
          <Link href="/" className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
            neoESPA
          </Link>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium">
            {isAuthenticated && (
              <Link href="/dashboard" className="text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors">{t.nav.dashboard}</Link>
            )}
            <Link href="/homework" className="text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors">{t.nav.homework}</Link>
            <Link href="/exam" className="text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors">{t.nav.exam}</Link>
            <Link href="/notice" className="text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors">{t.nav.notices}</Link>
            <Link href="/materials" className="text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors">{t.nav.materials}</Link>
            <Link href="/qa" className="text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors">{t.nav.qa}</Link>
            {isAuthenticated && (
              <Link href="/notifications" className="relative text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors">
                {t.nav.notifications}
                {displayedNotificationCount > 0 && (
                  <span className="absolute -top-1.5 -right-2.5 flex h-4 w-4 items-center justify-center rounded-full bg-blue-600 text-[10px] font-bold text-white">
                    {displayedNotificationCount}
                  </span>
                )}
              </Link>
            )}
            {user && ['admin', 'instructor', 'ta'].includes(user.user_group) && (
              <Link href="/admin" className="text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors font-semibold">{t.nav.admin}</Link>
            )}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center bg-slate-50 dark:bg-slate-900 rounded-md p-0.5 border border-slate-200 dark:border-slate-800">
            <button onClick={() => setTheme('light')} className={`p-1.5 rounded transition-all ${activeTheme === 'light' ? 'bg-white dark:bg-slate-800 text-blue-600 shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}><Sun size={14} /></button>
            <button onClick={() => setTheme('system')} className={`p-1.5 rounded transition-all ${activeTheme === 'system' ? 'bg-white dark:bg-slate-800 text-blue-600 shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}><Monitor size={14} /></button>
            <button onClick={() => setTheme('dark')} className={`p-1.5 rounded transition-all ${activeTheme === 'dark' ? 'bg-white dark:bg-slate-800 text-blue-600 shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}><Moon size={14} /></button>
          </div>

          {isLoading ? (
            <div className="h-8 w-24 bg-slate-100 dark:bg-slate-900 animate-pulse rounded" />
          ) : isAuthenticated && user ? (
            <div className="flex items-center gap-4 pl-4 border-l border-slate-200 dark:border-slate-800">
              <Link href="/profile" className="text-sm font-medium text-slate-700 dark:text-slate-300 hover:underline">
                {user.name}
              </Link>
              <button
                onClick={() => { logout(); router.push('/login'); }}
                className="text-slate-400 hover:text-rose-600 transition-colors"
                title={t.nav.logout}
              >
                <LogOut size={18} />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <Link href="/login" className="text-sm font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors px-2 py-1">{t.nav.login}</Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
