'use client';

import { use, useEffect, useState } from 'react';
import Link from 'next/link';
import { CheckCircle2, XCircle, ArrowLeft } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import { getExam, getExamSubmissions, type ExamApi, type ExamSubmissionApi } from '@/lib/api';

export default function ExamResultPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const examId = parseInt(id, 10);
  const { token } = useAuth();

  const [exam, setExam] = useState<ExamApi | null>(null);
  const [submissions, setSubmissions] = useState<ExamSubmissionApi[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      if (!token) return;
      setIsLoading(true);
      try {
        const [examData, subData] = await Promise.all([
          getExam(examId, token),
          getExamSubmissions(examId, token),
        ]);
        if (isMounted) {
          setExam(examData);
          setSubmissions(subData);
        }
      } catch (err) {
        console.error(err);
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadData();

    return () => {
      isMounted = false;
    };
  }, [examId, token]);

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center text-slate-400">
        Loading exam results...
      </div>
    );
  }

  const latestSubmission = submissions[0];

  return (
    <div className="max-w-4xl mx-auto py-8 space-y-6">
      <Link
        href="/exam"
        className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 font-medium transition-colors"
      >
        <ArrowLeft size={14} /> Back to Exam List
      </Link>

      <div className="card-simple space-y-6">
        <div className="border-b border-slate-200 dark:border-slate-800 pb-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white">
              {exam?.title ?? 'Exam Result'}
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">Exam Submission Status</p>
          </div>
          {latestSubmission ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-600 dark:bg-emerald-950/30 dark:text-emerald-400">
              <CheckCircle2 size={14} /> Submitted
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-50 text-rose-600 dark:bg-rose-950/30 dark:text-rose-400">
              <XCircle size={14} /> No Submissions
            </span>
          )}
        </div>

        {latestSubmission ? (
          <div className="space-y-4 text-sm">
            <div className="grid grid-cols-2 gap-4 p-4 bg-slate-50 dark:bg-slate-900 rounded-lg">
              <div>
                <span className="text-xs text-slate-400 block">Submission ID</span>
                <span className="font-mono font-medium">{latestSubmission.id}</span>
              </div>
              <div>
                <span className="text-xs text-slate-400 block">Submitted At</span>
                <span className="font-medium">
                  {new Date(latestSubmission.submitted_at).toLocaleString()}
                </span>
              </div>
              <div>
                <span className="text-xs text-slate-400 block">Language</span>
                <span className="font-mono uppercase font-medium">{latestSubmission.language}</span>
              </div>
              <div>
                <span className="text-xs text-slate-400 block">Status</span>
                <span className="font-medium capitalize">{latestSubmission.status}</span>
              </div>
            </div>

            <div className="p-4 border border-slate-200 dark:border-slate-800 rounded-lg bg-amber-50/50 dark:bg-amber-950/10">
              <p className="text-xs text-amber-700 dark:text-amber-400">
                Your exam response has been recorded. Final grades will be updated after instructor evaluation.
              </p>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-500 py-4 text-center">
            You have not submitted an answer for this exam.
          </p>
        )}
      </div>
    </div>
  );
}
