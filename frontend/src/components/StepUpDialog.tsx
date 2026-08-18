'use client';

import { useState } from 'react';
import { KeyRound, X } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';

type StepUpDialogProps = {
  open: boolean;
  onClose: () => void;
  onSuccess: (elevatedToken: string) => void;
  description?: string;
};

/**
 * 민감한 관리 작업 전 비밀번호 재인증을 받는다.
 * 서버가 재인증을 요구(403)했을 때 화면에서 열어 사용한다.
 */
export default function StepUpDialog({
  open,
  onClose,
  onSuccess,
  description,
}: StepUpDialogProps) {
  const { stepUp } = useAuth();
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  if (!open) return null;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage('');
    try {
      const elevatedToken = await stepUp(password);
      setPassword('');
      onSuccess(elevatedToken);
      onClose();
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '재인증에 실패했습니다.',
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 backdrop-blur-sm px-4">
      <div className="w-full max-w-sm card-simple shadow-lg">
        <header className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-1">
              <KeyRound size={14} className="text-accent" />
              재인증 필요
            </h2>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              {description ??
                '보안이 필요한 작업입니다. 비밀번호를 다시 입력해 주십시오.'}
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="닫기"
            className="text-slate-400 hover:text-slate-600 transition-colors"
          >
            <X size={16} />
          </button>
        </header>

        <form onSubmit={(event) => void handleSubmit(event)} className="space-y-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
              비밀번호
            </span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              autoFocus
              className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent"
            />
          </label>

          {errorMessage && (
            <div className="p-3 rounded text-[11px] font-medium border bg-rose-50 border-rose-100 text-rose-600 dark:bg-rose-950/20">
              {errorMessage}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting || !password}
            className="btn-flat w-full h-10 text-xs flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <KeyRound size={14} />
            {isSubmitting ? '확인 중...' : '재인증'}
          </button>
        </form>
      </div>
    </div>
  );
}
