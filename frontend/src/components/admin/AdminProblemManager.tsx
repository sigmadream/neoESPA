'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  Archive,
  BadgeCheck,
  CheckCircle2,
  Download,
  FileCode,
  GitBranch,
  PlayCircle,
  Plus,
  RefreshCw,
  Trash2,
  Upload,
  Users,
} from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import {
  addProblemCollaborator,
  approveProblemRevision,
  archiveProblem,
  createProblem,
  createProblemDryRun,
  createProblemRevision,
  createProblemTestcase,
  createProblemValidationJob,
  createTestcaseGroup,
  deleteProblemTestcase,
  downloadProblemAsset,
  getProblemAssets,
  getProblemCollaborators,
  getProblemRevisions,
  getProblems,
  getProblemTestcases,
  getTestcaseGroups,
  importProblemTestcasePackage,
  publishProblemRevision,
  removeProblemCollaborator,
  uploadProblemAsset,
  validateProblemRevision,
  type ProblemApi,
  type ProblemAssetApi,
  type ProblemCollaboratorApi,
  type ProblemRevisionApi,
  type ProblemTestCaseApi,
  type TestCaseGroupApi,
} from '@/lib/api';

const LANGUAGE_OPTIONS = ['c', 'cpp', 'python', 'java'] as const;

function statusTone(status: string) {
  if (status === 'published') return 'text-emerald-600 dark:text-emerald-400';
  if (status === 'validated' || status === 'approved') return 'text-accent';
  if (status === 'rejected') return 'text-rose-600 dark:text-rose-400';
  return 'text-amber-600 dark:text-amber-400';
}

