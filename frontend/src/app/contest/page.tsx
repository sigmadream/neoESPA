'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  Trophy,
  Megaphone,
  MessageCircleQuestion,
  RefreshCw,
  LogIn,
  Send,
  ListOrdered,
} from 'lucide-react';

import AuthGate from '@/components/AuthGate';
import { useAuth } from '@/components/AuthProvider';
import { parseServerDate } from '@/lib/datetime';
import {
  askContestClarification,
  getContestAnnouncements,
  getContestScoreboard,
  getMyContestClarifications,
  getOpenContests,
  joinContest,
  type ClarificationApi,
  type ContestAnnouncementApi,
  type ContestApi,
  type ContestScoreboardRowApi,
} from '@/lib/api';

const SCOREBOARD_PHASES = [
  { value: 'current' as const, label: '현재' },
  { value: 'live' as const, label: '대회 중 기록' },
  { value: 'system' as const, label: '시스템 테스트 반영' },
];

function formatSchedule(value: string | null) {
  const parsed = parseServerDate(value);
  return parsed ? parsed.toLocaleString() : '-';
}

function ContestPageContent() {
  const { token, user } = useAuth();
  const [contests, setContests] = useState<ContestApi[]>([]);
  const [contestId, setContestId] = useState('');
  const [accessCode, setAccessCode] = useState('');
  const [participationType, setParticipationType] =
    useState<'official' | 'virtual'>('official');

  const [joinedContestId, setJoinedContestId] = useState<number | null>(null);
  const [scoreboard, setScoreboard] = useState<ContestScoreboardRowApi[]>([]);
  const [announcements, setAnnouncements] = useState<ContestAnnouncementApi[]>([]);
  const [clarifications, setClarifications] = useState<ClarificationApi[]>([]);
  const [phase, setPhase] = useState<'current' | 'live' | 'system'>('current');
  const [question, setQuestion] = useState('');

  const [isJoining, setIsJoining] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const loadContests = useCallback(async () => {
    if (!token) return;
    try {
      setContests(await getOpenContests(token));
    } catch {
      // 목록 조회에 실패해도 대회 번호로 직접 참가할 수 있게 둔다.
    }
  }, [token]);

  useEffect(() => {
    void loadContests();
  }, [loadContests]);

  const loadContestView = useCallback(
    async (targetId: number, targetPhase: 'current' | 'live' | 'system') => {
      if (!token) return;
      setIsLoading(true);
      setErrorMessage('');
      const [scoreRes, noticeRes, clarifyRes] = await Promise.allSettled([
        getContestScoreboard(targetId, token, targetPhase),
        getContestAnnouncements(targetId, token),
        getMyContestClarifications(targetId, token),
      ]);

      if (scoreRes.status === 'fulfilled') {
        setScoreboard(scoreRes.value);
      } else {
        setScoreboard([]);
        setErrorMessage(
          scoreRes.reason instanceof Error
            ? scoreRes.reason.message
            : '스코어보드를 불러오지 못했습니다.',
        );
      }
      if (noticeRes.status === 'fulfilled') setAnnouncements(noticeRes.value);
      if (clarifyRes.status === 'fulfilled') setClarifications(clarifyRes.value);
      setIsLoading(false);
    },
    [token],
  );

  const handleJoin = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!token) return;
    const targetId = Number(contestId);
    if (!Number.isInteger(targetId) || targetId <= 0) {
      setErrorMessage('대회 번호를 정확히 입력하십시오.');
      return;
    }
    setIsJoining(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      await joinContest(
        targetId,
        {
          participation_type: participationType,
          access_code: accessCode.trim() || null,
        },
        token,
      );
      setSuccessMessage('대회에 참가했습니다.');
      setJoinedContestId(targetId);
      await Promise.all([loadContestView(targetId, phase), loadContests()]);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : '대회에 참가하지 못했습니다.';
      // 이미 참가한 대회는 그대로 대회 화면을 연다.
      if (message.includes('already exists')) {
        setJoinedContestId(targetId);
        setSuccessMessage('이미 참가한 대회입니다.');
        await loadContestView(targetId, phase);
      } else {
        setErrorMessage(message);
      }
    } finally {
      setIsJoining(false);
    }
  };

  const handleAskQuestion = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!token || joinedContestId === null || !question.trim()) return;
    setErrorMessage('');
    try {
      await askContestClarification(
        joinedContestId,
        { question: question.trim() },
        token,
      );
      setQuestion('');
      setSuccessMessage('질문을 등록했습니다. 운영진 답변을 기다려 주세요.');
      setClarifications(
        await getMyContestClarifications(joinedContestId, token),
      );
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '질문을 등록하지 못했습니다.',
      );
    }
  };

  const activeContest = contests.find(
    (contest) => contest.id === joinedContestId,
  );

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 space-y-10">
      <header>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
          <Trophy className="text-accent" size={24} />
          대회
        </h1>
        <p className="text-slate-500 text-sm font-medium">
          대회에 참가하고 스코어보드·공지·질문을 확인합니다.
        </p>
      </header>

      {(errorMessage || successMessage) && (
        <div
          className={`p-3 rounded text-[11px] font-medium border ${
            errorMessage
              ? 'bg-rose-50 border-rose-100 text-rose-600 dark:bg-rose-950/20'
              : 'bg-emerald-50 border-emerald-100 text-emerald-600 dark:bg-emerald-950/20'
          }`}
        >
          {errorMessage || successMessage}
        </div>
      )}

      <section className="card-simple">
        <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-6">
          <LogIn size={14} />
          대회 참가
        </h2>

        <div className="mb-6">
          <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
            참가 가능한 대회
          </span>
          {contests.length === 0 ? (
            <p className="text-[11px] text-slate-400 italic mt-2">
              현재 공개된 대회가 없습니다. 비공개 대회는 아래에 대회 번호와 참가 코드를 입력해
              참가하십시오.
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
              {contests.map((contest) => (
                <button
                  key={contest.id}
                  onClick={() => setContestId(String(contest.id))}
                  className={`text-left p-3 rounded border transition-all ${
                    contestId === String(contest.id)
                      ? 'border-blue-500 bg-blue-50/40 dark:bg-blue-950/20'
                      : 'border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate">
                      #{contest.id} {contest.title}
                    </span>
                    <span className="text-[10px] font-black uppercase text-emerald-600 dark:text-emerald-400">
                      {contest.scoring_format}
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-400 font-medium">
                    {formatSchedule(contest.starts_at)} ~ {formatSchedule(contest.ends_at)}
                    {contest.allow_virtual ? ' · 가상 참가 가능' : ''}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>

        <form
          onSubmit={(event) => void handleJoin(event)}
          className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end"
        >
          <label className="flex flex-col gap-1.5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
              대회 번호
            </span>
            <input
              value={contestId}
              onChange={(event) => setContestId(event.target.value)}
              inputMode="numeric"
              required
              placeholder="예: 1"
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent"
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
              참가 코드 (있는 경우)
            </span>
            <input
              value={accessCode}
              onChange={(event) => setAccessCode(event.target.value)}
              placeholder="비공개 대회만 필요"
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent"
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
              참가 유형
            </span>
            <select
              value={participationType}
              onChange={(event) =>
                setParticipationType(event.target.value as 'official' | 'virtual')
              }
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
            >
              <option value="official">공식 참가</option>
              <option value="virtual">가상 참가</option>
            </select>
          </label>
          <button
            type="submit"
            disabled={isJoining}
            className="btn-flat text-xs h-10 px-4 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <LogIn size={14} />
            참가하기
          </button>
        </form>
      </section>

      {joinedContestId !== null && (
        <>
          <section className="card-simple">
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
              <div>
                <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-1">
                  <ListOrdered size={14} />
                  스코어보드 · 대회 #{joinedContestId}
                </h2>
                {activeContest && (
                  <p className="text-[11px] text-slate-500 font-medium">
                    {activeContest.title} · {formatSchedule(activeContest.starts_at)} ~{' '}
                    {formatSchedule(activeContest.ends_at)}
                    {activeContest.freeze_at
                      ? ` · 프리즈 ${formatSchedule(activeContest.freeze_at)}`
                      : ''}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                <select
                  value={phase}
                  onChange={(event) => {
                    const next = event.target.value as 'current' | 'live' | 'system';
                    setPhase(next);
                    void loadContestView(joinedContestId, next);
                  }}
                  className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
                >
                  {SCOREBOARD_PHASES.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => void loadContestView(joinedContestId, phase)}
                  disabled={isLoading}
                  className="btn-outline text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
                >
                  <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
                  새로고침
                </button>
              </div>
            </header>

            {scoreboard.length === 0 ? (
              <p className="text-xs text-slate-400 italic">
                아직 집계된 결과가 없습니다.
              </p>
            ) : (
              <div className="divide-y divide-slate-50 dark:divide-slate-900">
                {scoreboard.map((row) => (
                  <div
                    key={`${row.rank}-${row.user_id}`}
                    className={`py-3 first:pt-0 last:pb-0 grid grid-cols-4 gap-4 items-center ${
                      row.user_id === user?.id
                        ? 'bg-blue-50/40 dark:bg-blue-950/10 rounded px-2'
                        : ''
                    }`}
                  >
                    <span className="text-sm font-black text-slate-900 dark:text-white">
                      {row.rank}위
                    </span>
                    <span className="text-xs font-bold text-slate-700 dark:text-slate-300 truncate">
                      {row.user_id}
                      {row.user_id === user?.id && (
                        <span className="ml-2 text-[10px] text-accent">나</span>
                      )}
                    </span>
                    <span className="text-xs font-medium text-slate-600 dark:text-slate-400">
                      {row.solved}문제 · {row.score}점
                    </span>
                    <span className="text-xs font-medium text-slate-500 text-right">
                      페널티 {row.penalty_minutes}분
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <section className="card-simple">
              <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-6">
                <Megaphone size={14} />
                대회 공지
              </h2>
              {announcements.length === 0 ? (
                <p className="text-xs text-slate-400 italic">등록된 공지가 없습니다.</p>
              ) : (
                <div className="space-y-3">
                  {announcements.map((announcement) => (
                    <div
                      key={announcement.id}
                      className="p-3 rounded border border-slate-100 dark:border-slate-800"
                    >
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
                          {announcement.title}
                        </span>
                        <span className="text-[10px] text-slate-400">
                          {formatSchedule(announcement.created_at)}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 leading-relaxed whitespace-pre-line">
                        {announcement.message}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="card-simple">
              <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-6">
                <MessageCircleQuestion size={14} />
                내 질문 (Clarification)
              </h2>

              <form
                onSubmit={(event) => void handleAskQuestion(event)}
                className="flex items-end gap-3 mb-6"
              >
                <label className="flex flex-col gap-1.5 flex-1">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                    질문 내용
                  </span>
                  <input
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    placeholder="문제 조건에 대해 궁금한 점을 남기세요."
                    className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent"
                  />
                </label>
                <button
                  type="submit"
                  disabled={!question.trim()}
                  className="btn-flat text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
                >
                  <Send size={14} />
                  등록
                </button>
              </form>

              {clarifications.length === 0 ? (
                <p className="text-xs text-slate-400 italic">등록한 질문이 없습니다.</p>
              ) : (
                <div className="space-y-3">
                  {clarifications.map((clarification) => (
                    <div
                      key={clarification.id}
                      className="p-3 rounded border border-slate-100 dark:border-slate-800"
                    >
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
                          #{clarification.id}
                        </span>
                        <span
                          className={`text-[10px] font-black uppercase ${
                            clarification.answer
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-amber-600 dark:text-amber-400'
                          }`}
                        >
                          {clarification.answer ? '답변 완료' : clarification.status}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed">
                        {clarification.question}
                      </p>
                      {clarification.answer && (
                        <p className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] text-emerald-700 dark:text-emerald-400 leading-relaxed">
                          {clarification.answer}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
}

export default function ContestPage() {
  return (
    <AuthGate>
      <ContestPageContent />
    </AuthGate>
  );
}
