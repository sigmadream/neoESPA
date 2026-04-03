'use client';

import { useState } from 'react';
import { LayoutGrid, BookOpen, Bell, FileCode, Users, Settings, ShieldAlert, ChevronRight } from 'lucide-react';

import AuthGate from '@/components/AuthGate';
import AdminHomeworkManager from '@/components/admin/AdminHomeworkManager';
import AdminMaterialManager from '@/components/admin/AdminMaterialManager';
import AdminNoticeManager from '@/components/admin/AdminNoticeManager';
import AdminOverviewManager from '@/components/admin/AdminOverviewManager';
import AdminPlagiarismManager from '@/components/admin/AdminPlagiarismManager';
import AdminSettingsManager from '@/components/admin/AdminSettingsManager';
import AdminUserManager from '@/components/admin/AdminUserManager';
import { useAuth } from '@/components/AuthProvider';

const ADMIN_TABS = [
  { id: 'overview', label: 'Overview', icon: LayoutGrid, description: 'Stats & Queue' },
  { id: 'homeworks', label: 'Homework', icon: BookOpen, description: 'Assignments' },
  { id: 'notices', label: 'Notices', icon: Bell, description: 'Announcements' },
  { id: 'materials', label: 'Materials', icon: FileCode, description: 'Reference Files' },
  { id: 'users', label: 'Users', icon: Users, description: 'Access Control' },
  { id: 'settings', label: 'Settings', icon: Settings, description: 'Global Config' },
  { id: 'plagiarism', label: 'Plagiarism', icon: ShieldAlert, description: 'Detection' },
] as const;

export default function AdminDashboardPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<(typeof ADMIN_TABS)[number]['id']>('overview');
  
  const visibleTabs = ADMIN_TABS.filter(
    (tab) => !['users', 'settings'].includes(tab.id) || user?.user_group === 'admin',
  );
  
  const currentTab = visibleTabs.some((tab) => tab.id === activeTab)
    ? activeTab
    : (visibleTabs[0]?.id ?? 'overview');

  return (
    <AuthGate roles={['admin', 'instructor', 'ta']}>
      <div className="max-w-7xl mx-auto py-8 px-4 space-y-10">
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
              Admin Console
            </h1>
            <p className="text-slate-500 text-sm font-medium">Manage course operations, assignments, and student access.</p>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          <aside className="lg:col-span-1 space-y-1">
            <nav className="space-y-1">
              {visibleTabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center justify-between px-4 py-3 text-sm font-bold rounded transition-all ${
                    currentTab === tab.id
                      ? 'bg-accent text-white shadow-sm'
                      : 'text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-900 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <tab.icon size={18} className={currentTab === tab.id ? 'text-white' : 'text-slate-400'} />
                    <span>{tab.label}</span>
                  </div>
                  {currentTab === tab.id && <ChevronRight size={14} />}
                </button>
              ))}
            </nav>
            
            <div className="mt-8 p-4 card-simple bg-slate-50/50 dark:bg-slate-900/20 border-dashed">
              <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2 text-center">Current Context</h3>
              <p className="text-[11px] text-slate-500 text-center leading-relaxed">
                Role: <span className="text-accent font-bold">{user?.user_group.toUpperCase()}</span><br />
                {visibleTabs.find(t => t.id === currentTab)?.description}
              </p>
            </div>
          </aside>

          <main className="lg:col-span-3">
            <div className="space-y-8 animate-in fade-in duration-300">
              {currentTab === 'overview' && <AdminOverviewManager />}
              {currentTab === 'homeworks' && <AdminHomeworkManager />}
              {currentTab === 'notices' && <AdminNoticeManager />}
              {currentTab === 'materials' && <AdminMaterialManager />}
              {currentTab === 'users' && <AdminUserManager />}
              {currentTab === 'settings' && <AdminSettingsManager />}
              {currentTab === 'plagiarism' && <AdminPlagiarismManager />}
            </div>
          </main>
        </div>
      </div>
    </AuthGate>
  );
}
