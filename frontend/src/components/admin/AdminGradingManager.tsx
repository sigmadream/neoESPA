'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  AlertOctagon,
  Cpu,
  Gauge,
  HardDrive,
  ListChecks,
  Pencil,
  PlayCircle,
  RefreshCw,
  RotateCcw,
  Timer,
  Zap,
} from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import {
  adjustSubmissionScore,
  createArtifactReconcileJob,
  getArtifactJobs,
  getGradingIncidents,
  getGradingMetrics,
  getJudgeJobs,
  getJudgeWorkers,
  gradeSubmissionNow,
  processNextGradingJob,
  queueSubmissionForGrading,
  requeueSubmissionForGrading,
  setJudgeWorkerState,
  type GradingMetricsApi,
  type JudgeJobApi,
  type JudgeWorkerApi,
} from '@/lib/api';

const JOB_STATUS_FILTERS = [
  { value: '', label: '전체 상태' },
  { value: 'queued', label: '대기' },
  { value: 'running', label: '진행 중' },
  { value: 'succeeded', label: '성공' },
  { value: 'failed', label: '실패' },
  { value: 'dead_letter', label: '데드레터' },
  { value: 'cancelled', label: '취소됨' },
];

const WORKER_ACTIONS = [
  { action: 'enable' as const, label: '활성화' },
  { action: 'drain' as const, label: '드레인' },
  { action: 'disable' as const, label: '비활성화' },
];

function statusTone(status: string) {
  if (['succeeded', 'online', 'idle'].includes(status)) {
    return 'text-emerald-600 dark:text-emerald-400';
  }
  if (['failed', 'dead_letter', 'offline', 'disabled'].includes(status)) {
    return 'text-rose-600 dark:text-rose-400';
  }
  if (['running', 'busy', 'draining'].includes(status)) {
    return 'text-accent';
  }
  return 'text-slate-500 dark:text-slate-400';
}

function formatTime(value: string | null) {
  if (!value) return '-';
  const parsed = new Date(value.includes(' ') ? value.replace(' ', 'T') : value);
  return Number.isNaN(parsed.getTime()) ? '-' : parsed.toLocaleString();
}

