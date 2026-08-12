'use client';

import { useEffect, startTransition, useState } from 'react';
import { Search, Filter, RefreshCw, UserPlus, Save, Power, Key, Users, CheckCircle2, Shield } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import {
  bulkCreateAdminUsers,
  getAdminUsers,
  resetAdminUserPassword,
  updateAdminUserRole,
  updateAdminUserStatus,
  type AdminUserApi,
  type BulkAdminUserEntry,
  type UserRole,
} from '@/lib/api';

const ROLE_OPTIONS: UserRole[] = ['student', 'ta', 'instructor', 'admin'];

function parseBulkUsers(input: string): BulkAdminUserEntry[] {
  const rows = input.split('\n').map((line) => line.trim()).filter(Boolean);
  if (rows.length === 0) throw new Error('Add at least one user row.');
  return rows.map((row, index) => {
    const [id, sid, name, email, phone, role = 'student', password] = row.split(',').map((v) => v.trim());
    if (!id || !sid || !name || !email || !phone) throw new Error(`Row ${index + 1} incomplete.`);
    if (!ROLE_OPTIONS.includes(role as UserRole)) throw new Error(`Row ${index + 1} invalid role: ${role}`);
    return { id, sid: Number(sid), name, email, phone, user_group: role as UserRole, ps: password || null, is_active: true };
  });
}

