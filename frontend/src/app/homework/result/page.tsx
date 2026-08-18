'use client';

import Link from 'next/link';
import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { CheckCircle2, AlertCircle, Clock, History, RotateCcw, LayoutList, ChevronLeft } from 'lucide-react';

import AuthGate from '@/components/AuthGate';
import { useAuth } from '@/components/AuthProvider';
import {
  getMySubmissions,
  getSubmission,
  getSubmissionFeedback,
  type SubmissionFeedbackApi,
  type SubmissionApi,
} from '@/lib/api';

function getStatusMeta(submission: SubmissionApi) {
  if (submission.status === 'failed' || submission.compile_status === 'failed' || submission.run_status === 'failed') {
    return {
      title: 'Grading Failed',
      colorClass: 'text-rose-600 dark:text-rose-400',
      bgClass: 'bg-rose-50 dark:bg-rose-950/20',
      icon: AlertCircle
    };
  }
  if (['graded', 'success', 'passed'].includes(submission.status)) {
    return {
      title: 'Grading Complete',
      colorClass: 'text-emerald-600 dark:text-emerald-400',
      bgClass: 'bg-emerald-50 dark:bg-emerald-950/20',
      icon: CheckCircle2
    };
  }
  return {
    title: 'Grading Pending',
    colorClass: 'text-amber-600 dark:text-amber-400',
    bgClass: 'bg-amber-50 dark:bg-amber-950/20',
    icon: Clock
  };
}

