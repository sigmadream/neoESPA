'use client';

import { startTransition, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { LogIn, UserPlus } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';

export default function LoginPage() {
  const { login, isLoading, isAuthenticated } = useAuth();
  const router = useRouter();
  const [id, setId] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    try {
      await login({ id, password });
      const nextPath = typeof window === 'undefined'
          ? '/'
          : new URLSearchParams(window.location.search).get('next') ?? '/';
      startTransition(() => {
        router.push(nextPath);
      });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Login failed.');
    }
  };

  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="max-w-md w-full card-simple space-y-8 py-10 px-8">
        <header className="text-center">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center justify-center gap-2 mb-2">
            <LogIn className="text-accent" size={24} />
            Sign In
          </h1>
          <p className="text-slate-500 text-sm font-medium">
            Enter your credentials to access neoESPA.
          </p>
        </header>

        {isAuthenticated && (
          <div className="p-3 rounded bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-900/30 text-xs font-medium text-emerald-600 dark:text-emerald-400">
            Session active. Redirecting to dashboard...
          </div>
        )}

        <form className="space-y-6" onSubmit={(e) => void handleSubmit(e)}>
          <div className="space-y-4">
            <div>
              <label htmlFor="id" className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">
                User ID
              </label>
              <input
                id="id"
                type="text"
                required
                className="block w-full text-sm rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2.5 outline-none focus:ring-1 focus:ring-accent transition-all"
                placeholder="Your unique ID"
                value={id}
                onChange={(e) => setId(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                className="block w-full text-sm rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2.5 outline-none focus:ring-1 focus:ring-accent transition-all"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <p className="text-[11px] text-slate-400 font-medium">
              Secure authentication via JWT.
            </p>
            <Link href="#" className="text-[11px] font-bold text-accent hover:underline">
              Forgot password?
            </Link>
          </div>

          {errorMessage && (
            <div className="p-3 rounded bg-rose-50 dark:bg-rose-950/20 border border-rose-100 dark:border-rose-900/30 text-xs font-medium text-rose-600 dark:text-rose-400">
              {errorMessage}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="btn-flat w-full h-11 flex items-center justify-center gap-2 disabled:opacity-50 shadow-sm"
          >
            {isLoading ? (
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <LogIn size={16} />
            )}
            <span>Sign In to System</span>
          </button>
        </form>

        <footer className="pt-6 border-t border-slate-100 dark:border-slate-800 text-center">
          <p className="text-xs text-slate-500 font-medium">
            New to neoESPA?{' '}
            <Link href="/register" className="text-accent hover:underline font-bold inline-flex items-center gap-1">
              Create account <UserPlus size={12} />
            </Link>
          </p>
        </footer>
      </div>
    </div>
  );
}
