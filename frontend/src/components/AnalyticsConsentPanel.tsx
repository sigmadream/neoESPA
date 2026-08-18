'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { CheckCircle2, ShieldQuestion, XCircle } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import {
  getAnalyticsConsents,
  recordAnalyticsConsent,
  type AnalyticsConsentApi,
} from '@/lib/api';

/**
 * 백엔드 `export-analytics-jsonl` CLI 의 --purpose / --policy-version 인자와
 * 반드시 같은 값을 사용해야 동의가 내보내기에 반영된다.
 */
const CONSENT_PURPOSE = 'learning_analytics';
const CONSENT_POLICY_VERSION = 'v1';

const CONSENT_SCOPES = [
  {
    value: 'submissions',
    label: '과제 제출 기록',
    description: '제출 시각·언어·채점 결과가 통계 분석에 포함됩니다.',
  },
  {
    value: 'learning_events',
    label: '학습 활동 기록',
    description: '코드 작성·실행 등 학습 과정 이벤트가 통계 분석에 포함됩니다.',
  },
] as const;

function formatTime(value: string) {
  const parsed = new Date(value.includes(' ') ? value.replace(' ', 'T') : value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export default function AnalyticsConsentPanel() {
  const { token } = useAuth();
  const [consents, setConsents] = useState<AnalyticsConsentApi[]>([]);
  const [selectedScopes, setSelectedScopes] = useState<string[]>([
    ...CONSENT_SCOPES.map((scope) => scope.value),
  ]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const load = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      const response = await getAnalyticsConsents(token);
      setConsents(response);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '동의 내역을 불러오지 못했습니다.',
      );
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  // 목록은 최신순으로 내려오므로, 같은 목적의 첫 항목이 현재 상태다.
  const currentConsent = useMemo(
    () =>
      consents.find(
        (consent) =>
          consent.purpose === CONSENT_PURPOSE &&
          consent.policy_version === CONSENT_POLICY_VERSION,
      ) ?? null,
    [consents],
  );

  useEffect(() => {
    if (currentConsent?.granted) {
      setSelectedScopes(currentConsent.scopes);
    }
  }, [currentConsent]);

  const submitConsent = async (granted: boolean) => {
    if (!token) return;
    setIsSaving(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      await recordAnalyticsConsent(
        {
          purpose: CONSENT_PURPOSE,
          policy_version: CONSENT_POLICY_VERSION,
          scopes: granted ? selectedScopes : [],
          granted,
        },
        token,
      );
      setSuccessMessage(
        granted
          ? '분석 데이터 활용에 동의했습니다. 언제든지 철회할 수 있습니다.'
          : '동의를 철회했습니다. 이후 내보내기에서 제외됩니다.',
      );
      await load();
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '동의 처리를 완료하지 못했습니다.',
      );
    } finally {
      setIsSaving(false);
    }
  };

  const toggleScope = (scope: string) => {
    setSelectedScopes((previous) =>
      previous.includes(scope)
        ? previous.filter((value) => value !== scope)
        : [...previous, scope],
    );
  };

  return (
    <section className="card-simple">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-2">
            <ShieldQuestion size={14} />
            학습 분석 데이터 활용 동의
          </h2>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            수업 개선을 위한 통계 분석에 내 학습 기록을 사용하도록 허용할지 선택합니다. 동의하지
            않아도 수업 참여와 채점에는 아무런 영향이 없습니다.
          </p>
        </div>
        <div
          className={`shrink-0 flex items-center gap-2 text-xs font-bold px-3 py-2 rounded border ${
            currentConsent?.granted
              ? 'text-emerald-600 border-emerald-100 bg-emerald-50 dark:bg-emerald-950/20 dark:border-emerald-900/30'
              : 'text-slate-500 border-slate-100 bg-slate-50 dark:bg-slate-900/40 dark:border-slate-800'
          }`}
        >
          {currentConsent?.granted ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
          {isLoading ? '확인 중' : currentConsent?.granted ? '동의함' : '동의하지 않음'}
        </div>
      </header>

      {(errorMessage || successMessage) && (
        <div
          className={`p-3 rounded text-[11px] font-medium border mb-6 ${
            errorMessage
              ? 'bg-rose-50 border-rose-100 text-rose-600 dark:bg-rose-950/20 dark:border-rose-900/30 dark:text-rose-400'
              : 'bg-emerald-50 border-emerald-100 text-emerald-600 dark:bg-emerald-950/20 dark:border-emerald-900/30 dark:text-emerald-400'
          }`}
        >
          {errorMessage || successMessage}
        </div>
      )}

      <div className="space-y-3">
        {CONSENT_SCOPES.map((scope) => (
          <label
            key={scope.value}
            className="flex items-start gap-3 p-3 rounded border border-slate-100 dark:border-slate-800 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-900/40 transition-all"
          >
            <input
              type="checkbox"
              checked={selectedScopes.includes(scope.value)}
              onChange={() => toggleScope(scope.value)}
              className="mt-0.5 rounded border-slate-300 text-accent focus:ring-accent"
            />
            <span className="min-w-0">
              <span className="block text-xs font-bold text-slate-700 dark:text-slate-200">
                {scope.label}
              </span>
              <span className="block text-[11px] text-slate-500 leading-relaxed">
                {scope.description}
              </span>
            </span>
          </label>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-3 mt-6">
        <button
          onClick={() => void submitConsent(true)}
          disabled={isSaving || isLoading || selectedScopes.length === 0}
          className="btn-flat text-xs h-10 px-4 flex items-center gap-2 disabled:opacity-50"
        >
          <CheckCircle2 size={14} />
          {currentConsent?.granted ? '동의 범위 갱신' : '동의하기'}
        </button>
        <button
          onClick={() => void submitConsent(false)}
          disabled={isSaving || isLoading || !currentConsent?.granted}
          className="btn-outline text-xs h-10 px-4 flex items-center gap-2 disabled:opacity-50"
        >
          <XCircle size={14} />
          동의 철회
        </button>
        <span className="text-[10px] text-slate-400 font-medium">
          정책 버전 {CONSENT_POLICY_VERSION} · 목적 {CONSENT_PURPOSE}
        </span>
      </div>

      {consents.length > 0 && (
        <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800">
          <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-3">
            동의 변경 이력
          </h3>
          <ul className="space-y-2">
            {consents.slice(0, 5).map((consent) => (
              <li
                key={consent.id}
                className="flex items-center justify-between gap-3 text-[11px]"
              >
                <span
                  className={`font-bold ${
                    consent.granted
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-slate-500'
                  }`}
                >
                  {consent.granted ? '동의' : '철회'}
                </span>
                <span className="text-slate-500 truncate flex-1">
                  {consent.scopes.length > 0 ? consent.scopes.join(', ') : '범위 없음'}
                </span>
                <span className="text-slate-400">{formatTime(consent.created_at)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