export default function AdminUserManager() {
  const { token, user } = useAuth();
  const [users, setUsers] = useState<AdminUserApi[]>([]);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<UserRole | 'all'>('all');
  const [activeFilter, setActiveFilter] = useState<'all' | 'active' | 'inactive'>('all');
  const [roleDrafts, setRoleDrafts] = useState<Record<string, UserRole>>({});
  const [bulkText, setBulkText] = useState('');
  const [defaultPassword, setDefaultPassword] = useState('welcome1234');
  const [isLoading, setIsLoading] = useState(true);
  const [busyUserId, setBusyUserId] = useState<string | null>(null);
  const [isBulkSaving, setIsBulkSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const loadUsers = async () => {
    if (!token || user?.user_group !== 'admin') return;
    setIsLoading(true);
    setErrorMessage('');
    try {
      const response = await getAdminUsers(token, {
        search,
        role: roleFilter,
        is_active: activeFilter === 'all' ? 'all' : activeFilter === 'active',
      });
      setUsers(response);
      setRoleDrafts(Object.fromEntries(response.map((u) => [u.id, u.user_group as UserRole])));
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to load users.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadUsers();
  }, [activeFilter, roleFilter, search, token, user?.user_group]);

  async function handleRoleSave(managedUser: AdminUserApi) {
    if (!token) return;
    const nextRole = roleDrafts[managedUser.id] ?? (managedUser.user_group as UserRole);
    if (nextRole === managedUser.user_group) return;
    setBusyUserId(managedUser.id);
    try {
      await updateAdminUserRole(managedUser.id, { user_group: nextRole }, token);
      setSuccessMessage(`Updated role for ${managedUser.id}.`);
      await loadUsers();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Update failed.');
    } finally {
      setBusyUserId(null);
    }
  }

  async function handleStatusToggle(managedUser: AdminUserApi) {
    if (!token) return;
    setBusyUserId(managedUser.id);
    try {
      await updateAdminUserStatus(managedUser.id, { is_active: !managedUser.is_active }, token);
      setSuccessMessage(`${managedUser.id} updated.`);
      await loadUsers();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Status update failed.');
    } finally {
      setBusyUserId(null);
    }
  }

  async function handlePasswordReset(managedUser: AdminUserApi) {
    if (!token) return;
    const nextPassword = window.prompt(`New password for ${managedUser.id}`, 'welcome1234');
    if (!nextPassword?.trim()) return;
    setBusyUserId(managedUser.id);
    try {
      await resetAdminUserPassword(managedUser.id, { new_password: nextPassword.trim() }, token);
      setSuccessMessage(`Password reset for ${managedUser.id}.`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Reset failed.');
    } finally {
      setBusyUserId(null);
    }
  }

  async function handleBulkCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setIsBulkSaving(true);
    setErrorMessage('');
    try {
      const parsed = parseBulkUsers(bulkText);
      const response = await bulkCreateAdminUsers({ users: parsed, default_password: defaultPassword.trim(), skip_existing: true }, token);
      setSuccessMessage(`Created ${response.created_count} users.`);
      setBulkText('');
      await loadUsers();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Bulk registration failed.');
    } finally {
      setIsBulkSaving(false);
    }
  }

  if (user?.user_group !== 'admin') return <div className="card-simple bg-slate-50 dark:bg-slate-900/20 border-dashed text-center py-12"><p className="text-slate-500 font-medium">최고 관리자(System Administrator) 권한 전용 메뉴입니다.</p></div>;

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: '전체 등록 계정', value: `${users.length}명`, icon: Users },
          { label: '활성 계정 수', value: `${users.filter(u => u.is_active).length}명`, icon: CheckCircle2 },
          { label: '관리자 및 교직원', value: `${users.filter(u => ['admin', 'instructor', 'ta'].includes(u.user_group)).length}명`, icon: Shield },
        ].map((stat) => (
          <div key={stat.label} className="card-simple flex flex-col justify-between py-4 px-5">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 flex items-center justify-between">
              {stat.label}
              <stat.icon size={12} className="opacity-50" />
            </span>
            <span className="text-2xl font-black text-slate-900 dark:text-white mt-2">{stat.value}</span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
        <div className="xl:col-span-2 space-y-6">
          <section className="card-simple">
            <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
              <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400">사용자 계정 디렉토리</h2>
              <div className="flex items-center gap-2">
                <button onClick={() => void loadUsers()} className="p-2 rounded hover:bg-slate-50 dark:hover:bg-slate-900 text-slate-400 hover:text-accent transition-all"><RefreshCw size={16} /></button>
              </div>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
              <div className="relative md:col-span-1">
                <Search size={14} className="absolute left-3 top-3 text-slate-400" />
                <input value={search} onChange={(e) => setSearch(e.target.value)} className="w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 pl-9 pr-3 py-2.5 outline-none focus:ring-1 focus:ring-accent" placeholder="이름, 아이디, 학번 검색..." />
              </div>
              <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value as UserRole | 'all')} className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2.5 outline-none">
                <option value="all">전체 권한 보기</option>
                {ROLE_OPTIONS.map(r => <option key={r} value={r}>{r.toUpperCase()}</option>)}
              </select>
              <select value={activeFilter} onChange={(e) => setActiveFilter(e.target.value as 'all' | 'active' | 'inactive')} className="text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2.5 outline-none">
                <option value="all">전체 상태 보기</option>
                <option value="active">활성화 계정</option>
                <option value="inactive">비활성화 계정</option>
              </select>
            </div>

            {(errorMessage || successMessage) && (
              <div className={`p-3 rounded text-[11px] font-medium mb-6 border ${errorMessage ? 'bg-rose-50 border-rose-100 text-rose-600 dark:bg-rose-950/20' : 'bg-emerald-50 border-emerald-100 text-emerald-600 dark:bg-emerald-950/20'}`}>
                {errorMessage || successMessage}
              </div>
            )}

            <div className="overflow-x-auto rounded border border-slate-100 dark:border-slate-800">
              <table className="min-w-full divide-y divide-slate-100 dark:divide-slate-800">
                <thead className="bg-slate-50 dark:bg-slate-900/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-widest text-slate-400">계정 정보 (이름, ID, 학번)</th>
                    <th className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-widest text-slate-400">권한 역할</th>
                    <th className="px-4 py-3 text-right text-[10px] font-bold uppercase tracking-widest text-slate-400">계정 관리</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50 dark:divide-slate-900 bg-white dark:bg-slate-950/20">
                  {isLoading ? (
                    <tr><td colSpan={3} className="px-4 py-10 text-center text-xs text-slate-400 animate-pulse">사용자 목록을 불러오는 중입니다...</td></tr>
                  ) : users.length === 0 ? (
                    <tr><td colSpan={3} className="px-4 py-10 text-center text-xs text-slate-400 italic">검색 조건에 맞는 사용자가 없습니다.</td></tr>
                  ) : (
                    users.map((u) => (
                      <tr key={u.id} className="group hover:bg-slate-50/50 dark:hover:bg-slate-900/30 transition-colors">
                        <td className="px-4 py-4">
                          <div className="font-bold text-sm text-slate-900 dark:text-slate-100">{u.name}</div>
                          <div className="text-[10px] text-slate-400 font-mono mt-0.5">{u.id} · 학번 {u.sid}</div>
                          <div className="text-[10px] text-slate-500 mt-1">{u.email}</div>
                        </td>
                        <td className="px-4 py-4">
                          <div className="flex items-center gap-2">
                            <select value={roleDrafts[u.id] ?? u.user_group} onChange={(e) => setRoleDrafts({...roleDrafts, [u.id]: e.target.value as UserRole})} className="text-[11px] rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 px-2 py-1 outline-none focus:ring-1 focus:ring-accent font-medium">
                              {ROLE_OPTIONS.map(r => <option key={r} value={r}>{r}</option>)}
                            </select>
                            <button onClick={() => void handleRoleSave(u)} disabled={busyUserId === u.id} className="p-1.5 rounded hover:bg-white dark:hover:bg-slate-800 text-slate-300 hover:text-accent border border-transparent hover:border-slate-100 transition-all" title="권한 저장"><Save size={12} /></button>
                          </div>
                        </td>
                        <td className="px-4 py-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button onClick={() => void handleStatusToggle(u)} disabled={busyUserId === u.id} className={`p-1.5 rounded transition-all ${u.is_active ? 'text-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-950/30' : 'text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-900'}`} title="계정 활성화/비활성화"><Power size={14} /></button>
                            <button onClick={() => void handlePasswordReset(u)} disabled={busyUserId === u.id} className="p-1.5 rounded hover:bg-amber-50 dark:hover:bg-amber-950/30 text-amber-500 transition-all" title="비밀번호 초기화"><Key size={14} /></button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <aside className="space-y-6">
          <section className="card-simple">
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-6 flex items-center gap-2">
              <UserPlus size={16} />
              사용자 일괄 등록 (CSV)
            </h2>
            <form onSubmit={(e) => void handleBulkCreate(e)} className="space-y-5">
              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">기본 비밀번호</label>
                <input value={defaultPassword} onChange={(e) => setDefaultPassword(e.target.value)} className="w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none" />
              </div>
              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">CSV 데이터 (아이디,학번,이름,이메일,전화번호)</label>
                <textarea value={bulkText} onChange={(e) => setBulkText(e.target.value)} rows={12} className="w-full text-xs rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 font-mono outline-none" placeholder="student01,20250001,홍길동,hong@example.com,010-0000-0000" />
              </div>
              <button type="submit" disabled={isBulkSaving} className="btn-flat w-full h-11 text-xs font-bold uppercase tracking-widest disabled:opacity-50">
                {isBulkSaving ? '처리 중...' : '사용자 일괄 등록하기'}
              </button>
            </form>
          </section>
        </aside>
      </div>
    </div>
  );
}