function HomeworkResultContent() {
  const { token } = useAuth();
  const searchParams = useSearchParams();
  const requestedSubmissionId = searchParams.get('id');

  const [submission, setSubmission] = useState<SubmissionApi | null>(null);
  const [feedback, setFeedback] = useState<SubmissionFeedbackApi | null>(null);
  const [history, setHistory] = useState<SubmissionApi[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (!token) return;
    const authToken: string = token;
    let isMounted = true;
    async function loadSubmissionData() {
      setIsLoading(true);
      try {
        if (requestedSubmissionId) {
          const sid = Number(requestedSubmissionId);
          const detail = await getSubmission(sid, authToken);
          const [relHistory, fb] = await Promise.all([
            getMySubmissions(authToken, detail.homework_num),
            getSubmissionFeedback(sid, authToken)
          ]);
          if (isMounted) {
            setSubmission(detail);
            setHistory(relHistory);
            setFeedback(fb);
          }
        } else {
          const submissions = await getMySubmissions(authToken);
          if (submissions[0]) {
            const fb = await getSubmissionFeedback(submissions[0].id, authToken);
            if (isMounted) {
              setSubmission(submissions[0]);
              setHistory(submissions);
              setFeedback(fb);
            }
          } else if (isMounted) {
            setSubmission(null);
            setFeedback(null);
          }
        }
      } catch (error) {
        if (isMounted) setErrorMessage(error instanceof Error ? error.message : 'Failed to load results.');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    void loadSubmissionData();
    return () => { isMounted = false; };
  }, [requestedSubmissionId, token]);

  if (isLoading) return <div className="py-20 text-center animate-pulse text-slate-400 font-medium">Analyzing results...</div>;
  if (errorMessage) return <div className="max-w-4xl mx-auto py-10"><div className="card-simple border-rose-100 bg-rose-50 dark:bg-rose-950/20 text-rose-600 dark:text-rose-400 text-sm font-medium">{errorMessage}</div></div>;
  if (!submission) return <div className="max-w-3xl mx-auto py-16 text-center space-y-6"><h1 className="text-2xl font-bold">No submissions yet</h1><Link href="/homework" className="btn-flat inline-flex items-center gap-2 px-6 py-3"><LayoutList size={18} />Go to Homework</Link></div>;

  const statusMeta = getStatusMeta(submission);

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-10">
      <header className="flex items-center justify-between">
        <div>
          <Link href="/homework" className="inline-flex items-center text-xs font-bold text-slate-400 hover:text-accent uppercase tracking-widest mb-4 transition-colors">
            <ChevronLeft size={14} className="mr-1" />
            과제 목록으로 돌아가기
          </Link>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">과제 제출 및 채점 결과</h1>
          <p className="text-slate-500 text-sm font-medium mt-1">
            과제 #{submission.homework_num} · {submission.homework_title}
          </p>
        </div>
        <div className={`flex items-center gap-2 px-4 py-2 rounded-full border ${statusMeta.bgClass} border-current/10 ${statusMeta.colorClass}`}>
          <statusMeta.icon size={16} />
          <span className="text-xs font-bold uppercase tracking-tighter">{statusMeta.title}</span>
        </div>
      </header>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 text-center">
        {[
          { label: '종합 점수', value: submission.total_score, highlight: 'text-accent' },
          { label: '기능 점수', value: submission.submission_score, highlight: 'text-emerald-600' },
          { label: '품질 점수', value: submission.quality_score, highlight: 'text-amber-600' },
          { label: '제출 횟수', value: `${submission.attempt_no}회차`, highlight: 'text-slate-900 dark:text-slate-100' },
          { label: '제출 언어', value: submission.language, highlight: 'text-slate-900 dark:text-slate-100' },
          { label: '채점 상태', value: submission.status, highlight: 'text-slate-900 dark:text-slate-100' },
        ].map((stat) => (
          <div key={stat.label} className="card-simple py-4 flex flex-col justify-between">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">{stat.label}</span>
            <span className={`text-2xl font-black ${stat.highlight}`}>{stat.value}</span>
          </div>
        ))}
      </div>

      {submission.manual_total_score !== null && (
        <div className="card-simple border-blue-200/60 bg-blue-50/40 dark:bg-blue-950/10">
          <h2 className="text-xs font-bold uppercase tracking-widest text-accent mb-2 flex items-center gap-2">
            <AlertCircle size={14} />
            운영진 점수 조정 내역
          </h2>
          <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
            자동 채점 결과 대신 운영진이 확정한 점수 <span className="font-bold">{submission.manual_total_score}점</span>이 반영되었습니다.
          </p>
          <p className="text-[11px] text-slate-500 font-medium mt-1">
            사유: {submission.score_adjustment_note || '별도 사유가 기록되지 않았습니다.'}
            {submission.score_adjusted_by ? ` · 처리자: ${submission.score_adjusted_by}` : ''}
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <section className="card-simple">
            <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-4 flex items-center gap-2">
              <AlertCircle size={14} />
              채점 요약 피드백
            </h2>
            <div className="bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded p-4 font-mono text-[13px] leading-relaxed text-slate-700 dark:text-slate-300 overflow-x-auto whitespace-pre-line min-h-[100px]">
              {submission.grader_summary || '채점 진행 중입니다. 잠시만 기다려 주세요.'}
            </div>
          </section>

          {(submission.compile_status === 'failed' || submission.compile_log) && (
            <section className="card-simple border-rose-200/60 bg-rose-50/40 dark:bg-rose-950/10">
              <h2 className="text-xs font-bold uppercase tracking-widest text-rose-600 dark:text-rose-400 mb-3 flex items-center gap-2">
                <AlertCircle size={14} />
                컴파일 에러 및 빌드 로그
              </h2>
              <div className="bg-slate-950 text-rose-300 border border-rose-900/30 rounded p-4 font-mono text-xs leading-relaxed overflow-x-auto whitespace-pre-wrap max-h-[300px]">
                {submission.compile_log || '실행 과정에서 컴파일 오류가 발생했습니다. 구문 문법과 언어 규칙을 확인하세요.'}
              </div>
            </section>
          )}

          {feedback && (
            <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="card-simple bg-amber-50/30 dark:bg-amber-950/10 border-amber-100/50">
                <h2 className="text-xs font-bold uppercase tracking-widest text-amber-600 mb-4">권장 개선 사항</h2>
                <p className="text-sm font-medium text-amber-800 dark:text-amber-200 mb-4">{feedback.deadline_message}</p>
                <ul className="space-y-2">
                  {feedback.hints.map((hint, idx) => (
                    <li key={idx} className="text-xs text-amber-700 dark:text-amber-400 flex items-start gap-2 italic">
                      <span className="w-1 h-1 rounded-full bg-amber-400 mt-1.5 shrink-0" />
                      {hint}
                    </li>
                  ))}
                </ul>
              </div>
              {feedback.coding_rule_guides.length > 0 && (
                <div className="card-simple bg-blue-50/30 dark:bg-blue-950/10 border-blue-100/50">
                  <h2 className="text-xs font-bold uppercase tracking-widest text-blue-600 mb-4">코드 품질 가이드</h2>
                  <div className="space-y-3">
                    {feedback.coding_rule_guides.slice(0, 2).map((guide) => (
                      <div key={guide.rule}>
                        <p className="text-xs font-bold text-blue-800 dark:text-blue-300">{guide.rule}</p>
                        <p className="text-[11px] text-blue-600 dark:text-blue-400">{guide.summary}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>
          )}
        </div>

        <aside className="space-y-6">
          <section className="card-simple">
            <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-5 flex items-center gap-2">
              <History size={14} />
              제출 히스토리
            </h2>
            <div className="space-y-3">
              {history.map((item) => (
                <Link key={item.id} href={`/homework/result?id=${item.id}`} className={`block p-3 rounded border transition-all ${item.id === submission.id ? 'border-accent bg-accent/5' : 'border-transparent hover:border-slate-100 dark:hover:border-slate-800 hover:bg-slate-50'}`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold">{item.attempt_no}회차 제출</span>
                    <span className="text-xs font-mono font-bold text-slate-500">{item.total_score}점</span>
                  </div>
                  <p className="text-[10px] text-slate-400">{new Date(item.submitted_at).toLocaleDateString()}</p>
                </Link>
              ))}
            </div>
          </section>

          <div className="space-y-3">
            <Link href={`/homework/${submission.homework_num}#submission-panel`} className="btn-flat w-full h-11 flex items-center justify-center gap-2 text-sm">
              <RotateCcw size={16} />
              수정하여 다시 제출하기
            </Link>
            <Link href="/homework" className="btn-outline w-full h-11 flex items-center justify-center gap-2 text-sm bg-white dark:bg-transparent">
              <LayoutList size={16} />
              전체 과제 목록으로
            </Link>
          </div>
        </aside>
      </div>
    </div>
  );
}

export default function HomeworkResultPage() {
  return (
    <AuthGate>
      <Suspense fallback={<div className="py-20 text-center text-slate-400 font-medium">Loading submission...</div>}>
        <HomeworkResultContent />
      </Suspense>
    </AuthGate>
  );
}
