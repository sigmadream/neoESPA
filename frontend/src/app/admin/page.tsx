'use client';

import { useState } from 'react';
import {
  LayoutGrid,
  BookOpen,
  Bell,
  FileCode,
  Users,
  Settings,
  ShieldAlert,
  ChevronRight,
  Gauge,
  RotateCcw,
  ScrollText,
  ShieldCheck,
  Trophy,
  FileCode2,
  ClipboardList,
  MailPlus,
} from 'lucide-react';

import AuthGate from '@/components/AuthGate';
import AdminAuditLogManager from '@/components/admin/AdminAuditLogManager';
import AdminContestManager from '@/components/admin/AdminContestManager';
import AdminExamManager from '@/components/admin/AdminExamManager';
import AdminGradingManager from '@/components/admin/AdminGradingManager';
import AdminInvitationManager from '@/components/admin/AdminInvitationManager';
import AdminHomeworkManager from '@/components/admin/AdminHomeworkManager';
import AdminMaterialManager from '@/components/admin/AdminMaterialManager';
import AdminNoticeManager from '@/components/admin/AdminNoticeManager';
import AdminOverviewManager from '@/components/admin/AdminOverviewManager';
import AdminPlagiarismManager from '@/components/admin/AdminPlagiarismManager';
import AdminProblemManager from '@/components/admin/AdminProblemManager';
import AdminRejudgeManager from '@/components/admin/AdminRejudgeManager';
import AdminRoleManager from '@/components/admin/AdminRoleManager';
import AdminSettingsManager from '@/components/admin/AdminSettingsManager';
import AdminUserManager from '@/components/admin/AdminUserManager';
import { useAuth } from '@/components/AuthProvider';

const ADMIN_TABS = [
  { id: 'overview', label: '현황 종합', icon: LayoutGrid, description: '통계 및 채점 큐' },
  { id: 'homeworks', label: '과제 관리', icon: BookOpen, description: '과제 등록 및 삭제' },
  { id: 'grading', label: '채점 운영', icon: Gauge, description: '채점 큐 · 워커 · 점수 조정' },
  { id: 'rejudge', label: '일괄 재채점', icon: RotateCcw, description: '범위 지정 재채점 작업' },
  { id: 'problems', label: '문제 뱅크', icon: FileCode2, description: '문제·리비전·테스트케이스' },
  { id: 'contests', label: '대회 운영', icon: Trophy, description: '대회 생성·게시·질문 답변' },
  { id: 'exams', label: '시험 관리', icon: ClipboardList, description: '시험 등록 및 일정 확인' },
  { id: 'notices', label: '공지사항 관리', icon: Bell, description: '강의 공지 등록' },
  { id: 'materials', label: '강의자료 관리', icon: FileCode, description: '참고 자료실 관리' },
  { id: 'users', label: '사용자 관리', icon: Users, description: '계정 승인 및 권한 관리' },
  { id: 'roles', label: '역할 권한', icon: ShieldCheck, description: '역할별 수행 권한 지정' },
  { id: 'invitations', label: '운영진 초대', icon: MailPlus, description: '관리자·조교 초대 발급' },
  { id: 'settings', label: '시스템 설정', icon: Settings, description: '전역 설정 및 규칙' },
  { id: 'plagiarism', label: '표절 검사', icon: ShieldAlert, description: '코드 유사도 검사' },
  { id: 'audit', label: '운영 로그', icon: ScrollText, description: '감사 로그 및 시스템 이벤트' },
] as const;

const TAB_CAPABILITIES: Record<(typeof ADMIN_TABS)[number]['id'], string[]> = {
  overview: ['observability:read'],
  homeworks: ['homework:manage'],
  grading: ['judge:operate'],
  rejudge: ['submission:rejudge'],
  problems: ['problem:create', 'problem:edit', 'problem:review', 'problem:publish'],
  contests: ['problem:publish'],
  exams: ['exam:manage'],
  notices: ['content:manage'],
  materials: ['content:manage'],
  users: ['user:manage'],
  roles: ['user:manage'],
  invitations: ['user:manage'],
  settings: ['settings:manage'],
  plagiarism: ['plagiarism:operate'],
  audit: ['audit:read'],
};

