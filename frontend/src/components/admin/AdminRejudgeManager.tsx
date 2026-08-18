'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  Ban,
  ClipboardList,
  RefreshCw,
  RotateCcw,
  Search,
  Send,
} from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import {
  cancelRejudgeJob,
  createRejudgeJob,
  getAdminHomeworks,
  getRejudgeJobs,
  previewRejudge,
  retryFailedRejudgeJob,
  type HomeworkAdminApi,
  type JudgeJobApi,
  type RejudgePreviewApi,
  type RejudgeScopePayload,
} from '@/lib/api';

const SUBMISSION_STATUSES = [
  'pending',
  'queued',
  'grading',
  'graded',
  'failed',
];

function statusTone(status: string) {
  if (status === 'succeeded') return 'text-emerald-600 dark:text-emerald-400';
  if (['failed', 'dead_letter'].includes(status)) {
    return 'text-rose-600 dark:text-rose-400';
  }
  if (status === 'running') return 'text-accent';
  return 'text-slate-500 dark:text-slate-400';
}

function formatTime(value: string | null) {
  if (!value) return '-';
  const parsed = new Date(value.includes(' ') ? value.replace(' ', 'T') : value);
  return Number.isNaN(parsed.getTime()) ? '-' : parsed.toLocaleString();
}

