'use client';

import { useEffect, useState } from 'react';
import { Settings, Save, RefreshCw, Sliders, CheckCircle2, AlertCircle } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import {
  getAdminSettings,
  updateAdminSettings,
  type SystemSettingApi,
} from '@/lib/api';

const LINT_SETTING_ORDER = [
  'lint_calc_weight',
  'lint_calc_panalty',
  'lint_err_issue',
  'lint_err_style',
  'lint_err_performance',
  'lint_err_information',
  'lint_set_default',
] as const;

const SETTING_KOREAN_META: Record<string, { title: string; description: string }> = {
  lint_calc_weight: {
    title: '코드 품질 점수 반영 가중치',
    description: '코드 품질 검사(Lint) 결과가 과제 전체 총점에 반영되는 최대 가중치 점수입니다.',
  },
  lint_calc_panalty: {
    title: '품질 감점 차등 비율',
    description: '품질 지침을 위반했을 때 차감되는 개별 페널티 단위 비율입니다.',
  },
  lint_err_issue: {
    title: '주요 결함 이슈 감점 기준',
    description: '구문 오류 및 심각한 코드 로직 이슈 발생 시 차감할 점수입니다.',
  },
  lint_err_style: {
    title: '코드 스타일 위반 감점 기준',
    description: '들여쓰기, 표기법 등 가독성 스타일 규격 위반 시 차감할 점수입니다.',
  },
  lint_err_performance: {
    title: '성능 비효율 감점 기준',
    description: '비효율적인 반복문 및 성능 저하 소스 코드 발견 시 차감할 점수입니다.',
  },
  lint_err_information: {
    title: '정보성 권고 감점 기준',
    description: '단순 개선 권장 사항 및 정보성 경고 감점 점수입니다.',
  },
  lint_set_default: {
    title: '신규 과제 등록 시 품질검사 기본 적용',
    description: '새로운 과제를 생성할 때 기본적으로 코드 품질 검사(Lint) 기능을 활성화할지 여부입니다.',
  },
};

type FormValue = string | boolean;

function orderSettings(settings: SystemSettingApi[]) {
  const orderMap = new Map<string, number>(LINT_SETTING_ORDER.map((k, i) => [k, i]));
  return [...settings].sort((a, b) => (orderMap.get(a.key) ?? 99) - (orderMap.get(b.key) ?? 99));
}

