'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { LayoutDashboard, CheckCircle2, Clock, BarChart3, AlertCircle, ChevronRight, ArrowUpRight } from 'lucide-react';

import AuthGate from '@/components/AuthGate';
import { useAuth } from '@/components/AuthProvider';
import {
  getStudentDashboard,
  type StudentDashboardApi,
  type StudentDashboardHomeworkItemApi,
} from '@/lib/api';
import { parseServerDate } from '@/lib/datetime';

const STATUS_META: Record<
  StudentDashboardHomeworkItemApi['schedule_status'],
  { label: string; className: string }
> = {
  upcoming: {
    label: '개설 예정',
    className: 'text-slate-400 bg-slate-50 dark:bg-slate-900',
  },
  open: {
    label: '제출 가능',
    className: 'text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-900/20',
  },
  closing_soon: {
    label: '마감 임박',
    className: 'text-amber-600 bg-amber-50 dark:text-amber-400 dark:bg-amber-900/20',
  },
  closed: {
    label: '마감됨',
    className: 'text-rose-600 bg-rose-50 dark:text-rose-400 dark:bg-rose-900/20',
  },
};

function formatDate(value: string | null) {
  if (!value) return '-';
  const parsed = parseServerDate(value);
  if (!parsed) return value;
  return parsed.toLocaleDateString() + ' ' + parsed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatRemainingTime(seconds: number | null, status: string) {
  if (seconds === null || status === 'closed' || seconds <= 0) return '마감 완료';
  const days = Math.floor(seconds / 86_400);
  const hours = Math.floor((seconds % 86_400) / 3_600);
  if (days > 0) return `${days}일 ${hours}시간 남음`;
  const minutes = Math.floor((seconds % 3_600) / 60);
  return `${hours}시간 ${minutes}분 남음`;
}

function DashboardContent() {
  const { token, user } = useAuth();
  const [dashboard, setDashboard] = useState<StudentDashboardApi | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (!token) return;
    const authToken: string = token;
    let isMounted = true;
    async function loadDashboard() {
      setIsLoading(true);
      try {
        const response = await getStudentDashboard(authToken);
        if (isMounted) setDashboard(response);
      } catch (error) {
        if (isMounted) setErrorMessage(error instanceof Error ? error.message : '대시보드를 불러오는 중 오류가 발생했습니다.');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    void loadDashboard();
    return () => { isMounted = false; };
  }, [token]);

  if (isLoading) return <div className="py-20 text-center animate-pulse text-slate-400 font-medium">대시보드 데이터를 불러오는 중...</div>;
  if (errorMessage) return <div className="max-w-5xl mx-auto py-10"><div className="card-simple border-rose-100 bg-rose-50 dark:bg-rose-950/20 text-rose-600 dark:text-rose-400 text-sm font-medium">{errorMessage}</div></div>;
  if (!dashboard) return null;

  const nextDeadline = dashboard.homework_items
    .filter((item) => item.schedule_status !== 'closed' && item.remaining_seconds !== null)
    .sort((left, right) => (left.remaining_seconds ?? 0) - (right.remaining_seconds ?? 0))[0] ?? null;

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-10">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
            <LayoutDashboard className="text-accent" size={24} />
            학생 대시보드
          </h1>
          <p className="text-slate-500 text-sm font-medium">반갑습니다, <span className="text-slate-900 dark:text-slate-200 font-bold">{user?.name}님</span>! 진행 중인 과제 현황 및 성적 현황입니다.</p>
        </div>
        {nextDeadline && (
          <div className="inline-flex items-center gap-3 px-4 py-2 bg-amber-50 dark:bg-amber-950/20 border border-amber-100 dark:border-amber-900/30 rounded-lg">
            <Clock className="text-amber-600 dark:text-amber-400" size={16} />
            <div className="text-xs">
              <p className="text-amber-800 dark:text-amber-300 font-bold uppercase tracking-tighter">다음 과제 마감일</p>
              <p className="text-amber-600 dark:text-amber-400 font-medium">{nextDeadline.title} · {formatRemainingTime(nextDeadline.remaining_seconds, nextDeadline.schedule_status)}</p>
            </div>
          </div>
        )}
      </header>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: '부여된 과제 수', value: `${dashboard.overview.total_homeworks}개`, icon: BarChart3 },
          { label: '제출 완료 과제', value: `${dashboard.overview.submitted_homeworks}개`, icon: CheckCircle2 },
          { label: '미제출 / 진행 중', value: `${dashboard.overview.pending_homeworks}개`, icon: Clock },
          { label: '평균 성적 점수', value: dashboard.overview.average_latest_score !== null ? `${dashboard.overview.average_latest_score.toFixed(1)}점` : '-', icon: ArrowUpRight },
        ].map((stat) => (
          <div key={stat.label} className="card-simple flex flex-col justify-between py-4 px-5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 flex items-center justify-between">
              {stat.label}
              <stat.icon size={12} className="opacity-50" />
            </span>
            <span className="text-2xl font-bold text-slate-900 dark:text-white mt-2">{stat.value}</span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <section className="card-simple">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400">진행 중인 과제 목록</h2>
              <Link href="/homework" className="text-xs font-medium text-accent hover:underline">전체 과제 보기 &rarr;</Link>
            </div>
            <div className="divide-y divide-slate-50 dark:divide-slate-900">
              {dashboard.homework_items.length === 0 ? (
                <p className="py-10 text-center text-sm text-slate-400">진행 중인 과제가 없습니다.</p>
              ) : (
                dashboard.homework_items.map((item) => (
                  <div key={item.homework_num} className="py-4 first:pt-0 last:pb-0 flex items-center justify-between group">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Link href={`/homework/${item.homework_num}`} className="text-sm font-bold text-slate-900 dark:text-white hover:text-accent transition-colors truncate">
                          #{item.homework_num} {item.title}
                        </Link>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-tighter ${STATUS_META[item.schedule_status].className}`}>
                          {STATUS_META[item.schedule_status].label}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 font-medium">
                        제출 마감일: {formatDate(item.deadline)} · 총 {item.submission_count}회 제출
                      </p>
                    </div>
                    <div className="flex items-center gap-4 ml-4">
                      <div className="text-right hidden sm:block">
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">최근 제출 점수</p>
                        <p className={`text-sm font-bold ${item.latest_score !== null ? 'text-slate-900 dark:text-slate-100' : 'text-slate-300'}`}>
                          {item.latest_score !== null ? `${item.latest_score.toFixed(1)}점` : (item.latest_submission_status ? '채점 중' : '미제출')}
                        </p>
                      </div>
                      <Link href={`/homework/${item.homework_num}#submission-panel`} className="p-2 rounded-md hover:bg-slate-50 dark:hover:bg-slate-900 text-slate-300 hover:text-accent transition-all">
                        <ChevronRight size={20} />
                      </Link>
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>

        <aside className="space-y-8">
          <section className="card-simple">
            <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-5">최근 답안 제출 이력</h2>
            <div className="space-y-4">
              {dashboard.recent_submissions.length === 0 ? (
                <p className="text-xs text-slate-400 italic">최근 제출한 이력이 없습니다.</p>
              ) : (
                dashboard.recent_submissions.map((sub) => (
                  <Link key={sub.id} href={`/homework/result?id=${sub.id}`} className="block p-3 rounded border border-transparent hover:border-slate-100 dark:hover:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900/50 transition-all">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-xs font-bold truncate">#{sub.homework_num} {sub.homework_title}</p>
                      <span className="text-xs font-mono font-bold text-accent">{sub.total_score.toFixed(1)}점</span>
                    </div>
                    <p className="text-[10px] text-slate-400 font-medium">채점 상태: {sub.status} · {new Date(sub.submitted_at).toLocaleDateString()}</p>
                  </Link>
                ))
              )}
            </div>
          </section>

          <section className="card-simple border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-900/10">
            <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4">주요 점검 대상</h2>
            <div className="space-y-3">
              {[
                { label: '마감 임박 과제', value: `${dashboard.overview.closing_soon_homeworks}개`, color: 'text-amber-600' },
                { label: '미제출 (기한 만료)', value: `${dashboard.overview.missing_homeworks}개`, color: 'text-rose-600' },
                { label: '채점 완료 과제', value: `${dashboard.overview.graded_homeworks}개`, color: 'text-blue-600' },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between text-xs font-medium">
                  <span className="text-slate-500">{item.label}</span>
                  <span className={`font-bold ${item.color}`}>{item.value}</span>
                </div>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <AuthGate>
      <DashboardContent />
    </AuthGate>
  );
}
