'use client';

import { startTransition, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { UserPlus, LogIn, ShieldCheck } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';

export default function RegisterPage() {
  const { register, isLoading } = useAuth();
  const router = useRouter();
  const [formData, setFormData] = useState({
    id: '',
    sid: '',
    name: '',
    phone: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');
    if (formData.password !== formData.confirmPassword) {
      setErrorMessage('Password confirmation does not match.');
      return;
    }
    try {
      await register({
        id: formData.id,
        sid: Number(formData.sid),
        name: formData.name,
        phone: formData.phone,
        email: formData.email,
        password: formData.password,
      });
      setSuccessMessage('Account created. Redirecting...');
      startTransition(() => {
        router.push('/');
      });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Registration failed.');
    }
  };

  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="max-w-md w-full card-simple space-y-8 py-10 px-8">
        <header className="text-center">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center justify-center gap-2 mb-2">
            <UserPlus className="text-accent" size={24} />
            Create Account
          </h1>
          <p className="text-slate-500 text-sm font-medium">Join neoESPA to start your coding journey.</p>
        </header>

        {successMessage && (
          <div className="p-3 rounded bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-900/30 text-xs font-medium text-emerald-600 dark:text-emerald-400 text-center">
            {successMessage}
          </div>
        )}

        <form className="space-y-5" onSubmit={(e) => void handleSubmit(e)}>
          <div className="grid grid-cols-1 gap-4">
            <div>
              <label htmlFor="name" className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Full Name</label>
              <input id="name" name="name" type="text" required className="block w-full text-sm rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent" placeholder="Your real name" onChange={handleChange} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="id" className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">User ID</label>
                <input id="id" name="id" type="text" required className="block w-full text-sm rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent" placeholder="ID" onChange={handleChange} />
              </div>
              <div>
                <label htmlFor="sid" className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Student ID</label>
                <input id="sid" name="sid" type="text" required className="block w-full text-sm rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent" placeholder="20240001" onChange={handleChange} />
              </div>
            </div>
            <div>
              <label htmlFor="email" className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Email</label>
              <input id="email" name="email" type="email" required className="block w-full text-sm rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent" placeholder="email@university.ac.kr" onChange={handleChange} />
            </div>
            <div>
              <label htmlFor="phone" className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Phone</label>
              <input id="phone" name="phone" type="tel" required className="block w-full text-sm rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent" placeholder="010-0000-0000" onChange={handleChange} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="password" className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Password</label>
                <input id="password" name="password" type="password" required className="block w-full text-sm rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent" placeholder="••••••••" onChange={handleChange} />
              </div>
              <div>
                <label htmlFor="confirmPassword" className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Confirm</label>
                <input id="confirmPassword" name="confirmPassword" type="password" required className="block w-full text-sm rounded border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 px-3 py-2 outline-none focus:ring-1 focus:ring-accent" placeholder="••••••••" onChange={handleChange} />
              </div>
            </div>
          </div>

          {errorMessage && (
            <div className="p-3 rounded bg-rose-50 dark:bg-rose-950/20 border border-rose-100 dark:border-rose-900/30 text-xs font-medium text-rose-600 dark:text-rose-400">
              {errorMessage}
            </div>
          )}

          <button type="submit" disabled={isLoading} className="btn-flat w-full h-11 flex items-center justify-center gap-2 disabled:opacity-50 mt-4">
            {isLoading ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <ShieldCheck size={16} />}
            <span>Create Student Account</span>
          </button>
        </form>

        <footer className="pt-6 border-t border-slate-100 dark:border-slate-800 text-center">
          <p className="text-xs text-slate-500 font-medium">
            Already have an account?{' '}
            <Link href="/login" className="text-accent hover:underline font-bold inline-flex items-center gap-1">
              Sign in here <LogIn size={12} />
            </Link>
          </p>
        </footer>
      </div>
    </div>
  );
}
