'use client';

import { useEffect, useState } from 'react';
import { User, Key, Info, Shield, Mail, Phone, Hash } from 'lucide-react';

import AuthGate from '@/components/AuthGate';
import { useAuth } from '@/components/AuthProvider';
import { changeCurrentUserPassword } from '@/lib/api';

type ProfileFormState = {
  name: string;
  phone: string;
  email: string;
};

type PasswordFormState = {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
};

function ProfilePageContent() {
  const { user, token, updateProfile, isLoading } = useAuth();
  const [form, setForm] = useState<ProfileFormState>({
    name: '',
    phone: '',
    email: '',
  });
  const [passwordForm, setPasswordForm] = useState<PasswordFormState>({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [profileErrorMessage, setProfileErrorMessage] = useState('');
  const [profileSuccessMessage, setProfileSuccessMessage] = useState('');
  const [passwordErrorMessage, setPasswordErrorMessage] = useState('');
  const [passwordSuccessMessage, setPasswordSuccessMessage] = useState('');
  const [isProfileSubmitting, setIsProfileSubmitting] = useState(false);
  const [isPasswordSubmitting, setIsPasswordSubmitting] = useState(false);

  useEffect(() => {
    if (!user) return;
    setForm({ name: user.name, phone: user.phone, email: user.email });
  }, [user]);

  function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsProfileSubmitting(true);
    setProfileErrorMessage('');
    setProfileSuccessMessage('');
    try {
      await updateProfile({ name: form.name.trim(), phone: form.phone.trim(), email: form.email.trim() });
      setProfileSuccessMessage('Profile updated successfully.');
    } catch (error) {
      setProfileErrorMessage(error instanceof Error ? error.message : 'Failed to update profile.');
    } finally {
      setIsProfileSubmitting(false);
    }
  }

  function handlePasswordChange(event: React.ChangeEvent<HTMLInputElement>) {
    const { name, value } = event.target;
    setPasswordForm((current) => ({ ...current, [name]: value }));
  }

  async function handlePasswordSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPasswordErrorMessage('');
    setPasswordSuccessMessage('');
    if (!token) return;
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      setPasswordErrorMessage('Passwords do not match.');
      return;
    }
    setIsPasswordSubmitting(true);
    try {
      const response = await changeCurrentUserPassword({
        current_password: passwordForm.currentPassword,
        new_password: passwordForm.newPassword,
      }, token);
      setPasswordSuccessMessage(response.message);
      setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
    } catch (error) {
      setPasswordErrorMessage(error instanceof Error ? error.message : 'Failed to change password.');
    } finally {
      setIsPasswordSubmitting(false);
    }
  }

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-10">
      <header>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
          <User className="text-accent" size={24} />
          Account Profile
        </h1>
        <p className="text-slate-500 text-sm font-medium">Manage your personal information and account security.</p>
      </header>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: 'Username', value: user?.id, icon: User },
          { label: 'Student ID', value: user?.sid, icon: Hash },
          { label: 'Role', value: user?.user_group?.toUpperCase(), icon: Shield },
        ].map((item) => (
          <div key={item.label} className="card-simple py-4 px-5 bg-slate-50/50 dark:bg-slate-900/20 border-slate-100 dark:border-slate-800">
            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 flex items-center justify-between mb-1">
              {item.label}
              <item.icon size={12} className="opacity-50" />
            </span>
            <span className="text-lg font-bold text-slate-700 dark:text-slate-200">{item.value ?? '-'}</span>
          </div>
        ))}
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <form onSubmit={(event) => void handleSubmit(event)} className="card-simple space-y-6">
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-6 flex items-center gap-2">
              <User size={16} />
              Basic Information
            </h2>

            <div className="grid gap-6 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Name</label>
                <input name="name" value={form.name} onChange={handleChange} className="block w-full text-sm rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2.5 outline-none focus:ring-1 focus:ring-accent" required />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5"><Phone size={12} /> Phone</label>
                <input name="phone" value={form.phone} onChange={handleChange} className="block w-full text-sm rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2.5 outline-none focus:ring-1 focus:ring-accent" required />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5"><Mail size={12} /> Email</label>
                <input type="email" name="email" value={form.email} onChange={handleChange} className="block w-full text-sm rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2.5 outline-none focus:ring-1 focus:ring-accent" required />
              </div>
            </div>

            {(profileErrorMessage || profileSuccessMessage) && (
              <div className={`p-3 rounded text-xs font-medium border ${profileErrorMessage ? 'bg-rose-50 border-rose-100 text-rose-600 dark:bg-rose-950/20 dark:border-rose-900/30 dark:text-rose-400' : 'bg-emerald-50 border-emerald-100 text-emerald-600 dark:bg-emerald-950/20 dark:border-emerald-900/30 dark:text-emerald-400'}`}>
                {profileErrorMessage || profileSuccessMessage}
              </div>
            )}

            <div className="flex justify-end pt-4">
              <button type="submit" disabled={isProfileSubmitting || isLoading} className="btn-flat px-8 text-sm h-11 disabled:opacity-50">
                {isProfileSubmitting ? 'Saving...' : 'Update Profile'}
              </button>
            </div>
          </form>
        </div>

        <aside className="space-y-8">
          <form onSubmit={(event) => void handlePasswordSubmit(event)} className="card-simple space-y-5">
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-4">
              <Key size={16} />
              Security
            </h2>
            
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Current Password</label>
              <input type="password" name="currentPassword" value={passwordForm.currentPassword} onChange={handlePasswordChange} className="block w-full text-sm rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent" required />
            </div>
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">New Password</label>
              <input type="password" name="newPassword" value={passwordForm.newPassword} onChange={handlePasswordChange} className="block w-full text-sm rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent" required />
            </div>
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">Confirm New Password</label>
              <input type="password" name="confirmPassword" value={passwordForm.confirmPassword} onChange={handlePasswordChange} className="block w-full text-sm rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent" required />
            </div>

            {(passwordErrorMessage || passwordSuccessMessage) && (
              <div className={`p-3 rounded text-[11px] font-medium border ${passwordErrorMessage ? 'bg-rose-50 border-rose-100 text-rose-600 dark:bg-rose-950/20 dark:border-rose-900/30 dark:text-rose-400' : 'bg-emerald-50 border-emerald-100 text-emerald-600 dark:bg-emerald-950/20 dark:border-emerald-900/30 dark:text-emerald-400'}`}>
                {passwordErrorMessage || passwordSuccessMessage}
              </div>
            )}

            <button type="submit" disabled={isPasswordSubmitting || isLoading} className="btn-outline w-full h-10 text-xs bg-white dark:bg-transparent font-bold">
              {isPasswordSubmitting ? 'Updating...' : 'Change Password'}
            </button>
          </form>

          <section className="card-simple border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-900/10">
            <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400 flex items-center gap-2 mb-4">
              <Info size={14} />
              Profile Tips
            </h2>
            <ul className="space-y-3">
              <li className="text-[11px] text-slate-500 leading-relaxed">System IDs like Username and SID cannot be changed here.</li>
              <li className="text-[11px] text-slate-500 leading-relaxed">Ensure your email is valid to receive course notifications.</li>
              <li className="text-[11px] text-slate-500 leading-relaxed">Updating your profile will refresh your session information instantly.</li>
            </ul>
          </section>
        </aside>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  return (
    <AuthGate>
      <ProfilePageContent />
    </AuthGate>
  );
}
