'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { KeyRound, RefreshCw, Save, ShieldCheck } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import StepUpDialog from '@/components/StepUpDialog';
import {
  getRoleCapabilities,
  updateRoleCapabilities,
  KNOWN_CAPABILITIES,
  MANAGED_ROLES,
} from '@/lib/api';

/** 백엔드 require_step_up 이 돌려주는 403 메시지. */
const STEP_UP_REQUIRED = 'step-up authentication is required';

const ROLE_LABELS: Record<string, string> = {
  instructor: '교수자',
  ta: '조교',
  problem_setter: '출제자',
  reviewer: '검수자',
  judge_operator: '채점 운영자',
  support: '지원 담당',
  viewer: '열람자',
  student: '학생',
};

const CAPABILITY_LABELS: Record<string, string> = {
  'problem:create': '문제 생성',
  'problem:edit': '문제 편집',
  'problem:review': '문제 검수',
  'problem:publish': '문제 게시',
  'problem:data.read': '문제 데이터 열람',
  'submission:rejudge': '제출물 재채점',
  'judge:operate': '채점 워커 운영',
  'homework:manage': '과제 관리',
  'grading:manual': '수동 채점·점수 조정',
  'content:manage': '공지·자료 관리',
  'exam:manage': '시험 관리',
  'plagiarism:operate': '표절 검사 실행',
  'observability:read': '운영 로그 열람',
  'collaboration:manage': '협업 세션 관리',
  'audit:read': '감사 로그 열람',
  'user:manage': '사용자 관리',
};

export default function AdminRoleManager() {
  const { token } = useAuth();
  const [roleName, setRoleName] = useState<string>(MANAGED_ROLES[0]);
  const [capabilities, setCapabilities] = useState<string[]>([]);
  const [serverCapabilities, setServerCapabilities] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [isStepUpOpen, setIsStepUpOpen] = useState(false);

  const loadRole = useCallback(
    async (targetRole: string) => {
      if (!token) return;
      setIsLoading(true);
      setErrorMessage('');
      setSuccessMessage('');
      try {
        const response = await getRoleCapabilities(targetRole, token);
        setCapabilities(response.capabilities);
        setServerCapabilities(response.capabilities);
      } catch (error) {
        setErrorMessage(
          error instanceof Error ? error.message : '권한을 불러오지 못했습니다.',
        );
      } finally {
        setIsLoading(false);
      }
    },
    [token],
  );

  useEffect(() => {
    void loadRole(roleName);
  }, [loadRole, roleName]);

  // 서버가 화면에 없는 권한을 돌려주더라도 잃어버리지 않도록 함께 보여준다.
  const allCapabilities = useMemo(() => {
    const merged = new Set<string>([...KNOWN_CAPABILITIES, ...serverCapabilities]);
    return [...merged].sort();
  }, [serverCapabilities]);

  const isDirty =
    capabilities.length !== serverCapabilities.length ||
    capabilities.some((capability) => !serverCapabilities.includes(capability));

  const toggleCapability = (capability: string) => {
    setCapabilities((previous) =>
      previous.includes(capability)
        ? previous.filter((value) => value !== capability)
        : [...previous, capability],
    );
  };

  const handleSave = async () => {
    if (!token) return;
    setIsSaving(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      const response = await updateRoleCapabilities(
        roleName,
        [...capabilities].sort(),
        token,
      );
      setCapabilities(response.capabilities);
      setServerCapabilities(response.capabilities);
      setSuccessMessage(
        `${ROLE_LABELS[roleName] ?? roleName} 역할의 권한 ${response.capabilities.length}개를 저장했습니다.`,
      );
    } catch (error) {
      const message =
        error instanceof Error ? error.message : '권한을 저장하지 못했습니다.';
      // 서버가 재인증을 요구하면 재인증 후 다시 저장한다.
      if (message.toLowerCase().includes(STEP_UP_REQUIRED)) {
        setIsStepUpOpen(true);
      } else {
        setErrorMessage(message);
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-8">
      <StepUpDialog
        open={isStepUpOpen}
        onClose={() => setIsStepUpOpen(false)}
        onSuccess={() => void handleSave()}
        description="역할 권한 변경은 재인증이 필요한 작업입니다."
      />
      <section className="card-simple">
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-2">
              <ShieldCheck size={16} className="text-accent" />
              역할별 권한
            </h2>
            <p className="text-slate-500 text-sm font-medium leading-relaxed">
              역할이 수행할 수 있는 작업을 지정합니다. 저장하면 해당 역할의 모든 사용자에게 즉시
              적용됩니다. (관리자 역할은 항상 전체 권한을 가지므로 편집 대상이 아닙니다.)
            </p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={roleName}
              onChange={(event) => setRoleName(event.target.value)}
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
            >
              {MANAGED_ROLES.map((role) => (
                <option key={role} value={role}>
                  {ROLE_LABELS[role] ?? role}
                </option>
              ))}
            </select>
            <button
              onClick={() => void loadRole(roleName)}
              disabled={isLoading || isSaving}
              className="btn-outline text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
            >
              <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
              되돌리기
            </button>
            <button
              onClick={() => void handleSave()}
              disabled={isSaving || isLoading || !isDirty}
              className="btn-flat text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
            >
              <Save size={14} />
              저장
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

        {isLoading ? (
          <div className="py-16 text-center animate-pulse text-slate-400 font-medium">
            권한을 불러오는 중입니다...
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {allCapabilities.map((capability) => {
              const isChecked = capabilities.includes(capability);
              return (
                <label
                  key={capability}
                  className={`flex items-start gap-3 p-3 rounded border cursor-pointer transition-all ${
                    isChecked
                      ? 'border-blue-500 bg-blue-50/40 dark:bg-blue-950/20'
                      : 'border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => toggleCapability(capability)}
                    className="mt-0.5 accent-blue-600"
                  />
                  <span className="min-w-0">
                    <span className="block text-xs font-bold text-slate-700 dark:text-slate-300">
                      {CAPABILITY_LABELS[capability] ?? capability}
                    </span>
                    <span className="block text-[10px] font-mono text-slate-400 truncate">
                      {capability}
                    </span>
                  </span>
                </label>
              );
            })}
          </div>
        )}

        <p className="mt-6 text-[11px] text-slate-400 font-medium flex items-center gap-2">
          <KeyRound size={12} />
          선택된 권한 {capabilities.length}개
          {isDirty && <span className="text-amber-600 dark:text-amber-400">· 저장되지 않은 변경 있음</span>}
        </p>
      </section>
    </div>
  );
}
