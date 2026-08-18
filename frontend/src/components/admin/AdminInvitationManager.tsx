'use client';

import { useCallback, useEffect, useState } from 'react';
import { Copy, MailPlus, ShieldAlert, ShieldCheck } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import StepUpDialog from '@/components/StepUpDialog';
import {
  ADMIN_INVITABLE_ROLES,
  createAdminInvitation,
  getAuthAssurance,
  type AdminInvitationIssuedApi,
  type AuthAssuranceApi,
} from '@/lib/api';

const INVITABLE_ROLES = ADMIN_INVITABLE_ROLES;

function formatTime(value: string) {
  const parsed = new Date(value.includes(' ') ? value.replace(' ', 'T') : value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export default function AdminInvitationManager() {
  const { token } = useAuth();
  const [assurance, setAssurance] = useState<AuthAssuranceApi | null>(null);
  const [issued, setIssued] = useState<AdminInvitationIssuedApi | null>(null);
  const [email, setEmail] = useState('');
  const [roleName, setRoleName] = useState<string>(INVITABLE_ROLES[0]);
  const [ttlMinutes, setTtlMinutes] = useState('1440');
  const [isWorking, setIsWorking] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [isStepUpOpen, setIsStepUpOpen] = useState(false);

  const loadAssurance = useCallback(async () => {
    if (!token) return;
    try {
      setAssurance(await getAuthAssurance(token));
    } catch {
      setAssurance(null);
    }
  }, [token]);

  useEffect(() => {
    void loadAssurance();
  }, [loadAssurance]);

  const issueInvitation = useCallback(async (tokenOverride?: string) => {
    const requestToken = tokenOverride ?? token;
    if (!requestToken) return;
    setIsWorking(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      const invitation = await createAdminInvitation(
        {
          email: email.trim(),
          role_name: roleName,
          ttl_minutes: Number(ttlMinutes) || 1440,
        },
        requestToken,
      );
      setIssued(invitation);
      setSuccessMessage(
        `${invitation.email} 앞으로 ${invitation.role_name} 초대를 발급했습니다.`,
      );
    } catch (error) {
      const message =
        error instanceof Error ? error.message : '초대를 발급하지 못했습니다.';
      // 서버가 재인증을 요구하면 재인증 창을 연다.
      if (message.toLowerCase().includes('step-up authentication is required')) {
        setIsStepUpOpen(true);
      } else {
        setErrorMessage(message);
      }
    } finally {
      setIsWorking(false);
    }
  }, [email, roleName, token, ttlMinutes]);

  const handleCopy = async (value: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setSuccessMessage('클립보드에 복사했습니다.');
    } catch {
      setErrorMessage('클립보드 복사를 사용할 수 없습니다. 직접 선택해 복사하십시오.');
    }
  };

  return (
    <div className="space-y-8">
      <StepUpDialog
        open={isStepUpOpen}
        onClose={() => setIsStepUpOpen(false)}
        onSuccess={(elevatedToken) => void issueInvitation(elevatedToken)}
        description="관리자 초대 발급은 재인증이 필요한 작업입니다."
      />

      <section className="card-simple">
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-2">
              <MailPlus size={16} className="text-accent" />
              관리자·조교 초대
            </h2>
            <p className="text-slate-500 text-sm font-medium leading-relaxed">
              역할을 지정해 일회성 초대 토큰을 발급합니다. 초대받은 사람은
              <span className="font-mono text-[11px] mx-1">/admin-invite</span>
              에서 토큰으로 계정을 만듭니다. 교수자·조교 역할은 초대 대상이 아니며, 계정 생성 후
              사용자 관리에서 역할을 변경해 부여합니다.
            </p>
          </div>
          {assurance && (
            <div
              className={`shrink-0 flex items-center gap-2 text-[11px] font-bold px-3 py-2 rounded border ${
                assurance.mfa_required
                  ? 'text-amber-600 border-amber-100 bg-amber-50 dark:bg-amber-950/20'
                  : 'text-slate-500 border-slate-100 bg-slate-50 dark:bg-slate-900/40 dark:border-slate-800'
              }`}
            >
              {assurance.mfa_required ? <ShieldAlert size={14} /> : <ShieldCheck size={14} />}
              재인증 {assurance.mfa_required ? '필요' : '불필요'}
              {assurance.mfa_method ? ` · ${assurance.mfa_method}` : ''}
            </div>
          )}
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

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
          <label className="flex flex-col gap-1.5 md:col-span-2">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
              초대할 이메일
            </span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="ta@pusan.ac.kr"
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent"
            />
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
              부여할 역할
            </span>
            <select
              value={roleName}
              onChange={(event) => setRoleName(event.target.value)}
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
            >
              {INVITABLE_ROLES.map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1.5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
              유효 시간(분)
            </span>
            <input
              value={ttlMinutes}
              onChange={(event) => setTtlMinutes(event.target.value)}
              inputMode="numeric"
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
            />
          </label>
        </div>

        <button
          onClick={() => void issueInvitation()}
          disabled={isWorking || !email.trim()}
          className="btn-flat text-xs h-10 px-4 mt-6 flex items-center gap-2 disabled:opacity-50"
        >
          <MailPlus size={14} />초대 발급
        </button>

        {issued && (
          <div className="mt-6 p-4 rounded border border-blue-100 dark:border-blue-950/40 bg-blue-50/40 dark:bg-blue-950/10">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
              발급된 초대 토큰
            </h3>
            <p className="text-[11px] text-slate-500 leading-relaxed mb-3">
              토큰은 지금 한 번만 표시됩니다. {formatTime(issued.expires_at)}까지 유효하며,
              초대받은 사람에게 안전한 경로로 전달하십시오.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 text-[11px] font-mono break-all p-2 rounded bg-white dark:bg-slate-950 border border-slate-100 dark:border-slate-800">
                {issued.token}
              </code>
              <button
                onClick={() => void handleCopy(issued.token)}
                className="btn-outline text-[11px] h-9 px-3 flex items-center gap-1.5"
              >
                <Copy size={12} />복사
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