export default function AdminProblemManager() {
  const { token } = useAuth();
  const [problems, setProblems] = useState<ProblemApi[]>([]);
  const [selectedProblemId, setSelectedProblemId] = useState<number | null>(null);
  const [revisions, setRevisions] = useState<ProblemRevisionApi[]>([]);
  const [selectedRevisionId, setSelectedRevisionId] = useState<number | null>(null);
  const [testcases, setTestcases] = useState<ProblemTestCaseApi[]>([]);
  const [assets, setAssets] = useState<ProblemAssetApi[]>([]);
  const [groups, setGroups] = useState<TestCaseGroupApi[]>([]);
  const [collaborators, setCollaborators] = useState<ProblemCollaboratorApi[]>([]);

  const [isLoading, setIsLoading] = useState(true);
  const [isWorking, setIsWorking] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const [approvalNote, setApprovalNote] = useState('');
  const [collaboratorId, setCollaboratorId] = useState('');
  const [collaboratorCanEdit, setCollaboratorCanEdit] = useState(true);

  const loadProblems = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      const response = await getProblems(token, { limit: 100 });
      setProblems(response);
      setSelectedProblemId((current) => current ?? response[0]?.id ?? null);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '문제 목록을 불러오지 못했습니다.',
      );
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void loadProblems();
  }, [loadProblems]);

  const loadProblemDetail = useCallback(
    async (problemId: number) => {
      if (!token) return;
      const [revisionRes, collaboratorRes] = await Promise.allSettled([
        getProblemRevisions(problemId, token),
        getProblemCollaborators(problemId, token),
      ]);
      if (revisionRes.status === 'fulfilled') {
        setRevisions(revisionRes.value);
        setSelectedRevisionId(revisionRes.value[0]?.id ?? null);
      } else {
        setRevisions([]);
        setSelectedRevisionId(null);
      }
      setCollaborators(
        collaboratorRes.status === 'fulfilled' ? collaboratorRes.value : [],
      );
    },
    [token],
  );

  useEffect(() => {
    if (selectedProblemId === null) return;
    void loadProblemDetail(selectedProblemId);
  }, [loadProblemDetail, selectedProblemId]);

  const loadTestcases = useCallback(async () => {
    if (!token || selectedProblemId === null || selectedRevisionId === null) {
      setTestcases([]);
      setAssets([]);
      setGroups([]);
      return;
    }
    const [caseRes, assetRes, groupRes] = await Promise.allSettled([
      getProblemTestcases(selectedProblemId, selectedRevisionId, token),
      getProblemAssets(selectedProblemId, selectedRevisionId, token),
      getTestcaseGroups(selectedProblemId, selectedRevisionId, token),
    ]);
    setTestcases(caseRes.status === 'fulfilled' ? caseRes.value : []);
    setAssets(assetRes.status === 'fulfilled' ? assetRes.value : []);
    setGroups(groupRes.status === 'fulfilled' ? groupRes.value : []);
  }, [selectedProblemId, selectedRevisionId, token]);

  useEffect(() => {
    void loadTestcases();
  }, [loadTestcases]);

  const runAction = async (
    action: (authToken: string) => Promise<string>,
    fallbackError: string,
  ) => {
    if (!token) return;
    setIsWorking(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      setSuccessMessage(await action(token));
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : fallbackError);
    } finally {
      setIsWorking(false);
    }
  };

  const handleCreateProblem = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    const data = new FormData(formElement);
    await runAction(async (authToken) => {
      const problem = await createProblem(
        {
          code: String(data.get('code') ?? ''),
          title: String(data.get('title') ?? ''),
          statement: String(data.get('statement') ?? ''),
          input_description: String(data.get('input_description') ?? ''),
          output_description: String(data.get('output_description') ?? ''),
          time_limit_ms: Number(data.get('time_limit_ms') || 2000),
          memory_limit_mb: Number(data.get('memory_limit_mb') || 256),
          allowed_languages: LANGUAGE_OPTIONS.filter(
            (language) => data.get(`language_${language}`) === 'on',
          ),
        },
        authToken,
      );
      formElement.reset();
      setSelectedProblemId(problem.id);
      await loadProblems();
      return `문제 #${problem.id} "${problem.title}"을(를) 만들었습니다.`;
    }, '문제를 만들지 못했습니다.');
  };

  const handleCreateTestcase = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (selectedProblemId === null || selectedRevisionId === null) return;
    const formElement = event.currentTarget;
    const data = new FormData(formElement);
    const inputFile = data.get('input_file');
    const outputFile = data.get('output_file');
    if (!(inputFile instanceof File) || !(outputFile instanceof File)) {
      setErrorMessage('입력 파일과 출력 파일을 모두 선택하십시오.');
      return;
    }
    await runAction(async (authToken) => {
      const testcase = await createProblemTestcase(
        selectedProblemId,
        selectedRevisionId,
        {
          caseName: String(data.get('case_name') ?? ''),
          position: Number(data.get('position') || testcases.length + 1),
          score: Number(data.get('score') || 0),
          isSample: data.get('is_sample') === 'on',
          inputFile,
          outputFile,
        },
        authToken,
      );
      formElement.reset();
      await loadTestcases();
      return `테스트케이스 "${testcase.case_name}"을(를) 추가했습니다.`;
    }, '테스트케이스를 추가하지 못했습니다.');
  };

  const handleImportPackage = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (selectedProblemId === null || selectedRevisionId === null) return;
    const formElement = event.currentTarget;
    const packageFile = new FormData(formElement).get('package');
    if (!(packageFile instanceof File)) {
      setErrorMessage('ZIP 패키지를 선택하십시오.');
      return;
    }
    await runAction(async (authToken) => {
      const imported = await importProblemTestcasePackage(
        selectedProblemId,
        selectedRevisionId,
        packageFile,
        authToken,
      );
      formElement.reset();
      await loadTestcases();
      return `테스트케이스 ${imported.length}개를 가져왔습니다.`;
    }, '테스트케이스 패키지를 가져오지 못했습니다.');
  };

  const selectedProblem = problems.find(
    (problem) => problem.id === selectedProblemId,
  );
  const selectedRevision = revisions.find(
    (revision) => revision.id === selectedRevisionId,
  );

  if (isLoading && problems.length === 0) {
    return (
      <div className="py-20 text-center animate-pulse text-slate-400 font-medium">
        문제 목록을 불러오는 중입니다...
      </div>
    );
  }

  return (
    <div className="space-y-8">
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <section className="card-simple lg:col-span-1">
          <header className="flex items-center justify-between mb-6">
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2">
              <FileCode size={16} className="text-accent" />
              문제 목록
            </h2>
            <button
              onClick={() => void loadProblems()}
              className="p-1.5 rounded hover:bg-slate-50 dark:hover:bg-slate-900 text-slate-400 transition-all"
            >
              <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            </button>
          </header>

          {problems.length === 0 ? (
            <p className="text-xs text-slate-400 italic">등록된 문제가 없습니다.</p>
          ) : (
            <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1">
              {problems.map((problem) => (
                <button
                  key={problem.id}
                  onClick={() => setSelectedProblemId(problem.id)}
                  className={`w-full text-left p-3 rounded border transition-all ${
                    selectedProblemId === problem.id
                      ? 'border-blue-500 bg-blue-50/40 dark:bg-blue-950/20'
                      : 'border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate">
                      #{problem.id} {problem.title}
                    </span>
                    {!problem.is_active && (
                      <span className="text-[9px] font-black uppercase text-slate-400">보관</span>
                    )}
                  </div>
                  <p className="text-[10px] text-slate-400 font-mono">
                    {problem.code} · rev {problem.latest_revision_no ?? '-'}
                    {problem.published_revision_id
                      ? ` · 게시 #${problem.published_revision_id}`
                      : ' · 미게시'}
                  </p>
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="card-simple lg:col-span-2">
          <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-6">
            <Plus size={16} />새 문제 만들기
          </h2>
          <form onSubmit={(event) => void handleCreateProblem(event)} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <label className="flex flex-col gap-1.5">
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">문제 코드</span>
                <input name="code" required placeholder="sum-two" className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none font-mono" />
              </label>
              <label className="flex flex-col gap-1.5 sm:col-span-2">
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">문제 제목</span>
                <input name="title" required placeholder="두 수의 합" className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none" />
              </label>
            </div>

            <label className="flex flex-col gap-1.5">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">문제 설명</span>
              <textarea name="statement" rows={3} className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none resize-none" placeholder="문제 지문을 입력하세요." />
            </label>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <label className="flex flex-col gap-1.5">
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">입력 설명</span>
                <textarea name="input_description" rows={2} className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none resize-none" />
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">출력 설명</span>
                <textarea name="output_description" rows={2} className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none resize-none" />
              </label>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 items-end">
              <label className="flex flex-col gap-1.5">
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">시간 제한(ms)</span>
                <input name="time_limit_ms" defaultValue={2000} inputMode="numeric" className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none" />
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">메모리(MB)</span>
                <input name="memory_limit_mb" defaultValue={256} inputMode="numeric" className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none" />
              </label>
              <div className="sm:col-span-2">
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 block mb-2">허용 언어</span>
                <div className="flex flex-wrap gap-3">
                  {LANGUAGE_OPTIONS.map((language) => (
                    <label key={language} className="flex items-center gap-1.5 text-[11px] font-medium cursor-pointer">
                      <input type="checkbox" name={`language_${language}`} defaultChecked className="rounded border-slate-300 text-accent focus:ring-accent" />
                      <span className="text-slate-600 dark:text-slate-400">{language.toUpperCase()}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <button type="submit" disabled={isWorking} className="btn-flat h-10 px-6 text-xs flex items-center gap-2 disabled:opacity-50">
              <Plus size={14} />문제 생성
            </button>
          </form>
        </section>
      </div>

      {selectedProblem && (
        <section className="card-simple">
          <header className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-6">
            <div>
              <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-1">
                <GitBranch size={16} className="text-accent" />
                #{selectedProblem.id} {selectedProblem.title} · Revision
              </h2>
              <p className="text-[11px] text-slate-500 font-medium">
                리비전을 만들어 지문·제한·테스트케이스를 수정하고, 검증을 거쳐 게시합니다.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() =>
                  void runAction(async (authToken) => {
                    const revision = await createProblemRevision(
                      selectedProblem.id,
                      { clone_from_revision_id: selectedRevisionId },
                      authToken,
                    );
                    await loadProblemDetail(selectedProblem.id);
                    return `Revision ${revision.revision_no}을(를) 만들었습니다.`;
                  }, '리비전을 만들지 못했습니다.')
                }
                disabled={isWorking}
                className="btn-outline text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
              >
                <GitBranch size={14} />현재 리비전 복제
              </button>
              <button
                onClick={() =>
                  void runAction(async (authToken) => {
                    const problem = await archiveProblem(selectedProblem.id, authToken);
                    await loadProblems();
                    return `문제 #${problem.id}을(를) 보관 처리했습니다.`;
                  }, '문제를 보관하지 못했습니다.')
                }
                disabled={isWorking || !selectedProblem.is_active}
                className="btn-outline text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
              >
                <Archive size={14} />보관
              </button>
            </div>
          </header>

          <div className="flex flex-wrap gap-2 mb-6">
            {revisions.map((revision) => (
              <button
                key={revision.id}
                onClick={() => setSelectedRevisionId(revision.id)}
                className={`text-[11px] font-medium px-3 py-1.5 rounded border transition-all ${
                  selectedRevisionId === revision.id
                    ? 'border-blue-500 bg-blue-50 text-blue-600 dark:bg-blue-950/30 dark:text-blue-400'
                    : 'border-slate-200 dark:border-slate-800 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-900'
                }`}
              >
                rev {revision.revision_no}
                <span className={`ml-2 text-[10px] font-black uppercase ${statusTone(revision.status)}`}>
                  {revision.status}
                </span>
              </button>
            ))}
          </div>

          {selectedRevision && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="space-y-4">
                <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                  검증 · 승인 · 게시
                </h3>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  테스트케이스를 등록한 뒤 검증을 통과해야 검수(승인)를 진행할 수 있고, 검수를 마쳐야
                  게시할 수 있습니다. 작성자 본인은 자신의 리비전을 승인할 수 없습니다.
                </p>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() =>
                      void runAction(async (authToken) => {
                        const revision = await validateProblemRevision(
                          selectedProblem.id,
                          selectedRevision.id,
                          authToken,
                        );
                        await loadProblemDetail(selectedProblem.id);
                        return `검증 결과 상태: ${revision.status}`;
                      }, '검증에 실패했습니다.')
                    }
                    disabled={isWorking}
                    className="btn-outline text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
                  >
                    <CheckCircle2 size={14} />즉시 검증
                  </button>
                  <button
                    onClick={() =>
                      void runAction(async (authToken) => {
                        const job = await createProblemValidationJob(
                          selectedProblem.id,
                          selectedRevision.id,
                          `ui-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
                          authToken,
                        );
                        return `검증 작업 #${job.id}을(를) 등록했습니다. (상태: ${job.status})`;
                      }, '검증 작업을 등록하지 못했습니다.')
                    }
                    disabled={isWorking}
                    className="btn-outline text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
                  >
                    <RefreshCw size={14} />검증 작업 등록
                  </button>
                  <button
                    onClick={() =>
                      void runAction(async (authToken) => {
                        const revision = await publishProblemRevision(
                          selectedProblem.id,
                          selectedRevision.id,
                          authToken,
                        );
                        await Promise.all([
                          loadProblems(),
                          loadProblemDetail(selectedProblem.id),
                        ]);
                        return `Revision ${revision.revision_no}을(를) 게시했습니다.`;
                      }, '게시하지 못했습니다.')
                    }
                    disabled={isWorking || selectedRevision.status === 'published'}
                    className="btn-flat text-xs h-9 px-4 flex items-center gap-2 disabled:opacity-50"
                  >
                    <BadgeCheck size={14} />게시
                  </button>
                </div>

                <div className="flex items-end gap-2">
                  <label className="flex flex-col gap-1.5 flex-1">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                      검수 의견
                    </span>
                    <input
                      value={approvalNote}
                      onChange={(event) => setApprovalNote(event.target.value)}
                      placeholder="예: 테스트케이스 보강 필요"
                      className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
                    />
                  </label>
                  {[
                    { decision: 'approved', label: '승인' },
                    { decision: 'changes_requested', label: '수정 요청' },
                  ].map((item) => (
                    <button
                      key={item.decision}
                      onClick={() =>
                        void runAction(async (authToken) => {
                          const approval = await approveProblemRevision(
                            selectedProblem.id,
                            selectedRevision.id,
                            { decision: item.decision, note: approvalNote.trim() || null },
                            authToken,
                          );
                          setApprovalNote('');
                          await loadProblemDetail(selectedProblem.id);
                          return `검수 결과 "${approval.decision}"을(를) 기록했습니다.`;
                        }, '검수 결과를 기록하지 못했습니다.')
                      }
                      disabled={isWorking}
                      className="btn-outline text-[11px] h-9 px-3 disabled:opacity-50"
                    >
                      {item.label}
                    </button>
                  ))}
                </div>

                {selectedRevision.validation_report && (
                  <div>
                    <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                      검증 리포트
                    </h3>
                    <pre className="rounded bg-slate-950 p-3 font-mono text-[10px] text-emerald-400/90 leading-relaxed overflow-auto max-h-40 border border-slate-800">
                      {selectedRevision.validation_report}
                    </pre>
                  </div>
                )}

                <div>
                  <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2 flex items-center gap-2">
                    <Users size={12} />
                    공동 작업자
                  </h3>
                  <p className="text-[11px] text-slate-500 leading-relaxed mb-2">
                    문제 데이터 열람 권한(problem:data.read)이 있는 역할만 지정할 수 있습니다.
                    학생 계정은 추가되지 않습니다.
                  </p>
                  <div className="space-y-2 mb-3">
                    {collaborators.length === 0 ? (
                      <p className="text-[11px] text-slate-400 italic">지정된 공동 작업자가 없습니다.</p>
                    ) : (
                      collaborators.map((collaborator) => (
                        <div
                          key={collaborator.id}
                          className="flex items-center justify-between gap-2 text-[11px] p-2 rounded border border-slate-100 dark:border-slate-800"
                        >
                          <span className="font-bold text-slate-700 dark:text-slate-300">
                            {collaborator.user_id}
                            <span className="ml-2 font-medium text-slate-400">
                              {collaborator.can_edit ? '편집 가능' : '읽기 전용'}
                            </span>
                          </span>
                          <button
                            onClick={() =>
                              void runAction(async (authToken) => {
                                await removeProblemCollaborator(
                                  selectedProblem.id,
                                  collaborator.user_id,
                                  authToken,
                                );
                                await loadProblemDetail(selectedProblem.id);
                                return `${collaborator.user_id}을(를) 제외했습니다.`;
                              }, '공동 작업자를 제외하지 못했습니다.')
                            }
                            disabled={isWorking}
                            className="text-slate-400 hover:text-rose-500 transition-colors disabled:opacity-50"
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                  <div className="flex items-end gap-2">
                    <input
                      value={collaboratorId}
                      onChange={(event) => setCollaboratorId(event.target.value)}
                      placeholder="사용자 ID"
                      className="flex-1 text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none"
                    />
                    <label className="flex items-center gap-1.5 text-[11px] font-medium cursor-pointer">
                      <input
                        type="checkbox"
                        checked={collaboratorCanEdit}
                        onChange={(event) => setCollaboratorCanEdit(event.target.checked)}
                        className="rounded border-slate-300 text-accent focus:ring-accent"
                      />
                      <span className="text-slate-600 dark:text-slate-400">편집 허용</span>
                    </label>
                    <button
                      onClick={() =>
                        void runAction(async (authToken) => {
                          const collaborator = await addProblemCollaborator(
                            selectedProblem.id,
                            { user_id: collaboratorId.trim(), can_edit: collaboratorCanEdit },
                            authToken,
                          );
                          setCollaboratorId('');
                          await loadProblemDetail(selectedProblem.id);
                          return `${collaborator.user_id}을(를) 추가했습니다.`;
                        }, '공동 작업자를 추가하지 못했습니다.')
                      }
                      disabled={isWorking || !collaboratorId.trim()}
                      className="btn-outline text-[11px] h-9 px-3 disabled:opacity-50"
                    >
                      추가
                    </button>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                  테스트케이스 ({testcases.length}개)
                </h3>

                <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
                  {testcases.length === 0 ? (
                    <p className="text-[11px] text-slate-400 italic">등록된 테스트케이스가 없습니다.</p>
                  ) : (
                    testcases.map((testcase) => (
                      <div
                        key={testcase.id}
                        className="flex items-center justify-between gap-2 p-2 rounded border border-slate-100 dark:border-slate-800"
                      >
                        <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300 truncate">
                          {testcase.position}. {testcase.case_name}
                          {testcase.is_sample && (
                            <span className="ml-2 text-[9px] font-black uppercase text-accent">예제</span>
                          )}
                        </span>
                        <span className="flex items-center gap-3">
                          <span className="text-[10px] font-medium text-slate-400">
                            {testcase.score}점
                          </span>
                          <button
                            onClick={() =>
                              void runAction(async (authToken) => {
                                await deleteProblemTestcase(
                                  selectedProblem.id,
                                  selectedRevision.id,
                                  testcase.id,
                                  authToken,
                                );
                                await loadTestcases();
                                return `테스트케이스 "${testcase.case_name}"을(를) 삭제했습니다.`;
                              }, '테스트케이스를 삭제하지 못했습니다.')
                            }
                            disabled={isWorking}
                            className="text-slate-400 hover:text-rose-500 transition-colors disabled:opacity-50"
                          >
                            <Trash2 size={12} />
                          </button>
                        </span>
                      </div>
                    ))
                  )}
                </div>

                <form
                  onSubmit={(event) => void handleCreateTestcase(event)}
                  className="space-y-3 p-3 rounded border border-slate-100 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-900/20"
                >
                  <div className="grid grid-cols-3 gap-2">
                    <input name="case_name" required placeholder="케이스 이름" className="text-[11px] rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-2 py-1.5 outline-none" />
                    <input name="position" inputMode="numeric" placeholder="순서" className="text-[11px] rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-2 py-1.5 outline-none" />
                    <input name="score" inputMode="decimal" placeholder="배점" className="text-[11px] rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-2 py-1.5 outline-none" />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <input name="input_file" type="file" required className="text-[10px] file:mr-2 file:rounded file:border-0 file:bg-slate-200 dark:file:bg-slate-800 file:px-2 file:py-1 file:text-[10px] file:font-bold" />
                    <input name="output_file" type="file" required className="text-[10px] file:mr-2 file:rounded file:border-0 file:bg-slate-200 dark:file:bg-slate-800 file:px-2 file:py-1 file:text-[10px] file:font-bold" />
                  </div>
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-1.5 text-[11px] font-medium cursor-pointer">
                      <input type="checkbox" name="is_sample" className="rounded border-slate-300 text-accent focus:ring-accent" />
                      <span className="text-slate-600 dark:text-slate-400">예제로 공개</span>
                    </label>
                    <button type="submit" disabled={isWorking} className="btn-outline text-[11px] h-8 px-3 flex items-center gap-1.5 disabled:opacity-50">
                      <Plus size={12} />케이스 추가
                    </button>
                  </div>
                </form>

                <form
                  onSubmit={(event) => void handleImportPackage(event)}
                  className="flex items-center gap-2 p-3 rounded border border-dashed border-slate-200 dark:border-slate-800"
                >
                  <input name="package" type="file" accept=".zip" required className="flex-1 text-[10px] file:mr-2 file:rounded file:border-0 file:bg-slate-200 dark:file:bg-slate-800 file:px-2 file:py-1 file:text-[10px] file:font-bold" />
                  <button type="submit" disabled={isWorking} className="btn-outline text-[11px] h-8 px-3 flex items-center gap-1.5 disabled:opacity-50">
                    <Upload size={12} />ZIP 일괄 등록
                  </button>
                </form>

                <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
                  <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                    채점 그룹 ({groups.length}개)
                  </h3>
                  <p className="text-[11px] text-slate-500 leading-relaxed mb-2">
                    부분 점수를 그룹 단위로 계산할 때 사용합니다. 테스트케이스의 그룹 지정은 API로
                    관리합니다.
                  </p>
                  <div className="flex flex-wrap gap-2 mb-3">
                    {groups.map((group) => (
                      <span
                        key={group.id}
                        className="text-[10px] font-medium px-2 py-1 rounded border border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50"
                      >
                        {group.group_key} · {group.score}점 · {group.scoring_policy}
                      </span>
                    ))}
                  </div>
                  <form
                    onSubmit={(event) => {
                      event.preventDefault();
                      const data = new FormData(event.currentTarget);
                      const formElement = event.currentTarget;
                      void runAction(async (authToken) => {
                        const group = await createTestcaseGroup(
                          selectedProblem.id,
                          selectedRevision.id,
                          {
                            group_key: String(data.get('group_key') ?? ''),
                            position: Number(data.get('position') || groups.length + 1),
                            score: Number(data.get('score') || 0),
                            scoring_policy: String(data.get('scoring_policy') ?? 'sum'),
                          },
                          authToken,
                        );
                        formElement.reset();
                        await loadTestcases();
                        return `채점 그룹 "${group.group_key}"을(를) 추가했습니다.`;
                      }, '채점 그룹을 추가하지 못했습니다.');
                    }}
                    className="grid grid-cols-4 gap-2"
                  >
                    <input name="group_key" required placeholder="그룹 키" className="text-[11px] rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-2 py-1.5 outline-none" />
                    <input name="score" inputMode="decimal" placeholder="배점" className="text-[11px] rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-2 py-1.5 outline-none" />
                    <select name="scoring_policy" className="text-[11px] rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-2 py-1.5 outline-none">
                      <option value="sum">sum</option>
                      <option value="min">min</option>
                      <option value="all_or_nothing">all_or_nothing</option>
                    </select>
                    <button type="submit" disabled={isWorking} className="btn-outline text-[11px] h-8 px-2 disabled:opacity-50">
                      그룹 추가
                    </button>
                  </form>
                </div>

                <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
                  <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                    자산 ({assets.length}개)
                  </h3>
                  <p className="text-[11px] text-slate-500 leading-relaxed mb-2">
                    checker·validator·generator는 파이썬 소스(.py)만 등록됩니다.
                  </p>
                  <div className="space-y-2 max-h-40 overflow-y-auto pr-1 mb-3">
                    {assets.length === 0 ? (
                      <p className="text-[11px] text-slate-400 italic">등록된 자산이 없습니다.</p>
                    ) : (
                      assets.map((asset) => (
                        <div
                          key={asset.id}
                          className="flex items-center justify-between gap-2 p-2 rounded border border-slate-100 dark:border-slate-800"
                        >
                          <span className="text-[11px] text-slate-700 dark:text-slate-300 truncate">
                            <span className="font-bold">{asset.display_name}</span>
                            <span className="ml-2 text-slate-400">
                              {asset.asset_kind} · {Math.max(1, Math.round(asset.size_bytes / 1024))}KB
                            </span>
                          </span>
                          <button
                            onClick={() =>
                              void runAction(async (authToken) => {
                                const filename = await downloadProblemAsset(
                                  selectedProblem.id,
                                  selectedRevision.id,
                                  asset.id,
                                  asset.display_name,
                                  authToken,
                                );
                                return `${filename} 파일을 내려받았습니다.`;
                              }, '자산을 내려받지 못했습니다.')
                            }
                            disabled={isWorking}
                            className="text-slate-400 hover:text-accent transition-colors disabled:opacity-50"
                          >
                            <Download size={12} />
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                  <form
                    onSubmit={(event) => {
                      event.preventDefault();
                      const formElement = event.currentTarget;
                      const data = new FormData(formElement);
                      const file = data.get('asset_file');
                      if (!(file instanceof File)) {
                        setErrorMessage('업로드할 파일을 선택하십시오.');
                        return;
                      }
                      void runAction(async (authToken) => {
                        const asset = await uploadProblemAsset(
                          selectedProblem.id,
                          selectedRevision.id,
                          { assetKind: String(data.get('asset_kind') ?? 'attachment'), file },
                          authToken,
                        );
                        formElement.reset();
                        await loadTestcases();
                        return `자산 "${asset.display_name}"을(를) 올렸습니다.`;
                      }, '자산을 올리지 못했습니다.');
                    }}
                    className="grid grid-cols-3 gap-2"
                  >
                    <select name="asset_kind" className="text-[11px] rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-2 py-1.5 outline-none">
                      <option value="attachment">attachment</option>
                      <option value="checker">checker</option>
                      <option value="validator">validator</option>
                      <option value="generator">generator</option>
                      <option value="solution">solution</option>
                    </select>
                    <input name="asset_file" type="file" required className="text-[10px] file:mr-2 file:rounded file:border-0 file:bg-slate-200 dark:file:bg-slate-800 file:px-2 file:py-1 file:text-[10px] file:font-bold" />
                    <button type="submit" disabled={isWorking} className="btn-outline text-[11px] h-8 px-2 flex items-center justify-center gap-1.5 disabled:opacity-50">
                      <Upload size={12} />자산 업로드
                    </button>
                  </form>
                </div>

                <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
                  <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                    드라이런 (모범답안 시험 채점)
                  </h3>
                  <p className="text-[11px] text-slate-500 leading-relaxed mb-2">
                    샌드박스 자체 점검(hostile-fixture)을 통과한 환경에서만 실행됩니다.
                  </p>
                  <form
                    onSubmit={(event) => {
                      event.preventDefault();
                      const formElement = event.currentTarget;
                      const data = new FormData(formElement);
                      const sourceFile = data.get('source_file');
                      if (!(sourceFile instanceof File)) {
                        setErrorMessage('소스 파일을 선택하십시오.');
                        return;
                      }
                      void runAction(async (authToken) => {
                        const job = await createProblemDryRun(
                          selectedProblem.id,
                          selectedRevision.id,
                          { language: String(data.get('language') ?? 'python'), sourceFile },
                          authToken,
                        );
                        formElement.reset();
                        return `드라이런 작업 #${job.id}을(를) 등록했습니다. (상태: ${job.status})`;
                      }, '드라이런을 등록하지 못했습니다.');
                    }}
                    className="grid grid-cols-3 gap-2"
                  >
                    <select name="language" className="text-[11px] rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-2 py-1.5 outline-none">
                      {LANGUAGE_OPTIONS.map((language) => (
                        <option key={language} value={language}>
                          {language}
                        </option>
                      ))}
                    </select>
                    <input name="source_file" type="file" required className="text-[10px] file:mr-2 file:rounded file:border-0 file:bg-slate-200 dark:file:bg-slate-800 file:px-2 file:py-1 file:text-[10px] file:font-bold" />
                    <button type="submit" disabled={isWorking} className="btn-outline text-[11px] h-8 px-2 flex items-center justify-center gap-1.5 disabled:opacity-50">
                      <PlayCircle size={12} />드라이런 실행
                    </button>
                  </form>
                </div>
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
