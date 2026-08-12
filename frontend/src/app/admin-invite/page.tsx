'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { KeyRound, ShieldCheck, UserPlus } from 'lucide-react';

import { acceptAdminInvitation, bootstrapFirstAdmin } from '@/lib/api';

type Mode = 'invitation' | 'bootstrap';

const MODES: Array<{ value: Mode; label: string; description: string }> = [
  {
    value: 'invitation',
    label: '초대로 가입',
    description: '운영진에게 받은 초대 토큰으로 관리자·조교 계정을 만듭니다.',
  },
  {
    value: 'bootstrap',
    label: '최초 관리자 등록',
    description:
      '시스템에 관리자가 아직 없을 때, CLI(issue-bootstrap-token)로 발급한 일회성 토큰으로 첫 관리자를 만듭니다.',
  },
];

export default function AdminInvitePage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>('invitation');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setIsSubmitting(true);
    setErrorMessage('');
    setSuccessMessage('');

    const common = {
      token: String(data.get('token') ?? '').trim(),
      id: String(data.get('id') ?? '').trim(),
      sid: Number(data.get('sid') ?? 0),
      name: String(data.get('name') ?? '').trim(),
      phone: String(data.get('phone') ?? '').trim(),
      password: String(data.get('password') ?? ''),
    };

    try {
      const user =
        mode === 'invitation'
          ? await acceptAdminInvitation(common)
          : await bootstrapFirstAdmin({
              ...common,
              email: String(data.get('email') ?? '').trim(),
            });
      setSuccessMessage(
        `${user.id} 계정이 ${user.user_group} 권한으로 생성되었습니다. 로그인 화면으로 이동합니다.`,
      );
      setTimeout(() => router.push('/login'), 1500);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '계정을 만들지 못했습니다.',
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const activeMode = MODES.find((item) => item.value === mode);

  return (
    <div className="max-w-2xl mx-auto py-12 px-4 space-y-8">
      <header>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
          <ShieldCheck className="text-accent" size={24} />
          운영진 계정 등록
        </h1>
        <p className="text-slate-500 text-sm font-medium">
          발급받은 토큰으로 운영진 계정을 만듭니다.
        </p>
      </header>

      <div className="flex flex-wrap gap-2">
        {MODES.map((item) => (
          <button
            key={item.value}
            onClick={() => {
              setMode(item.value);
              setErrorMessage('');
              setSuccessMessage('');
            }}
            className={`text-xs font-bold px-4 py-2 rounded border transition-all ${
              mode === item.value
                ? 'border-blue-500 bg-blue-50 text-blue-600 dark:bg-blue-950/30 dark:text-blue-400'
                : 'border-slate-200 dark:border-slate-800 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-900'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      <section className="card-simple">
        <p className="text-[11px] text-slate-500 leading-relaxed mb-6">
          {activeMode?.description}
        </p>

        <form onSubmit={(event) => void handleSubmit(event)} className="space-y-5">
          <label className="flex flex-col gap-1.5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 flex items-center gap-1.5">
              <KeyRound size={11} /> 토큰
            </span>
            <input
              name="token"
              required
              placeholder="발급받은 일회성 토큰"
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2.5 outline-none focus:ring-1 focus:ring-accent font-mono"
            />
          </label>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <label className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">아이디</span>
              <input name="id" required className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2.5 outline-none focus:ring-1 focus:ring-accent" />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">학번/교번</span>
              <input name="sid" required inputMode="numeric" className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2.5 outline-none focus:ring-1 focus:ring-accent" />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">이름</span>
              <input name="name" required className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2.5 outline-none focus:ring-1 focus:ring-accent" />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">연락처</span>
              <input name="phone" required placeholder="010-0000-0000" className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2.5 outline-none focus:ring-1 focus:ring-accent" />
            </label>
            {mode === 'bootstrap' && (
              <label className="flex flex-col gap-1.5 sm:col-span-2">
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">이메일</span>
                <input name="email" type="email" required className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2.5 outline-none focus:ring-1 focus:ring-accent" />
              </label>
            )}
            <label className="flex flex-col gap-1.5 sm:col-span-2">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">비밀번호</span>
              <input name="password" type="password" required className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2.5 outline-none focus:ring-1 focus:ring-accent" />
            </label>
          </div>

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

          <button
            type="submit"
            disabled={isSubmitting}
            className="btn-flat w-full h-11 text-sm flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <UserPlus size={16} />
            {isSubmitting ? '등록 중...' : '계정 만들기'}
          </button>
        </form>
      </section>
    </div>
  );
}