export default function AdminGradingManager() {
  const { token } = useAuth();
  const [metrics, setMetrics] = useState<GradingMetricsApi | null>(null);
  const [workers, setWorkers] = useState<JudgeWorkerApi[]>([]);
  const [jobs, setJobs] = useState<JudgeJobApi[]>([]);
  const [incidents, setIncidents] = useState<JudgeJobApi[]>([]);
  const [artifactJobs, setArtifactJobs] = useState<JudgeJobApi[]>([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isWorking, setIsWorking] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const [submissionId, setSubmissionId] = useState('');
  const [manualScore, setManualScore] = useState('');
  const [adjustmentNote, setAdjustmentNote] = useState('');

  const loadAll = useCallback(
    async (nextStatus?: string) => {
      if (!token) return;
      setIsLoading(true);
      setErrorMessage('');
      try {
        const [metricsRes, workersRes, jobsRes, incidentsRes, artifactRes] =
          await Promise.all([
            getGradingMetrics(token),
            getJudgeWorkers(token),
            getJudgeJobs(token, {
              status: nextStatus ?? statusFilter,
              limit: 30,
            }),
            getGradingIncidents(token, { limit: 20 }),
            getArtifactJobs(token),
          ]);
        setMetrics(metricsRes);
        setWorkers(workersRes);
        setJobs(jobsRes);
        setIncidents(incidentsRes);
        setArtifactJobs(artifactRes);
      } catch (error) {
        setErrorMessage(
          error instanceof Error ? error.message : '채점 현황을 불러오지 못했습니다.',
        );
      } finally {
        setIsLoading(false);
      }
    },
    [statusFilter, token],
  );

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  const runAction = async (
    action: (authToken: string) => Promise<string>,
    fallbackError: string,
  ) => {
    if (!token) return;
    setIsWorking(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      setSuccessMessage(await action(token));
      await loadAll();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : fallbackError);
    } finally {
      setIsWorking(false);
    }
  };

  const handleProcessNext = () =>
    runAction(async (authToken) => {
      const submission = await processNextGradingJob(authToken);
      return submission
        ? `제출 #${submission.id} 채점을 처리했습니다. (상태: ${submission.status})`
        : '대기 중인 채점 작업이 없습니다.';
    }, '채점 처리를 실행하지 못했습니다.');

  const handleWorkerAction = (
    workerId: string,
    action: 'enable' | 'disable' | 'drain',
  ) =>
    runAction(async (authToken) => {
      const worker = await setJudgeWorkerState(workerId, action, authToken);
      return `워커 ${worker.worker_id} 상태를 ${worker.status}(으)로 변경했습니다.`;
    }, '워커 상태를 변경하지 못했습니다.');

  const parsedSubmissionId = Number(submissionId);
  const hasSubmissionTarget =
    Number.isInteger(parsedSubmissionId) && parsedSubmissionId > 0;

  const handleSubmissionAction = (kind: 'queue' | 'requeue' | 'grade') =>
    runAction(async (authToken) => {
      const request =
        kind === 'queue'
          ? queueSubmissionForGrading
          : kind === 'requeue'
            ? requeueSubmissionForGrading
            : gradeSubmissionNow;
      const submission = await request(parsedSubmissionId, authToken);
      return `제출 #${submission.id} 처리 완료 (상태: ${submission.status}, 점수: ${submission.total_score})`;
    }, '제출물 처리를 실행하지 못했습니다.');

  const handleScoreAdjust = () =>
    runAction(async (authToken) => {
      const submission = await adjustSubmissionScore(
        parsedSubmissionId,
        {
          manual_total_score: Number(manualScore),
          adjustment_note: adjustmentNote.trim() || null,
        },
        authToken,
      );
      setManualScore('');
      setAdjustmentNote('');
      return `제출 #${submission.id} 점수를 ${submission.total_score}(으)로 조정했습니다.`;
    }, '점수를 조정하지 못했습니다.');

  if (isLoading && !metrics) {
    return (
      <div className="py-20 text-center animate-pulse text-slate-400 font-medium">
        채점 현황을 불러오는 중입니다...
      </div>
    );
  }

  const verdictEntries = Object.entries(metrics?.verdict_counts ?? {});

  return (
    <div className="space-y-8">
      <section className="card-simple">
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-2">
              <Gauge size={16} className="text-accent" />
              채점 큐 현황
            </h2>
            <p className="text-slate-500 text-sm font-medium leading-relaxed">
              채점 작업 큐와 워커 상태를 확인하고, 지연된 제출물을 직접 처리합니다.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => void loadAll()}
              disabled={isWorking}
              className="btn-outline text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
            >
              <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
              새로고침
            </button>
            <button
              onClick={() => void handleProcessNext()}
              disabled={isWorking}
              className="btn-flat text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
            >
              <PlayCircle size={14} />
              대기 1건 처리
            </button>
          </div>
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

        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          {[
            { label: '대기 작업', value: `${metrics?.queued_jobs ?? 0}건`, icon: ListChecks },
            { label: '진행 중', value: `${metrics?.running_jobs ?? 0}건`, icon: Activity },
            { label: '실패', value: `${metrics?.failed_jobs ?? 0}건`, icon: AlertOctagon },
            { label: '데드레터', value: `${metrics?.dead_letter_jobs ?? 0}건`, icon: AlertOctagon },
            {
              label: '평균 대기',
              value: `${Math.round((metrics?.average_queue_wait_ms ?? 0) / 100) / 10}초`,
              icon: Timer,
            },
            {
              label: '워커 온라인',
              value: `${metrics?.workers_online ?? 0} / ${
                (metrics?.workers_online ?? 0) + (metrics?.workers_offline ?? 0)
              }`,
              icon: Cpu,
            },
          ].map((stat) => (
            <div key={stat.label} className="card-simple flex flex-col justify-between py-4 px-5">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 flex items-center justify-between">
                {stat.label}
                <stat.icon size={12} className="opacity-50" />
              </span>
              <span className="text-2xl font-black text-slate-900 dark:text-white mt-2">
                {stat.value}
              </span>
            </div>
          ))}
        </div>

        {verdictEntries.length > 0 && (
          <div className="mt-6">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-3">
              판정 분포
            </h3>
            <div className="flex flex-wrap gap-2">
              {verdictEntries.map(([verdict, count]) => (
                <span
                  key={verdict}
                  className="text-[11px] font-medium px-2.5 py-1 rounded border border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50"
                >
                  {verdict}
                  <span className="ml-2 font-bold text-slate-900 dark:text-white">{count}</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </section>

      <section className="card-simple">
        <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-6">
          <Cpu size={16} className="text-accent" />
          채점 워커
        </h2>
        {workers.length === 0 ? (
          <p className="text-xs text-slate-400 italic">등록된 워커가 없습니다.</p>
        ) : (
          <div className="divide-y divide-slate-50 dark:divide-slate-900">
            {workers.map((worker) => (
              <div
                key={worker.worker_id}
                className="py-4 first:pt-0 last:pb-0 grid grid-cols-1 md:grid-cols-4 gap-4 items-center"
              >
                <div className="min-w-0">
                  <p className="text-sm font-bold text-slate-900 dark:text-white truncate">
                    {worker.worker_id}
                  </p>
                  <p className={`text-[11px] font-bold ${statusTone(worker.status)}`}>
                    {worker.status}
                  </p>
                </div>
                <div className="flex flex-col">
                  <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter">
                    동시 처리 / 현재 작업
                  </span>
                  <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
                    {worker.concurrency} / {worker.current_job_id ?? '-'}
                  </span>
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter">
                    마지막 하트비트
                  </span>
                  <span className="text-xs font-medium text-slate-600 dark:text-slate-400 truncate">
                    {formatTime(worker.heartbeat_at)}
                  </span>
                </div>
                <div className="flex items-center gap-2 md:justify-end">
                  {WORKER_ACTIONS.map((item) => (
                    <button
                      key={item.action}
                      onClick={() => void handleWorkerAction(worker.worker_id, item.action)}
                      disabled={isWorking}
                      className="btn-outline text-[11px] h-8 px-3 disabled:opacity-50"
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
                {worker.last_error && (
                  <p className="md:col-span-4 text-[11px] text-rose-600 dark:text-rose-400 font-medium">
                    최근 오류: {worker.last_error}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <section className="card-simple">
          <header className="flex items-center justify-between gap-4 mb-6">
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2">
              <ListChecks size={16} className="text-accent" />
              채점 작업
            </h2>
            <select
              value={statusFilter}
              onChange={(event) => {
                setStatusFilter(event.target.value);
                void loadAll(event.target.value);
              }}
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
            >
              {JOB_STATUS_FILTERS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </header>
          <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
            {jobs.length === 0 ? (
              <p className="text-xs text-slate-400 italic">해당 조건의 작업이 없습니다.</p>
            ) : (
              jobs.map((job) => (
                <button
                  key={job.id}
                  onClick={() =>
                    job.submission_id && setSubmissionId(String(job.submission_id))
                  }
                  className="w-full text-left p-3 rounded border border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900 transition-all"
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300">
                      #{job.id} · {job.job_type}
                    </span>
                    <span className={`text-[10px] font-black uppercase ${statusTone(job.status)}`}>
                      {job.status}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-slate-400 font-medium">
                    <span>
                      제출 {job.submission_id ?? '-'} · 시도 {job.attempt_count}/{job.max_attempts}
                    </span>
                    <span>{formatTime(job.created_at)}</span>
                  </div>
                </button>
              ))
            )}
          </div>
        </section>

        <section className="card-simple">
          <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-6">
            <AlertOctagon size={16} className="text-rose-500" />
            채점 인시던트
          </h2>
          <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
            {incidents.length === 0 ? (
              <p className="text-xs text-slate-400 italic">기록된 인시던트가 없습니다.</p>
            ) : (
              incidents.map((job) => (
                <button
                  key={job.id}
                  onClick={() =>
                    job.submission_id && setSubmissionId(String(job.submission_id))
                  }
                  className="w-full text-left p-3 rounded border border-rose-100 dark:border-rose-950/40 bg-rose-50/40 dark:bg-rose-950/10 hover:bg-rose-50 dark:hover:bg-rose-950/20 transition-all"
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300">
                      #{job.id} · 제출 {job.submission_id ?? '-'}
                    </span>
                    <span className={`text-[10px] font-black uppercase ${statusTone(job.status)}`}>
                      {job.status}
                    </span>
                  </div>
                  <p className="text-[11px] text-rose-600 dark:text-rose-400 font-medium line-clamp-2">
                    {job.error_message ?? '오류 메시지가 없습니다.'}
                  </p>
                </button>
              ))
            )}
          </div>
        </section>
      </div>

      <section className="card-simple">
        <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-2">
          <Zap size={16} className="text-accent" />
          제출물 채점 조작
        </h2>
        <p className="text-slate-500 text-sm font-medium leading-relaxed mb-6">
          위 목록에서 작업을 선택하거나 제출 번호를 직접 입력해 재채점하고, 필요한 경우 총점을 수동으로
          조정합니다. 조정 내역은 감사 로그에 남습니다.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <label className="flex flex-col gap-1.5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
              제출 번호
            </span>
            <input
              value={submissionId}
              onChange={(event) => setSubmissionId(event.target.value)}
              inputMode="numeric"
              placeholder="예: 1024"
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
              수동 총점
            </span>
            <input
              value={manualScore}
              onChange={(event) => setManualScore(event.target.value)}
              inputMode="decimal"
              placeholder="예: 85"
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
            />
          </label>
          <label className="flex flex-col gap-1.5 md:col-span-2">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
              조정 사유
            </span>
            <input
              value={adjustmentNote}
              onChange={(event) => setAdjustmentNote(event.target.value)}
              placeholder="예: 채점 기준 예외 적용"
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
            />
          </label>
        </div>

        <div className="flex flex-wrap items-center gap-3 mt-6">
          <button
            onClick={() => void handleSubmissionAction('queue')}
            disabled={isWorking || !hasSubmissionTarget}
            className="btn-outline text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
          >
            <ListChecks size={14} />큐 등록
          </button>
          <button
            onClick={() => void handleSubmissionAction('requeue')}
            disabled={isWorking || !hasSubmissionTarget}
            className="btn-outline text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
          >
            <RotateCcw size={14} />재채점 등록
          </button>
          <button
            onClick={() => void handleSubmissionAction('grade')}
            disabled={isWorking || !hasSubmissionTarget}
            className="btn-flat text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
          >
            <PlayCircle size={14} />즉시 채점
          </button>
          <button
            onClick={() => void handleScoreAdjust()}
            disabled={isWorking || !hasSubmissionTarget || manualScore.trim() === ''}
            className="btn-outline text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
          >
            <Pencil size={14} />점수 조정
          </button>
        </div>
      </section>

      <section className="card-simple">
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-6">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-1">
              <HardDrive size={16} className="text-accent" />
              아티팩트 정합성
            </h2>
            <p className="text-slate-500 text-[11px] font-medium leading-relaxed">
              제출물·테스트케이스 저장소와 DB 기록이 어긋난 경우 정합성 점검 작업을 실행합니다.
            </p>
          </div>
          <button
            onClick={() =>
              void runAction(async (authToken) => {
                const job = await createArtifactReconcileJob(authToken);
                return `정합성 점검 작업 #${job.id}을(를) 등록했습니다. (상태: ${job.status})`;
              }, '정합성 점검 작업을 등록하지 못했습니다.')
            }
            disabled={isWorking}
            className="btn-outline text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
          >
            <HardDrive size={14} />정합성 점검 실행
          </button>
        </header>

        {artifactJobs.length === 0 ? (
          <p className="text-xs text-slate-400 italic">실행된 정합성 작업이 없습니다.</p>
        ) : (
          <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
            {artifactJobs.map((job) => (
              <div
                key={job.id}
                className="flex items-center justify-between gap-3 p-3 rounded border border-slate-100 dark:border-slate-800"
              >
                <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300">
                  #{job.id} · {job.job_type}
                </span>
                <span className="flex items-center gap-4">
                  <span className="text-[10px] text-slate-400 font-medium">
                    {formatTime(job.created_at)}
                  </span>
                  <span className={`text-[10px] font-black uppercase ${statusTone(job.status)}`}>
                    {job.status}
                  </span>
                </span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