export default function AdminDashboardPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<(typeof ADMIN_TABS)[number]['id']>('overview');
  const effectiveCapabilities = new Set(user?.capabilities ?? []);
  const hasAllCapabilities = effectiveCapabilities.has('*');
  const visibleTabs = ADMIN_TABS.filter((tab) => {
    const required = TAB_CAPABILITIES[tab.id];
    return hasAllCapabilities || required.some((capability) => effectiveCapabilities.has(capability));
  });
  
  const currentTab = visibleTabs.some((tab) => tab.id === activeTab)
    ? activeTab
    : (visibleTabs[0]?.id ?? 'overview');

  return (
    <AuthGate roles={['super_admin', 'admin', 'instructor', 'ta', 'problem_setter', 'reviewer', 'judge_operator', 'support', 'viewer']}>
      <div className="max-w-7xl mx-auto py-8 px-4 space-y-10">
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
              관리자 콘솔
            </h1>
            <p className="text-slate-500 text-sm font-medium">강의 운영, 과제 관리 및 학생 권한을 관리합니다.</p>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          <aside className="lg:col-span-1 space-y-1">
            <nav className="space-y-1">
              {visibleTabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center justify-between px-4 py-3 text-sm font-bold rounded-lg transition-all ${
                    currentTab === tab.id
                      ? 'bg-blue-600 text-white dark:bg-blue-500 dark:text-white shadow-sm font-semibold'
                      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-slate-100'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <tab.icon size={18} className={currentTab === tab.id ? 'text-white' : 'text-slate-400 dark:text-slate-500'} />
                    <span className={currentTab === tab.id ? 'text-white' : ''}>{tab.label}</span>
                  </div>
                  {currentTab === tab.id && <ChevronRight size={14} className="text-white" />}
                </button>
              ))}
            </nav>
            
            <div className="mt-8 p-4 card-simple bg-slate-50/50 dark:bg-slate-900/20 border-dashed">
              <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2 text-center">현재 관리 권한</h3>
              <p className="text-[11px] text-slate-500 text-center leading-relaxed">
                권한: <span className="text-accent font-bold">{user?.user_group.toUpperCase()}</span><br />
                {visibleTabs.find(t => t.id === currentTab)?.description}
              </p>
            </div>
          </aside>

          <main className="lg:col-span-3">
            {visibleTabs.length === 0 && (
              <div className="card-simple py-16 text-center text-sm text-slate-500">
                현재 역할에 부여된 관리 권한이 없습니다.
              </div>
            )}
            {visibleTabs.length > 0 && <div className="space-y-8 animate-in fade-in duration-300">
              {currentTab === 'overview' && <AdminOverviewManager />}
              {currentTab === 'homeworks' && <AdminHomeworkManager />}
              {currentTab === 'grading' && <AdminGradingManager />}
              {currentTab === 'rejudge' && <AdminRejudgeManager />}
              {currentTab === 'problems' && <AdminProblemManager />}
              {currentTab === 'contests' && <AdminContestManager />}
              {currentTab === 'exams' && <AdminExamManager />}
              {currentTab === 'invitations' && <AdminInvitationManager />}
              {currentTab === 'notices' && <AdminNoticeManager />}
              {currentTab === 'materials' && <AdminMaterialManager />}
              {currentTab === 'users' && <AdminUserManager />}
              {currentTab === 'roles' && <AdminRoleManager />}
              {currentTab === 'settings' && <AdminSettingsManager />}
              {currentTab === 'plagiarism' && <AdminPlagiarismManager />}
              {currentTab === 'audit' && <AdminAuditLogManager />}
            </div>}
          </main>
        </div>
      </div>
    </AuthGate>
  );
}