export default function AdminSettingsManager() {
  const { token, user } = useAuth();
  const [settings, setSettings] = useState<SystemSettingApi[]>([]);
  const [formValues, setFormValues] = useState<Record<string, FormValue>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const loadSettings = async () => {
    if (!token || user?.user_group !== 'admin') return;
    setIsLoading(true);
    try {
      const response = await getAdminSettings(token, { prefix: 'lint_' });
      const ordered = orderSettings(response);
      setSettings(ordered);
      setFormValues(Object.fromEntries(ordered.map(s => [s.key, s.value_type === 'boolean' ? s.value === 'true' : s.value])));
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Load failed.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { void loadSettings(); }, [token, user?.user_group]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setIsSaving(true);
    setErrorMessage('');
    try {
      const payload = settings.map(s => ({
        key: s.key,
        value: s.value_type === 'boolean' ? Boolean(formValues[s.key]) : Number(formValues[s.key])
      }));
      await updateAdminSettings({ settings: payload }, token);
      setSuccessMessage('Settings updated.');
      await loadSettings();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Update failed.');
    } finally {
      setIsSaving(false);
    }
  };

  if (user?.user_group !== 'admin') return <div className="card-simple bg-slate-50 dark:bg-slate-900/20 border-dashed text-center py-12"><p className="text-slate-500 font-medium">최고 관리자(System Administrator) 권한 전용 메뉴입니다.</p></div>;

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: '설정 항목 수', value: `${settings.length}개`, icon: Settings },
          { label: '린트 가중치', value: formValues.lint_calc_weight ?? '-', icon: Sliders },
          { label: '기본 적용 모드', value: formValues.lint_set_default ? '활성화' : '비활성화', icon: CheckCircle2 },
        ].map((stat) => (
          <div key={stat.label} className="card-simple py-4 px-5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 flex items-center justify-between mb-1">
              {stat.label}
              <stat.icon size={12} className="opacity-50" />
            </span>
            <span className="text-2xl font-black text-slate-900 dark:text-white">{stat.value}</span>
          </div>
        ))}
      </div>

      <section className="card-simple">
        <header className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400">전역 시스템 환경설정</h2>
            <p className="text-[11px] text-slate-500 mt-1">채점 가중치 및 코드 품질 검사(Lint) 규칙을 설정합니다.</p>
          </div>
          <button onClick={() => void loadSettings()} className="p-1.5 rounded hover:bg-slate-50 dark:hover:bg-slate-900 text-slate-400 transition-all"><RefreshCw size={14} /></button>
        </header>

        {(errorMessage || successMessage) && (
          <div className={`p-3 rounded text-[11px] font-medium mb-8 border ${errorMessage ? 'bg-rose-50 border-rose-100 text-rose-600 dark:bg-rose-950/20' : 'bg-emerald-50 border-emerald-100 text-emerald-600 dark:bg-emerald-950/20'}`}>
            {errorMessage || successMessage}
          </div>
        )}

        {isLoading ? (
          <div className="py-12 text-center text-xs text-slate-400 animate-pulse">시스템 설정을 동기화 중입니다...</div>
        ) : (
          <form onSubmit={(e) => void handleSubmit(e)} className="space-y-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {settings.filter(s => s.value_type === 'number').map((s) => {
                const meta = SETTING_KOREAN_META[s.key];
                return (
                  <div key={s.key} className="p-4 rounded border border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-950/20">
                    <div className="flex items-start justify-between gap-4 mb-3">
                      <div className="min-w-0">
                        <label className="text-xs font-bold text-slate-700 dark:text-slate-200 block truncate">
                          {meta?.title ?? s.key} <span className="text-[10px] text-slate-400 font-mono">({s.key})</span>
                        </label>
                        <p className="text-[10px] text-slate-500 leading-relaxed mt-1">{meta?.description ?? s.description}</p>
                      </div>
                    </div>
                    <input
                      type="number" step="0.1" min="0"
                      value={String(formValues[s.key] ?? '')}
                      onChange={e => setFormValues({...formValues, [s.key]: e.target.value})}
                      className="block w-full text-sm rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent font-medium"
                    />
                  </div>
                );
              })}
            </div>

            <div className="p-5 rounded border border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-950/20 flex items-center gap-4">
              <input
                type="checkbox"
                checked={Boolean(formValues.lint_set_default)}
                onChange={e => setFormValues({...formValues, lint_set_default: e.target.checked})}
                className="h-4 w-4 rounded border-slate-300 text-accent focus:ring-accent cursor-pointer"
              />
              <div className="min-w-0">
                <label className="text-xs font-bold text-slate-700 dark:text-slate-200 block">
                  {SETTING_KOREAN_META['lint_set_default']?.title ?? 'lint_set_default'} <span className="text-[10px] text-slate-400 font-mono">(lint_set_default)</span>
                </label>
                <p className="text-[10px] text-slate-500 leading-relaxed">{SETTING_KOREAN_META['lint_set_default']?.description ?? settings.find(s => s.key === 'lint_set_default')?.description}</p>
              </div>
            </div>

            <button type="submit" disabled={isSaving} className="btn-flat w-full h-12 flex items-center justify-center gap-2 shadow-sm disabled:opacity-50">
              {isSaving ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Save size={16} />}
              <span>전역 시스템 설정 적용하기</span>
            </button>
          </form>
        )}
      </section>
    </div>
  );
}
