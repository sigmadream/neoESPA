'use client';

import { useCallback, useEffect, useState } from 'react';
import { Activity, FileSearch, RefreshCw, ScrollText } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import {
  getAuditLogs,
  getSystemEvents,
  type AuditLogApi,
  type SystemEventApi,
} from '@/lib/api';

const RESULT_FILTERS = [
  { value: '', label: '전체 결과' },
  { value: 'success', label: '성공' },
  { value: 'failure', label: '실패' },
];

const EVENT_CATEGORIES = [
  { value: '', label: '전체 카테고리' },
  { value: 'grading', label: '채점' },
  { value: 'submission', label: '제출' },
  { value: 'auth', label: '인증' },
  { value: 'system', label: '시스템' },
];

function levelTone(level: string) {
  const normalized = level.toLowerCase();
  if (['error', 'critical', 'fatal'].includes(normalized)) {
    return 'text-rose-600 dark:text-rose-400';
  }
  if (normalized === 'warning' || normalized === 'warn') {
    return 'text-amber-600 dark:text-amber-400';
  }
  return 'text-slate-500 dark:text-slate-400';
}

function formatTime(value: string | null) {
  if (!value) return '-';
  const parsed = new Date(value.includes(' ') ? value.replace(' ', 'T') : value);
  return Number.isNaN(parsed.getTime()) ? '-' : parsed.toLocaleString();
}

