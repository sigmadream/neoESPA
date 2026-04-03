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

  if (user?.user_group !== 'admin') return <div className="card-simple bg-slate-50 dark:bg-slate-900/20 border-dashed text-center py-12"><p className="text-slate-500 font-medium">Restricted to system administrators.</p></div>;

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: 'Config Count', value: settings.length, icon: Settings },
          { label: 'Lint Weight', value: formValues.lint_calc_weight ?? '-', icon: Sliders },
          { label: 'Default Mode', value: formValues.lint_set_default ? 'ON' : 'OFF', icon: CheckCircle2 },
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
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400">System Configuration</h2>
            <p className="text-[11px] text-slate-500 mt-1">Global grading weights and linting rules.</p>
          </div>
          <button onClick={() => void loadSettings()} className="p-1.5 rounded hover:bg-slate-50 dark:hover:bg-slate-900 text-slate-400 transition-all"><RefreshCw size={14} /></button>
        </header>

        {(errorMessage || successMessage) && (
          <div className={`p-3 rounded text-[11px] font-medium mb-8 border ${errorMessage ? 'bg-rose-50 border-rose-100 text-rose-600 dark:bg-rose-950/20' : 'bg-emerald-50 border-emerald-100 text-emerald-600 dark:bg-emerald-950/20'}`}>
            {errorMessage || successMessage}
          </div>
        )}

        {isLoading ? (
          <div className="py-12 text-center text-xs text-slate-400 animate-pulse">Syncing configuration...</div>
        ) : (
          <form onSubmit={(e) => void handleSubmit(e)} className="space-y-8">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {settings.filter(s => s.value_type === 'number').map((s) => (
                <div key={s.key} className="p-4 rounded border border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-950/20">
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <div className="min-w-0">
                      <label className="text-xs font-bold text-slate-700 dark:text-slate-200 block truncate font-mono">{s.key}</label>
                      <p className="text-[10px] text-slate-500 leading-relaxed mt-1">{s.description}</p>
                    </div>
                  </div>
                  <input
                    type="number" step="0.1" min="0"
                    value={String(formValues[s.key] ?? '')}
                    onChange={e => setFormValues({...formValues, [s.key]: e.target.value})}
                    className="block w-full text-sm rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent"
                  />
                </div>
              ))}
            </div>

            <div className="p-5 rounded border border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-950/20 flex items-center gap-4">
              <input
                type="checkbox"
                checked={Boolean(formValues.lint_set_default)}
                onChange={e => setFormValues({...formValues, lint_set_default: e.target.checked})}
                className="h-4 w-4 rounded border-slate-300 text-accent focus:ring-accent cursor-pointer"
              />
              <div className="min-w-0">
                <label className="text-xs font-bold text-slate-700 dark:text-slate-200 block font-mono">lint_set_default</label>
                <p className="text-[10px] text-slate-500 leading-relaxed">{settings.find(s => s.key === 'lint_set_default')?.description}</p>
              </div>
            </div>

            <button type="submit" disabled={isSaving} className="btn-flat w-full h-12 flex items-center justify-center gap-2 shadow-sm disabled:opacity-50">
              {isSaving ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Save size={16} />}
              <span>Apply Global Settings</span>
            </button>
          </form>
        )}
      </section>
    </div>
  );
}
