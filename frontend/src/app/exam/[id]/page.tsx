'use client';

import { use, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import DynamicEditor from '@/components/DynamicEditor';
import { Clock, Send, AlertTriangle } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import { getExam, submitExam, type ExamApi } from '@/lib/api';

export default function ExamTakePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const examId = parseInt(id, 10);
  const router = useRouter();
  const { token } = useAuth();

  const [exam, setExam] = useState<ExamApi | null>(null);
  const [code, setCode] = useState<string>('# Write your exam submission code here\n');
  const [language, setLanguage] = useState<string>('python');
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(null);

  useEffect(() => {
    if (!exam?.deadline) {
      setRemainingSeconds(null);
      return;
    }

    const deadlineMs = new Date(exam.deadline).getTime();
    const updateRemaining = () => {
      setRemainingSeconds(Math.max(0, Math.floor((deadlineMs - Date.now()) / 1000)));
    };

    updateRemaining();
    const timer = setInterval(updateRemaining, 1000);
    return () => clearInterval(timer);
  }, [exam?.deadline]);

  const formatRemaining = (totalSeconds: number) => {
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    const pad = (value: number) => String(value).padStart(2, '0');
    return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
  };

  useEffect(() => {
    let isMounted = true;

    async function fetchExam() {
      setIsLoading(true);
      try {
        const data = await getExam(examId, token);
        if (isMounted) {
          setExam(data);
          if (data.allowed_languages && data.allowed_languages.length > 0) {
            setLanguage(data.allowed_languages[0]);
          }
        }
      } catch (err) {
        if (isMounted) {
          setErrorMessage(err instanceof Error ? err.message : 'Failed to load exam details.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    if (examId) {
      void fetchExam();
    }

    return () => {
      isMounted = false;
    };
  }, [examId, token]);

  const handleSubmit = async () => {
    if (!token) {
      alert('Authentication required.');
      return;
    }

    if (!code.trim()) {
      alert('Please enter your code before submitting.');
      return;
    }

    if (!confirm('Are you sure you want to submit your exam response?')) {
      return;
    }

    setIsSubmitting(true);
    try {
      await submitExam(
        examId,
        {
          language,
          code_text: code,
          original_filename: `exam_${examId}.${language === 'python' ? 'py' : 'c'}`,
        },
        token,
      );
      router.push(`/exam/${examId}/result`);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Exam submission failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto py-12 text-center text-slate-400">
        Loading exam session...
      </div>
    );
  }

  if (errorMessage || !exam) {
    return (
      <div className="max-w-3xl mx-auto py-12">
        <div className="card-simple border-rose-200 bg-rose-50 dark:bg-rose-950/20 text-center p-8">
          <AlertTriangle className="mx-auto text-rose-500 mb-3" size={36} />
          <h2 className="text-lg font-bold text-rose-700 dark:text-rose-400 mb-2">Exam Unavailable</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400">{errorMessage || 'Exam not found.'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto py-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
              Exam Mode
            </span>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{exam.title}</h1>
          </div>
          <p className="text-slate-500 text-sm">{exam.intro}</p>
        </div>

        <div className="flex items-center gap-4">
          {remainingSeconds !== null && (
            <div
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-mono font-bold ${
                remainingSeconds <= 300
                  ? 'border-rose-200 bg-rose-50 text-rose-600 dark:bg-rose-950/20 dark:text-rose-400'
                  : 'border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300'
              }`}
            >
              <Clock size={15} />
              {remainingSeconds > 0 ? formatRemaining(remainingSeconds) : 'Time is up'}
            </div>
          )}
          <button
            onClick={() => void handleSubmit()}
            disabled={isSubmitting || !exam.can_submit}
            className="flex items-center gap-2 px-5 py-2.5 bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white font-medium rounded-lg transition-colors shadow-sm"
          >
            <Send size={16} />
            {isSubmitting ? 'Submitting...' : 'Submit Exam'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <div className="card-simple space-y-3">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Exam Info</h3>
            <div className="text-xs space-y-2 text-slate-600 dark:text-slate-400">
              <div className="flex justify-between">
                <span>Code Name:</span>
                <span className="font-mono text-slate-900 dark:text-slate-200">{exam.codeName}</span>
              </div>
              <div className="flex justify-between">
                <span>Time Limit:</span>
                <span>{exam.sec}s per test run</span>
              </div>
              <div className="flex justify-between">
                <span>Deadline:</span>
                <span>{exam.deadline ? new Date(exam.deadline).toLocaleString() : 'N/A'}</span>
              </div>
            </div>
          </div>

          <div className="card-simple space-y-2">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">Language</label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full text-xs p-2 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900"
            >
              {exam.allowed_languages.map((lang) => (
                <option key={lang} value={lang}>
                  {lang.toUpperCase()}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="lg:col-span-3 card-simple p-0 overflow-hidden border border-slate-200 dark:border-slate-800 h-[550px]">
          <DynamicEditor
            height="100%"
            language={language}
            theme="vs-dark"
            value={code}
            onChange={(val) => setCode(val ?? '')}
            options={{
              minimap: { enabled: false },
              fontSize: 14,
            }}
          />
        </div>
      </div>
    </div>
  );
}