export default function AdminAuditLogManager() {
  const { token } = useAuth();
  const [auditLogs, setAuditLogs] = useState<AuditLogApi[]>([]);
  const [events, setEvents] = useState<SystemEventApi[]>([]);
  const [selectedLog, setSelectedLog] = useState<AuditLogApi | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [eventErrorMessage, setEventErrorMessage] = useState('');

  const [actorFilter, setActorFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [resultFilter, setResultFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');

  const load = useCallback(
    async (overrides?: { result?: string; category?: string }) => {
      if (!token) return;
      setIsLoading(true);
      setErrorMessage('');
      setEventErrorMessage('');
      // 감사 로그는 audit:read, 시스템 이벤트는 observability:read 권한이 필요하다.
      // 한쪽 권한만 있는 역할도 볼 수 있는 만큼은 보이도록 개별로 처리한다.
      const [logResult, eventResult] = await Promise.allSettled([
        getAuditLogs(token, {
          actor_user_id: actorFilter,
          action_type: actionFilter,
          result: overrides?.result ?? resultFilter,
          limit: 50,
        }),
        getSystemEvents(token, {
          category: overrides?.category ?? categoryFilter,
        }),
      ]);

      if (logResult.status === 'fulfilled') {
        setAuditLogs(logResult.value);
      } else {
        setAuditLogs([]);
        setErrorMessage(
          logResult.reason instanceof Error
            ? logResult.reason.message
            : '감사 로그를 불러오지 못했습니다.',
        );
      }

      if (eventResult.status === 'fulfilled') {
        setEvents(eventResult.value);
      } else {
        setEvents([]);
        setEventErrorMessage(
          eventResult.reason instanceof Error
            ? eventResult.reason.message
            : '시스템 이벤트를 불러오지 못했습니다.',
        );
      }

      setIsLoading(false);
    },
    [actionFilter, actorFilter, categoryFilter, resultFilter, token],
  );

  useEffect(() => {
    void load();
    // 필터는 사용자가 조회 버튼을 눌렀을 때만 반영한다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  if (isLoading && auditLogs.length === 0 && events.length === 0) {
    return (
      <div className="py-20 text-center animate-pulse text-slate-400 font-medium">
        운영 로그를 불러오는 중입니다...
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <section className="card-simple">
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-2">
              <ScrollText size={16} className="text-accent" />
              감사 로그
            </h2>
            <p className="text-slate-500 text-sm font-medium leading-relaxed">
              점수 조정·재채점·권한 변경 등 운영 행위의 기록입니다. 변경 전후 값까지 확인할 수 있습니다.
            </p>
          </div>
          <button
            onClick={() => void load()}
            disabled={isLoading}
            className="btn-flat text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            조회
          </button>
        </header>

        {errorMessage && (
          <div className="p-3 rounded text-[11px] font-medium border mb-6 bg-rose-50 border-rose-100 text-rose-600 dark:bg-rose-950/20">
            {errorMessage}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <label className="flex flex-col gap-1.5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
              수행자 ID
            </span>
            <input
              value={actorFilter}
              onChange={(event) => setActorFilter(event.target.value)}
              placeholder="예: admin"
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
              행위 유형
            </span>
            <input
              value={actionFilter}
              onChange={(event) => setActionFilter(event.target.value)}
              placeholder="예: adjust_submission_score"
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
              결과
            </span>
            <select
              value={resultFilter}
              onChange={(event) => {
                setResultFilter(event.target.value);
                void load({ result: event.target.value });
              }}
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
            >
              {RESULT_FILTERS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-2 max-h-[520px] overflow-y-auto pr-1">
            {auditLogs.length === 0 ? (
              <p className="text-xs text-slate-400 italic">조건에 맞는 감사 로그가 없습니다.</p>
            ) : (
              auditLogs.map((log) => (
                <button
                  key={log.id}
                  onClick={() => setSelectedLog(log)}
                  className={`w-full text-left p-3 rounded border transition-all ${
                    selectedLog?.id === log.id
                      ? 'border-blue-500 bg-blue-50/40 dark:bg-blue-950/20'
                      : 'border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300 truncate">
                      {log.action_type}
                    </span>
                    <span
                      className={`text-[10px] font-black uppercase ${
                        log.result === 'success'
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-rose-600 dark:text-rose-400'
                      }`}
                    >
                      {log.result}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-slate-400 font-medium">
                    <span className="truncate">
                      {log.actor_user_id ?? '시스템'} → {log.target_type}
                      {log.target_id ? ` #${log.target_id}` : ''}
                    </span>
                    <span>{formatTime(log.created_at)}</span>
                  </div>
                </button>
              ))
            )}
          </div>

          <aside className="space-y-3">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2">
              <FileSearch size={12} />
              상세 내역
            </h3>
            {selectedLog ? (
              <div className="space-y-3 text-[11px]">
                {[
                  { label: '요청 ID', value: selectedLog.request_id ?? '-' },
                  { label: '연계 작업', value: selectedLog.job_id ? `#${selectedLog.job_id}` : '-' },
                ].map((item) => (
                  <div key={item.label}>
                    <p className="text-[9px] font-bold uppercase tracking-tighter text-slate-400">
                      {item.label}
                    </p>
                    <p className="font-medium text-slate-600 dark:text-slate-400 break-all">
                      {item.value}
                    </p>
                  </div>
                ))}
                {[
                  { label: '변경 전', value: selectedLog.before_json },
                  { label: '변경 후', value: selectedLog.after_json },
                  { label: '요청 내용', value: selectedLog.payload_json },
                ].map((item) => (
                  <div key={item.label}>
                    <p className="text-[9px] font-bold uppercase tracking-tighter text-slate-400 mb-1">
                      {item.label}
                    </p>
                    <pre className="rounded bg-slate-950 p-3 font-mono text-[10px] text-emerald-400/90 leading-relaxed overflow-auto max-h-40 border border-slate-800">
                      {item.value ?? '-'}
                    </pre>
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-40 flex items-center justify-center border border-dashed rounded-md bg-slate-50/30 dark:bg-slate-900/10">
                <p className="text-xs text-slate-400 font-medium">로그를 선택하십시오.</p>
              </div>
            )}
          </aside>
        </div>
      </section>

      <section className="card-simple">
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-6">
          <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2">
            <Activity size={16} className="text-accent" />
            시스템 이벤트
          </h2>
          <select
            value={categoryFilter}
            onChange={(event) => {
              setCategoryFilter(event.target.value);
              void load({ category: event.target.value });
            }}
            className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
          >
            {EVENT_CATEGORIES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </header>

        {eventErrorMessage && (
          <div className="p-3 rounded text-[11px] font-medium border mb-4 bg-rose-50 border-rose-100 text-rose-600 dark:bg-rose-950/20">
            {eventErrorMessage}
          </div>
        )}

        <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
          {events.length === 0 ? (
            <p className="text-xs text-slate-400 italic">기록된 이벤트가 없습니다.</p>
          ) : (
            events.map((event) => (
              <div
                key={event.id}
                className="p-3 rounded border border-slate-100 dark:border-slate-800"
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300">
                    {event.event_type}
                  </span>
                  <span className={`text-[10px] font-black uppercase ${levelTone(event.level)}`}>
                    {event.level}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                  {event.message}
                </p>
                <div className="flex items-center justify-between text-[10px] text-slate-400 font-medium mt-1">
                  <span className="truncate">
                    {event.category}
                    {event.submission_id ? ` · 제출 #${event.submission_id}` : ''}
                    {event.user_id ? ` · ${event.user_id}` : ''}
                  </span>
                  <span>{formatTime(event.created_at)}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}