export default function AdminRejudgeManager() {
  const { token } = useAuth();
  const [homeworks, setHomeworks] = useState<HomeworkAdminApi[]>([]);
  const [jobs, setJobs] = useState<JudgeJobApi[]>([]);
  const [preview, setPreview] = useState<RejudgePreviewApi | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isWorking, setIsWorking] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const [homeworkNum, setHomeworkNum] = useState('');
  const [userId, setUserId] = useState('');
  const [submissionIds, setSubmissionIds] = useState('');
  const [statuses, setStatuses] = useState<string[]>([]);
  const [reason, setReason] = useState('');

  const loadJobs = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      const [homeworkRes, jobRes] = await Promise.all([
        getAdminHomeworks(token),
        getRejudgeJobs(token, 20),
      ]);
      setHomeworks(homeworkRes);
      setJobs(jobRes);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '재채점 작업을 불러오지 못했습니다.',
      );
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  const buildScope = (): RejudgeScopePayload => {
    const parsedIds = submissionIds
      .split(/[\s,]+/)
      .map((value) => Number(value))
      .filter((value) => Number.isInteger(value) && value > 0);

    return {
      homework_num: homeworkNum ? Number(homeworkNum) : null,
      user_id: userId.trim() || null,
      submission_ids: parsedIds,
      statuses,
    };
  };

  const hasScope =
    homeworkNum !== '' ||
    userId.trim() !== '' ||
    submissionIds.trim() !== '' ||
    statuses.length > 0;

  const handlePreview = async () => {
    if (!token) return;
    setIsWorking(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      setPreview(await previewRejudge(buildScope(), token));
    } catch (error) {
      setPreview(null);
      setErrorMessage(
        error instanceof Error ? error.message : '대상을 조회하지 못했습니다.',
      );
    } finally {
      setIsWorking(false);
    }
  };

  const handleCreate = async () => {
    if (!token || !reason.trim()) return;
    setIsWorking(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      const job = await createRejudgeJob(
        {
          ...buildScope(),
          reason: reason.trim(),
          // 동일 요청이 중복 등록되지 않도록 백엔드가 사용하는 멱등 키.
          idempotency_key: `ui-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
        },
        token,
      );
      setSuccessMessage(`재채점 작업 #${job.id}을(를) 등록했습니다.`);
      setPreview(null);
      setReason('');
      await loadJobs();
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '재채점 작업을 등록하지 못했습니다.',
      );
    } finally {
      setIsWorking(false);
    }
  };

  const handleJobAction = async (jobId: number, action: 'cancel' | 'retry') => {
    if (!token) return;
    setIsWorking(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      const job =
        action === 'cancel'
          ? await cancelRejudgeJob(jobId, token)
          : await retryFailedRejudgeJob(jobId, token);
      setSuccessMessage(`작업 #${job.id} 상태: ${job.status}`);
      await loadJobs();
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '작업을 처리하지 못했습니다.',
      );
    } finally {
      setIsWorking(false);
    }
  };

  const toggleStatus = (status: string) => {
    setStatuses((previous) =>
      previous.includes(status)
        ? previous.filter((value) => value !== status)
        : [...previous, status],
    );
    setPreview(null);
  };

  if (isLoading && jobs.length === 0) {
    return (
      <div className="py-20 text-center animate-pulse text-slate-400 font-medium">
        재채점 작업을 불러오는 중입니다...
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <section className="card-simple">
        <header className="mb-8">
          <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-2">
            <RotateCcw size={16} className="text-accent" />
            일괄 재채점
          </h2>
          <p className="text-slate-500 text-sm font-medium leading-relaxed">
            채점 기준이나 테스트케이스가 바뀐 경우, 범위를 지정해 제출물을 한 번에 다시 채점합니다.
            등록 전에 반드시 대상 건수를 미리 확인하십시오.
          </p>
        </header>

        {(errorMessage || successMessage) && (
          <div
            className={`p-3 rounded text-[11px] font-medium border mb-6 ${
              errorMessage
                ? 'bg-rose-50 border-rose-100 text-rose-600 dark:bg-rose-950/20'
                : 'bg-emerald-50 border-emerald-100 text-emerald-600 dark:bg-emerald-950/20'
            }`}
          >
            {errorMessage || successMessage}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
              과제
            </span>
            <select
              value={homeworkNum}
              onChange={(event) => {
                setHomeworkNum(event.target.value);
                setPreview(null);
              }}
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
            >
              <option value="">전체 과제</option>
              {homeworks.map((homework) => (
                <option key={homework.num} value={homework.num}>
                  #{homework.num} {homework.title}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
              학생 ID
            </span>
            <input
              value={userId}
              onChange={(event) => {
                setUserId(event.target.value);
                setPreview(null);
              }}
              placeholder="비우면 전체 학생"
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
              제출 번호 (쉼표 구분)
            </span>
            <input
              value={submissionIds}
              onChange={(event) => {
                setSubmissionIds(event.target.value);
                setPreview(null);
              }}
              placeholder="예: 101, 102, 103"
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
            />
          </label>
        </div>

        <div className="mt-6">
          <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
            제출 상태
          </span>
          <div className="flex flex-wrap gap-2 mt-2">
            {SUBMISSION_STATUSES.map((status) => (
              <button
                key={status}
                onClick={() => toggleStatus(status)}
                className={`text-[11px] font-medium px-3 py-1.5 rounded border transition-all ${
                  statuses.includes(status)
                    ? 'border-blue-500 bg-blue-50 text-blue-600 dark:bg-blue-950/30 dark:text-blue-400'
                    : 'border-slate-200 dark:border-slate-800 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-900'
                }`}
              >
                {status}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-col md:flex-row md:items-end gap-4 mt-6">
          <label className="flex flex-col gap-1.5 flex-1">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
              재채점 사유 (필수)
            </span>
            <input
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="예: 3주차 테스트케이스 수정 반영"
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
            />
          </label>
          <div className="flex items-center gap-3">
            <button
              onClick={() => void handlePreview()}
              disabled={isWorking || !hasScope}
              className="btn-outline text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
            >
              <Search size={14} />대상 미리보기
            </button>
            <button
              onClick={() => void handleCreate()}
              disabled={isWorking || !hasScope || !reason.trim() || !preview}
              className="btn-flat text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
            >
              <Send size={14} />재채점 등록
            </button>
          </div>
        </div>

        {preview && (
          <div className="mt-6 p-4 rounded border border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
            <p className="text-xs font-bold text-slate-700 dark:text-slate-300">
              대상 제출물 {preview.target_count}건
              {preview.truncated && (
                <span className="ml-2 text-[11px] font-medium text-amber-600 dark:text-amber-400">
                  (미리보기 목록은 일부만 표시됩니다)
                </span>
              )}
            </p>
            <p className="text-[11px] text-slate-500 font-mono mt-2 break-all">
              {preview.submission_ids.join(', ') || '해당 조건에 맞는 제출물이 없습니다.'}
            </p>
          </div>
        )}
      </section>

      <section className="card-simple">
        <header className="flex items-center justify-between gap-4 mb-6">
          <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2">
            <ClipboardList size={16} className="text-accent" />
            재채점 작업 이력
          </h2>
          <button
            onClick={() => void loadJobs()}
            disabled={isWorking}
            className="btn-outline text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            새로고침
          </button>
        </header>

        {jobs.length === 0 ? (
          <p className="text-xs text-slate-400 italic">등록된 재채점 작업이 없습니다.</p>
        ) : (
          <div className="divide-y divide-slate-50 dark:divide-slate-900">
            {jobs.map((job) => (
              <div
                key={job.id}
                className="py-4 first:pt-0 last:pb-0 grid grid-cols-1 md:grid-cols-4 gap-4 items-center"
              >
                <div className="min-w-0">
                  <p className="text-sm font-bold text-slate-900 dark:text-white">#{job.id}</p>
                  <p className={`text-[11px] font-bold uppercase ${statusTone(job.status)}`}>
                    {job.status}
                  </p>
                </div>
                <div className="flex flex-col">
                  <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter">
                    진행률 / 시도
                  </span>
                  <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
                    {Math.round(job.progress * 100)}% · {job.attempt_count}/{job.max_attempts}
                  </span>
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter">
                    등록 시각
                  </span>
                  <span className="text-xs font-medium text-slate-600 dark:text-slate-400 truncate">
                    {formatTime(job.created_at)}
                  </span>
                </div>
                <div className="flex items-center gap-2 md:justify-end">
                  <button
                    onClick={() => void handleJobAction(job.id, 'retry')}
                    disabled={isWorking}
                    className="btn-outline text-[11px] h-8 px-3 flex items-center gap-1.5 disabled:opacity-50"
                  >
                    <RotateCcw size={12} />실패 재시도
                  </button>
                  <button
                    onClick={() => void handleJobAction(job.id, 'cancel')}
                    disabled={isWorking}
                    className="btn-outline text-[11px] h-8 px-3 flex items-center gap-1.5 disabled:opacity-50"
                  >
                    <Ban size={12} />취소
                  </button>
                </div>
                {job.error_message && (
                  <p className="md:col-span-4 text-[11px] text-rose-600 dark:text-rose-400 font-medium">
                    {job.error_message}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
