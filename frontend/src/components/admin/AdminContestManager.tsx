'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  BadgeCheck,
  FlaskConical,
  Megaphone,
  MessageCircleQuestion,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trophy,
} from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import { parseServerDate } from '@/lib/datetime';
import {
  answerContestClarification,
  approveContestOperation,
  attachContestProblem,
  createContest,
  createContestAnnouncement,
  enableContestSystemTesting,
  getContestClarifications,
  getContests,
  publishContest,
  type ClarificationApi,
  type ContestApi,
} from '@/lib/api';

const CONTEST_OPERATIONS = [
  { value: 'rejudge', label: '재채점' },
  { value: 'system_testing', label: '시스템 테스트' },
  { value: 'scoreboard_override', label: '스코어보드 보정' },
];

function statusTone(status: string) {
  if (status === 'published') return 'text-emerald-600 dark:text-emerald-400';
  if (status === 'draft') return 'text-amber-600 dark:text-amber-400';
  return 'text-slate-500 dark:text-slate-400';
}

function formatSchedule(value: string | null) {
  const parsed = parseServerDate(value);
  return parsed ? parsed.toLocaleString() : '-';
}

export default function AdminContestManager() {
  const { token } = useAuth();
  const [contests, setContests] = useState<ContestApi[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isWorking, setIsWorking] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const [announcementTitle, setAnnouncementTitle] = useState('');
  const [announcementMessage, setAnnouncementMessage] = useState('');
  const [clarifications, setClarifications] = useState<ClarificationApi[]>([]);
  const [clarificationFilter, setClarificationFilter] = useState<
    'all' | 'open' | 'answered'
  >('all');
  const [clarificationId, setClarificationId] = useState('');
  const [clarificationAnswer, setClarificationAnswer] = useState('');
  const [approvalOperation, setApprovalOperation] = useState(
    CONTEST_OPERATIONS[0].value,
  );
  const [approvalReason, setApprovalReason] = useState('');
  const [systemTestingApprovalId, setSystemTestingApprovalId] = useState('');
  const [problemRevisionId, setProblemRevisionId] = useState('');
  const [problemLabel, setProblemLabel] = useState('');
  const [problemPosition, setProblemPosition] = useState('');
  const [problemPoints, setProblemPoints] = useState('');

  const loadContests = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      const response = await getContests(token);
      setContests(response);
      setSelectedId((current) => current ?? response[0]?.id ?? null);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '대회 목록을 불러오지 못했습니다.',
      );
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadContests();
  }, [loadContests]);

  const loadClarifications = useCallback(
    async (contestId: number, filter: 'all' | 'open' | 'answered') => {
      if (!token) return;
      try {
        setClarifications(
          await getContestClarifications(contestId, token, filter),
        );
      } catch {
        setClarifications([]);
      }
    },
    [token],
  );

  useEffect(() => {
    if (selectedId === null) return;
    void loadClarifications(selectedId, clarificationFilter);
    // 필터 변경은 select 핸들러에서 직접 다시 불러온다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadClarifications, selectedId]);

  const runAction = async (
    action: (authToken: string, contestId: number) => Promise<string>,
    fallbackError: string,
  ) => {
    if (!token || selectedId === null) return;
    setIsWorking(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      setSuccessMessage(await action(token, selectedId));
      await loadContests();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : fallbackError);
    } finally {
      setIsWorking(false);
    }
  };

  const handleCreate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token) return;
    const data = new FormData(event.currentTarget);
    const formElement = event.currentTarget;
    setIsWorking(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      const organizations = String(data.get('allowed_organizations') ?? '')
        .split(',')
        .map((value) => value.trim())
        .filter(Boolean);
      const contest = await createContest(
        {
          code: String(data.get('code') ?? ''),
          title: String(data.get('title') ?? ''),
          starts_at: String(data.get('starts_at') ?? ''),
          ends_at: String(data.get('ends_at') ?? ''),
          freeze_at: String(data.get('freeze_at') ?? '') || null,
          access_code: String(data.get('access_code') ?? '') || null,
          visibility: String(data.get('visibility') ?? 'public'),
          scoring_format: String(data.get('scoring_format') ?? 'icpc'),
          allow_virtual: data.get('allow_virtual') === 'on',
          allowed_organizations: organizations,
        },
        token,
      );
      setSuccessMessage(`대회 #${contest.id} "${contest.title}"을(를) 만들었습니다.`);
      formElement.reset();
      setSelectedId(contest.id);
      await loadContests();
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '대회를 만들지 못했습니다.',
      );
    } finally {
      setIsWorking(false);
    }
  };

  const selectedContest = contests.find((contest) => contest.id === selectedId);

  if (isLoading && contests.length === 0) {
    return (
      <div className="py-20 text-center animate-pulse text-slate-400 font-medium">
        대회 정보를 불러오는 중입니다...
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <section className="card-simple">
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-2">
              <Trophy size={16} className="text-accent" />
              대회 운영
            </h2>
            <p className="text-slate-500 text-sm font-medium leading-relaxed">
              대회를 만들고 게시하며, 문제 연결·공지·질문 답변·운영 승인을 처리합니다.
              게시된 공개 대회는 학생의 대회 화면 목록에 바로 나타나고, 비공개 대회는 대회 번호와
              참가 코드를 전달해야 참가할 수 있습니다.
            </p>
          </div>
          <button
            onClick={() => void loadContests()}
            disabled={isWorking}
            className="btn-outline text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            새로고침
          </button>
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

        {contests.length === 0 ? (
          <p className="text-xs text-slate-400 italic">등록된 대회가 없습니다.</p>
        ) : (
          <div className="space-y-2">
            {contests.map((contest) => (
              <button
                key={contest.id}
                onClick={() => setSelectedId(contest.id)}
                className={`w-full text-left p-3 rounded border transition-all ${
                  selectedId === contest.id
                    ? 'border-blue-500 bg-blue-50/40 dark:bg-blue-950/20'
                    : 'border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
                    #{contest.id} {contest.title}
                    <span className="ml-2 text-[10px] font-mono text-slate-400">
                      {contest.code}
                    </span>
                  </span>
                  <span className={`text-[10px] font-black uppercase ${statusTone(contest.status)}`}>
                    {contest.status}
                    {contest.system_testing && ' · SYSTEM'}
                  </span>
                </div>
                <p className="text-[10px] text-slate-400 font-medium">
                  {formatSchedule(contest.starts_at)} ~ {formatSchedule(contest.ends_at)} ·{' '}
                  {contest.scoring_format} · {contest.visibility}
                  {contest.allow_virtual ? ' · 가상 참가 허용' : ''}
                </p>
              </button>
            ))}
          </div>
        )}
      </section>

      <section className="card-simple">
        <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-6">
          <Plus size={16} />새 대회 만들기
        </h2>
        <form onSubmit={(event) => void handleCreate(event)} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">대회 코드</span>
              <input name="code" required placeholder="2026-spring-1" className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none font-mono" />
            </label>
            <label className="flex flex-col gap-1.5 md:col-span-2">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">대회 제목</span>
              <input name="title" required placeholder="1학기 프로그래밍 경진대회" className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none" />
            </label>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { name: 'starts_at', label: '시작 일시', required: true },
              { name: 'ends_at', label: '종료 일시', required: true },
              { name: 'freeze_at', label: '스코어보드 프리즈', required: false },
            ].map((field) => (
              <label key={field.name} className="flex flex-col gap-1.5">
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">{field.label}</span>
                <input
                  name={field.name}
                  required={field.required}
                  placeholder="YYYY-MM-DD HH:MM:SS"
                  className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
                />
              </label>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">공개 범위</span>
              <select name="visibility" className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none">
                <option value="public">공개</option>
                <option value="private">비공개</option>
              </select>
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">채점 방식</span>
              <select name="scoring_format" className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none">
                <option value="icpc">ICPC</option>
                <option value="ioi">IOI</option>
              </select>
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">참가 코드</span>
              <input name="access_code" placeholder="비공개 대회용" className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none" />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">허용 조직 (쉼표)</span>
              <input name="allowed_organizations" placeholder="비우면 전체 허용" className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none" />
            </label>
          </div>

          <label className="flex items-center gap-2 text-xs font-medium cursor-pointer">
            <input type="checkbox" name="allow_virtual" className="rounded border-slate-300 text-accent focus:ring-accent" />
            <span className="text-slate-600 dark:text-slate-400">가상 참가 허용</span>
          </label>

          <button type="submit" disabled={isWorking} className="btn-flat h-10 px-6 text-xs flex items-center gap-2 disabled:opacity-50">
            <Plus size={14} />대회 생성
          </button>
        </form>
      </section>

      {selectedContest && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <section className="card-simple">
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-2">
              <BadgeCheck size={16} className="text-accent" />
              대회 #{selectedContest.id} 상태 전환
            </h2>
            <p className="text-slate-500 text-[11px] font-medium leading-relaxed mb-4">
              백엔드가 요구하는 순서가 있습니다.
            </p>
            <ol className="text-[11px] text-slate-500 leading-relaxed mb-6 space-y-1 list-decimal list-inside">
              <li>문제를 1개 이상 연결합니다. (연결 전에는 게시가 거부됩니다)</li>
              <li>게시하면 학생이 참가할 수 있습니다.</li>
              <li>
                시스템 테스트는 <span className="font-bold">system_testing</span> 승인을 먼저 발급하고,
                그 승인 번호로 시작합니다. 승인은 1회만 사용됩니다.
              </li>
            </ol>
            <div className="flex flex-wrap items-end gap-3">
              <button
                onClick={() =>
                  void runAction(async (authToken, contestId) => {
                    const contest = await publishContest(contestId, authToken);
                    return `대회 #${contest.id} 상태: ${contest.status}`;
                  }, '대회를 게시하지 못했습니다.')
                }
                disabled={isWorking || selectedContest.status === 'published'}
                className="btn-flat text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
              >
                <BadgeCheck size={14} />게시하기
              </button>
              <label className="flex flex-col gap-1.5">
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                  승인 번호
                </span>
                <input
                  value={systemTestingApprovalId}
                  onChange={(event) => setSystemTestingApprovalId(event.target.value)}
                  inputMode="numeric"
                  placeholder="발급된 승인 번호"
                  className="w-36 text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
                />
              </label>
              <button
                onClick={() =>
                  void runAction(async (authToken, contestId) => {
                    const contest = await enableContestSystemTesting(
                      contestId,
                      Number(systemTestingApprovalId),
                      authToken,
                    );
                    setSystemTestingApprovalId('');
                    return `시스템 테스트: ${contest.system_testing ? '활성화' : '비활성화'}`;
                  }, '시스템 테스트를 활성화하지 못했습니다.')
                }
                disabled={
                  isWorking ||
                  selectedContest.system_testing ||
                  !systemTestingApprovalId.trim()
                }
                className="btn-outline text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
              >
                <FlaskConical size={14} />시스템 테스트 시작
              </button>
            </div>

            <div className="mt-8 pt-6 border-t border-slate-100 dark:border-slate-800">
              <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-3 flex items-center gap-2">
                <ShieldCheck size={12} />
                운영 승인 발급
              </h3>
              <p className="text-[11px] text-slate-500 leading-relaxed mb-3">
                재채점처럼 결과를 바꾸는 작업은 사유가 기록된 승인 토큰이 필요합니다.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <select
                  value={approvalOperation}
                  onChange={(event) => setApprovalOperation(event.target.value)}
                  className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
                >
                  {CONTEST_OPERATIONS.map((operation) => (
                    <option key={operation.value} value={operation.value}>
                      {operation.label}
                    </option>
                  ))}
                </select>
                <input
                  value={approvalReason}
                  onChange={(event) => setApprovalReason(event.target.value)}
                  placeholder="승인 사유"
                  className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
                />
              </div>
              <button
                onClick={() =>
                  void runAction(async (authToken, contestId) => {
                    const approval = await approveContestOperation(
                      contestId,
                      { operation: approvalOperation, reason: approvalReason.trim() },
                      authToken,
                    );
                    setApprovalReason('');
                    // 발급 직후 시스템 테스트에 바로 쓸 수 있도록 승인 번호를 채워둔다.
                    if (approval.operation === 'system_testing') {
                      setSystemTestingApprovalId(String(approval.id));
                    }
                    return `승인 #${approval.id} (${approval.operation})을(를) 발급했습니다.`;
                  }, '운영 승인을 발급하지 못했습니다.')
                }
                disabled={isWorking || !approvalReason.trim()}
                className="btn-outline text-xs h-9 px-4 mt-3 flex items-center gap-2 disabled:opacity-50"
              >
                <ShieldCheck size={14} />승인 발급
              </button>
            </div>
          </section>

          <section className="card-simple">
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-6">
              <Plus size={16} />
              문제 연결
            </h2>
            <p className="text-slate-500 text-[11px] font-medium leading-relaxed mb-4">
              게시된 문제 revision 번호를 대회 문제로 연결합니다.
            </p>
            <div className="grid grid-cols-2 gap-3">
              {[
                { value: problemRevisionId, setter: setProblemRevisionId, label: 'Revision 번호', placeholder: '예: 12' },
                { value: problemLabel, setter: setProblemLabel, label: '문제 라벨', placeholder: '예: A' },
                { value: problemPosition, setter: setProblemPosition, label: '순서', placeholder: '예: 1' },
                { value: problemPoints, setter: setProblemPoints, label: '배점', placeholder: '예: 100' },
              ].map((field) => (
                <label key={field.label} className="flex flex-col gap-1.5">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                    {field.label}
                  </span>
                  <input
                    value={field.value}
                    onChange={(event) => field.setter(event.target.value)}
                    placeholder={field.placeholder}
                    className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
                  />
                </label>
              ))}
            </div>
            <button
              onClick={() =>
                void runAction(async (authToken, contestId) => {
                  const problem = await attachContestProblem(
                    contestId,
                    {
                      revision_id: Number(problemRevisionId),
                      label: problemLabel.trim(),
                      position: Number(problemPosition),
                      points: problemPoints ? Number(problemPoints) : undefined,
                    },
                    authToken,
                  );
                  setProblemRevisionId('');
                  setProblemLabel('');
                  setProblemPosition('');
                  setProblemPoints('');
                  return `문제 ${problem.label}을(를) 연결했습니다.`;
                }, '문제를 연결하지 못했습니다.')
              }
              disabled={
                isWorking ||
                !problemRevisionId.trim() ||
                !problemLabel.trim() ||
                !problemPosition.trim()
              }
              className="btn-flat text-xs h-9 px-4 mt-4 flex items-center gap-2 disabled:opacity-50"
            >
              <Plus size={14} />문제 연결
            </button>
          </section>

          <section className="card-simple">
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-6">
              <Megaphone size={16} />
              대회 공지 발행
            </h2>
            <div className="space-y-3">
              <input
                value={announcementTitle}
                onChange={(event) => setAnnouncementTitle(event.target.value)}
                placeholder="공지 제목"
                className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
              />
              <textarea
                value={announcementMessage}
                onChange={(event) => setAnnouncementMessage(event.target.value)}
                rows={4}
                placeholder="참가자 전체에게 전달할 내용"
                className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none resize-none"
              />
            </div>
            <button
              onClick={() =>
                void runAction(async (authToken, contestId) => {
                  const announcement = await createContestAnnouncement(
                    contestId,
                    {
                      title: announcementTitle.trim(),
                      message: announcementMessage.trim(),
                    },
                    authToken,
                  );
                  setAnnouncementTitle('');
                  setAnnouncementMessage('');
                  return `공지 "${announcement.title}"을(를) 발행했습니다.`;
                }, '공지를 발행하지 못했습니다.')
              }
              disabled={isWorking || !announcementTitle.trim() || !announcementMessage.trim()}
              className="btn-flat text-xs h-9 px-4 mt-4 flex items-center gap-2 disabled:opacity-50"
            >
              <Megaphone size={14} />공지 발행
            </button>
          </section>

          <section className="card-simple">
            <header className="flex items-center justify-between gap-4 mb-4">
              <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2">
                <MessageCircleQuestion size={16} />
                질문 답변
              </h2>
              <select
                value={clarificationFilter}
                onChange={(event) => {
                  const next = event.target.value as 'all' | 'open' | 'answered';
                  setClarificationFilter(next);
                  void loadClarifications(selectedContest.id, next);
                }}
                className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
              >
                <option value="all">전체</option>
                <option value="open">미답변</option>
                <option value="answered">답변 완료</option>
              </select>
            </header>

            {clarifications.length === 0 ? (
              <p className="text-xs text-slate-400 italic">해당 조건의 질문이 없습니다.</p>
            ) : (
              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {clarifications.map((clarification) => (
                  <button
                    key={clarification.id}
                    onClick={() => {
                      setClarificationId(String(clarification.id));
                      setClarificationAnswer(clarification.answer ?? '');
                    }}
                    className={`w-full text-left p-3 rounded border transition-all ${
                      clarificationId === String(clarification.id)
                        ? 'border-blue-500 bg-blue-50/40 dark:bg-blue-950/20'
                        : 'border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300">
                        #{clarification.id} · {clarification.user_id}
                      </span>
                      <span
                        className={`text-[10px] font-black uppercase ${
                          clarification.answer
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-amber-600 dark:text-amber-400'
                        }`}
                      >
                        {clarification.answer ? '답변 완료' : '미답변'}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed line-clamp-2">
                      {clarification.question}
                    </p>
                  </button>
                ))}
              </div>
            )}

            <div className="mt-4 space-y-3">
              <textarea
                value={clarificationAnswer}
                onChange={(event) => setClarificationAnswer(event.target.value)}
                rows={4}
                placeholder={
                  clarificationId
                    ? `질문 #${clarificationId}에 대한 답변`
                    : '위에서 질문을 선택하십시오.'
                }
                className="block w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none resize-none"
              />
            </div>
            <button
              onClick={() =>
                void runAction(async (authToken, contestId) => {
                  const clarification = await answerContestClarification(
                    contestId,
                    Number(clarificationId),
                    clarificationAnswer.trim(),
                    authToken,
                  );
                  setClarificationId('');
                  setClarificationAnswer('');
                  await loadClarifications(contestId, clarificationFilter);
                  return `질문 #${clarification.id}에 답변했습니다.`;
                }, '답변을 등록하지 못했습니다.')
              }
              disabled={isWorking || !clarificationId.trim() || !clarificationAnswer.trim()}
              className="btn-flat text-xs h-9 px-4 mt-4 flex items-center gap-2 disabled:opacity-50"
            >
              <MessageCircleQuestion size={14} />답변 등록
            </button>
          </section>
        </div>
      )}
    </div>
  );
}
