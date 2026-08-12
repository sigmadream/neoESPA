'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Upload, Send, AlertCircle, FileCode, CheckCircle2, Loader2 } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import { createSubmission, saveCodeSnapshot, getLatestSnapshot, type HomeworkApi } from '@/lib/api';

const LANGUAGE_LABELS: Record<string, string> = {
  python: 'Python',
  c: 'C',
  cpp: 'C++',
  java: 'Java',
};

const DEFAULT_LANGUAGES = Object.keys(LANGUAGE_LABELS);

const LANGUAGE_BY_EXTENSION: Record<string, string> = {
  py: 'python',
  c: 'c',
  cc: 'cpp',
  cpp: 'cpp',
  cxx: 'cpp',
  java: 'java',
};

export default function HomeworkSubmissionPanel({
  homework,
}: {
  homework: HomeworkApi;
}) {
  const { token } = useAuth();
  const router = useRouter();
  const allowedLanguages =
    homework.allowed_languages.length > 0
      ? homework.allowed_languages
      : DEFAULT_LANGUAGES;
  const allowedLanguageText = allowedLanguages
    .map((language) => LANGUAGE_LABELS[language] ?? language)
    .join(', ');

  const [language, setLanguage] = useState(allowedLanguages[0] ?? 'python');
  const [code, setCode] = useState('');
  const [selectedFileName, setSelectedFileName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  
  // Auto-save state
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);
  const initialLoadRef = useRef(false);

  // Restore latest snapshot on mount
  useEffect(() => {
    async function restoreLatest() {
      if (!token || initialLoadRef.current) return;
      
      try {
        const latest = await getLatestSnapshot(homework.num, token);
        if (latest && latest.code_text) {
          setCode(latest.code_text);
          if (allowedLanguages.includes(latest.language)) {
            setLanguage(latest.language);
          }
          setLastSaved(new Date(latest.created_at));
        }
      } catch (err) {
        console.error('Failed to restore latest snapshot:', err);
      } finally {
        initialLoadRef.current = true;
      }
    }

    void restoreLatest();
  }, [homework.num, token, allowedLanguages]);

  // Auto-save logic
  useEffect(() => {
    if (!token || !initialLoadRef.current) return;

    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }

    if (!code.trim()) return;

    autoSaveTimerRef.current = setTimeout(() => {
      async function triggerAutoSave() {
        if (!token) return;
        setIsSaving(true);
        setSaveError(false);
        try {
          await saveCodeSnapshot({
            homework_num: homework.num,
            language,
            code_text: code,
            snapshot_type: 'auto_save',
          }, token);
          setLastSaved(new Date());
        } catch (err) {
          console.error('Auto-save failed:', err);
          setSaveError(true);
        } finally {
          setIsSaving(false);
        }
      }

      void triggerAutoSave();
    }, 3000); // 3 seconds debounce

    return () => {
      if (autoSaveTimerRef.current) {
        clearTimeout(autoSaveTimerRef.current);
      }
    };
  }, [code, language, homework.num, token]);

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      setSelectedFileName('');
      return;
    }

    try {
      const nextCode = await file.text();
      const extension = file.name.split('.').pop()?.toLowerCase() ?? '';
      const detectedLanguage = LANGUAGE_BY_EXTENSION[extension];
      const nextLanguage =
        detectedLanguage && allowedLanguages.includes(detectedLanguage)
          ? detectedLanguage
          : language;

      setSelectedFileName(file.name);
      setErrorMessage(
        detectedLanguage && !allowedLanguages.includes(detectedLanguage)
          ? `Detected ${LANGUAGE_LABELS[detectedLanguage] ?? detectedLanguage}, but this assignment only accepts ${allowedLanguageText}.`
          : '',
      );
      setCode(nextCode);
      setLanguage(nextLanguage);
    } catch {
      setErrorMessage('Failed to read the selected file.');
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      setErrorMessage('로그인 후 제출할 수 있습니다.');
      return;
    }
    if (!code.trim()) {
      setErrorMessage('Please provide your source code.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage('');

    try {
      const submission = await createSubmission(
        {
          homework_num: homework.num,
          language,
          code_text: code,
          original_filename: selectedFileName || null,
        },
        token,
      );
      router.push(`/homework/result?id=${submission.id}`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Submission failed.');
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!token) {
    return (
      <section className="card-simple border-dashed border-slate-200 bg-slate-50/50 dark:bg-slate-900/10">
        <div className="flex items-center gap-3 mb-3">
          <AlertCircle className="text-slate-400" size={20} />
          <h2 className="text-base font-semibold">Sign in to Submit</h2>
        </div>
        <p className="text-sm text-slate-500">
          You must be logged in to submit your assignment.
        </p>
      </section>
    );
  }

  return (
    <section className="card-simple space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold flex items-center gap-2 text-slate-900 dark:text-white">
          <Send size={18} className="text-accent" />
          Submit Solution
        </h2>
        <div className="text-[10px] font-mono text-slate-400">
          TARGET: {homework.codeName}
        </div>
      </div>

      <form onSubmit={(event) => void handleSubmit(event)} className="space-y-6">
        {errorMessage && (
          <div className="p-3 rounded bg-rose-50 dark:bg-rose-950/20 border border-rose-100 dark:border-rose-900/30 text-xs font-medium text-rose-600 dark:text-rose-400">
            {errorMessage}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label htmlFor="language" className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
              제출 언어 선택
            </label>
            <select
              id="language"
              className="block w-full text-sm rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 transition-all focus:ring-1 focus:ring-accent outline-none"
              value={language}
              onChange={(event) => setLanguage(event.target.value)}
              disabled={allowedLanguages.length === 0}
            >
              {allowedLanguages.map((lang) => (
                <option key={lang} value={lang}>{LANGUAGE_LABELS[lang] ?? lang}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
              소스 코드 파일 업로드
            </label>
            <label className="flex items-center justify-center w-full h-10 px-4 border border-slate-200 dark:border-slate-800 rounded bg-white dark:bg-slate-950 text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-900 cursor-pointer transition-colors group">
              <Upload size={14} className="mr-2 group-hover:text-accent" />
              <span>{selectedFileName ? '파일 변경하기' : '파일 선택하기'}</span>
              <input type="file" className="sr-only" onChange={handleFileChange} />
            </label>
            {selectedFileName && (
              <p className="mt-1 text-[10px] text-accent font-medium truncate italic">{selectedFileName}</p>
            )}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <label htmlFor="code" className="block text-xs font-bold text-slate-400 uppercase tracking-wider">
                코드 에디터
              </label>
              <div className="flex items-center gap-1.5 transition-all">
                {isSaving ? (
                  <div className="flex items-center gap-1 text-[10px] text-accent animate-pulse font-medium">
                    <Loader2 size={10} className="animate-spin" />
                    자동 저장 중...
                  </div>
                ) : saveError ? (
                  <div className="flex items-center gap-1 text-[10px] text-rose-500 font-bold animate-pulse">
                    <AlertCircle size={10} />
                    저장 실패
                  </div>
                ) : lastSaved ? (
                  <div className="flex items-center gap-1 text-[10px] text-emerald-500 font-medium">
                    <CheckCircle2 size={10} />
                    임시 저장됨 {lastSaved.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </div>
                ) : null}
              </div>
            </div>
            <span className="text-[10px] text-slate-400 font-medium">UTF-8 인코딩 필수</span>
          </div>
          <div className="relative group">
            <div className="absolute top-3 left-3">
              <FileCode size={14} className="text-slate-700 dark:text-slate-500 opacity-50" />
            </div>
            <textarea
              id="code"
              rows={15}
              className="block w-full rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 pl-9 pr-4 py-3 font-mono text-sm text-slate-800 dark:text-slate-200 focus:ring-1 focus:ring-accent outline-none transition-all resize-none"
              placeholder="// 작성한 코드를 입력하거나 소스 코드 파일을 업로드하세요..."
              value={code}
              onChange={(event) => setCode(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Tab') {
                  event.preventDefault();
                  const target = event.currentTarget;
                  const start = target.selectionStart;
                  const end = target.selectionEnd;
                  const indent = '  ';

                  if (event.shiftKey) {
                    const lineStart = target.value.lastIndexOf('\n', start - 1) + 1;
                    const beforeCursor = target.value.substring(lineStart, start);
                    if (beforeCursor.endsWith(indent)) {
                      const newValue =
                        target.value.substring(0, start - indent.length) + target.value.substring(start);
                      setCode(newValue);
                      requestAnimationFrame(() => {
                        target.selectionStart = target.selectionEnd = start - indent.length;
                      });
                    }
                  } else {
                    const newValue =
                      target.value.substring(0, start) + indent + target.value.substring(end);
                    setCode(newValue);
                    requestAnimationFrame(() => {
                      target.selectionStart = target.selectionEnd = start + indent.length;
                    });
                  }
                }
              }}
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={isSubmitting || !homework.can_submit}
          className="btn-flat w-full h-12 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm active:translate-y-0.5 transition-all"
        >
          {isSubmitting ? (
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <Send size={16} />
          )}
          <span>과제 답안 제출하기</span>
        </button>
      </form>
    </section>
  );
}
