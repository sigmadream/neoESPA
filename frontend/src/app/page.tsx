import Link from 'next/link';
import { BookOpen, FileCode, Bell, User } from 'lucide-react';

export default function Home() {
  return (
    <div className="max-w-5xl mx-auto py-12 px-4">
      <header className="mb-12">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100 mb-2">
          Dashboard
        </h1>
        <p className="text-slate-500 dark:text-slate-400">
          Welcome to neoESPA. Manage your programming assignments and view results.
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Link href="/homework" className="card-simple hover:border-accent transition-colors group">
          <div className="flex items-start space-x-4">
            <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg group-hover:bg-blue-100 transition-colors">
              <BookOpen className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold mb-1">Homeworks</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                View upcoming assignments and submit your solutions.
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
              <h2 className="text-lg font-semibold mb-1">Notices</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Check important announcements and course updates.
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
              <h2 className="text-lg font-semibold mb-1">My Profile</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Manage your account settings and view submission history.
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
              <h2 className="text-lg font-semibold mb-1">Materials</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Access lecture notes, examples, and reference guides.
              </p>
            </div>
          </div>
        </Link>
      </div>

      <section className="mt-16 pt-12 border-t border-slate-100 dark:border-slate-800">
        <h2 className="text-xl font-semibold mb-6">Recent Activity</h2>
        <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-8 text-center border border-dashed border-slate-200 dark:border-slate-800">
          <p className="text-slate-500 dark:text-slate-400 text-sm">
            Sign in to see your recent activity and submission status.
          </p>
          <div className="mt-4">
            <Link href="/login" className="text-sm font-medium text-accent hover:underline">
              Sign In &rarr;
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
