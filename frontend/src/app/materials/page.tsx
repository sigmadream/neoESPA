'use client';

import { useEffect, useState } from 'react';
import { FileText, ExternalLink, User, Lock, Eye } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import { getMaterials, type LectureMaterialApi } from '@/lib/api';

export default function MaterialsPage() {
  const { token, user } = useAuth();
  const [materials, setMaterials] = useState<LectureMaterialApi[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    let isMounted = true;
    async function loadMaterials() {
      setIsLoading(true);
      try {
        const response = await getMaterials(token);
        if (isMounted) setMaterials(response);
      } catch (error) {
        if (isMounted) setErrorMessage(error instanceof Error ? error.message : 'Failed to load materials.');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }
    void loadMaterials();
    return () => { isMounted = false; };
  }, [token]);

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-10">
      <header>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
          <FileText className="text-accent" size={24} />
          Learning Materials
        </h1>
        <p className="text-slate-500 text-sm font-medium">
          Access course slides, lab instructions, and reference guides.
          {user && ['admin', 'instructor', 'ta'].includes(user.user_group) && (
            <span className="text-accent ml-1 font-bold">· Admin View Active</span>
          )}
        </p>
      </header>

      {errorMessage && (
        <div className="card-simple border-rose-100 bg-rose-50 dark:bg-rose-950/20 text-rose-600 dark:text-rose-400 text-sm font-medium">
          {errorMessage}
        </div>
      )}

      <section className="space-y-4">
        {isLoading ? (
          <div className="space-y-4">
            {[...Array(2)].map((_, i) => (
              <div key={i} className="h-32 w-full bg-slate-50 dark:bg-slate-900 animate-pulse rounded-md border border-slate-100 dark:border-slate-800" />
            ))}
          </div>
        ) : materials.length === 0 ? (
          <div className="card-simple text-center py-16 border-dashed">
            <p className="text-slate-400 text-sm italic">No materials available at the moment.</p>
          </div>
        ) : (
          materials.map((material) => (
            <article
              key={material.id}
              className={`card-simple group transition-all hover:border-accent ${!material.is_published ? 'border-dashed opacity-80 bg-slate-50/50 dark:bg-slate-900/10' : ''}`}
            >
              <div className="flex flex-col sm:flex-row items-start justify-between gap-6">
                <div className="flex-1 space-y-3">
                  <div className="flex flex-wrap items-center gap-3">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider flex items-center gap-1 ${
                        material.is_published
                          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400'
                          : 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400'
                      }`}
                    >
                      {material.is_published ? <Eye size={10} /> : <Lock size={10} />}
                      {material.is_published ? 'Published' : 'Draft'}
                    </span>
                    <span className="text-[11px] text-slate-400 font-medium flex items-center gap-1">
                      <User size={12} /> {material.created_by}
                    </span>
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 group-hover:text-accent transition-colors">
                      {material.title}
                    </h2>
                    <p className="mt-1.5 text-sm text-slate-500 dark:text-slate-400 leading-relaxed max-w-3xl">
                      {material.description}
                    </p>
                  </div>
                </div>

                <a
                  href={material.url}
                  target="_blank"
                  rel="noreferrer"
                  className="btn-flat text-xs inline-flex items-center gap-2 whitespace-nowrap self-start sm:self-center px-5"
                >
                  <ExternalLink size={14} />
                  Open Material
                </a>
              </div>
            </article>
          ))
        )}
      </section>
    </div>
  );
}
