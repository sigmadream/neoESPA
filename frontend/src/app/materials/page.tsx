'use client';

import { useEffect, useState } from 'react';
import { FileText, ExternalLink, User, Lock, Eye, MessageSquare, Send, Download } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import MarkdownContent from '@/components/MarkdownContent';
import { getMaterials, getMaterialAttachmentUrl, type LectureMaterialApi } from '@/lib/api';

export default function MaterialsPage() {
  const { token, user } = useAuth();
  const [materials, setMaterials] = useState<LectureMaterialApi[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [activeMaterialId, setActiveMaterialId] = useState<number | null>(null);
  const [commentText, setCommentText] = useState('');

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

  const handleAddComment = async (materialId: number) => {
    if (!token || !commentText.trim()) return;

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || ''}/api/materials/${materialId}/comments`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ content: commentText }),
      });

      if (!res.ok) {
        throw new Error('Failed to post comment');
      }

      const updatedMat: LectureMaterialApi = await res.json();
      setMaterials((prev) => prev.map((m) => (m.id === materialId ? updatedMat : m)));
      setCommentText('');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Error posting comment');
    }
  };

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-10">
      <header>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
          <FileText className="text-accent" size={24} />
          Learning Materials & Articles
        </h1>
        <p className="text-slate-500 text-sm font-medium">
          Access course slides, article materials, and download reference resources.
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

      <section className="space-y-6">
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
              className={`card-simple group transition-all hover:border-accent space-y-4 ${!material.is_published ? 'border-dashed opacity-80 bg-slate-50/50 dark:bg-slate-900/10' : ''}`}
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
                    {material.content && (
                      <div className="mt-3 p-4 bg-slate-50 dark:bg-slate-900 rounded-lg text-sm border border-slate-100 dark:border-slate-800">
                        <MarkdownContent content={material.content} />
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  {material.url && (
                    <a
                      href={material.url}
                      target="_blank"
                      rel="noreferrer"
                      className="btn-flat text-xs inline-flex items-center gap-2 whitespace-nowrap px-4 py-2"
                    >
                      <ExternalLink size={14} />
                      Open Link
                    </a>
                  )}
                  {material.attachment_name && (
                    <a
                      href={getMaterialAttachmentUrl(material.id)}
                      download={material.attachment_name}
                      className="btn-flat text-xs inline-flex items-center gap-2 whitespace-nowrap px-4 py-2"
                    >
                      <Download size={14} />
                      {material.attachment_name}
                    </a>
                  )}
                  <button
                    onClick={() => setActiveMaterialId(activeMaterialId === material.id ? null : material.id)}
                    className="text-xs text-slate-500 hover:text-accent flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 dark:border-slate-700 rounded-lg transition-colors"
                  >
                    <MessageSquare size={13} />
                    Comments ({material.comments?.length || 0})
                  </button>
                </div>
              </div>

              {activeMaterialId === material.id && (
                <div className="pt-4 border-t border-slate-100 dark:border-slate-800 space-y-4">
                  <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300">Comments</h4>
                  <div className="space-y-2">
                    {(material.comments || []).length === 0 ? (
                      <p className="text-xs text-slate-400 italic">No comments yet. Be the first to leave a comment!</p>
                    ) : (
                      material.comments?.map((comment) => (
                        <div key={comment.id} className="p-3 bg-slate-50 dark:bg-slate-900 rounded-lg text-xs space-y-1">
                          <div className="flex justify-between font-semibold text-slate-700 dark:text-slate-300">
                            <span>{comment.user_name || comment.user_id}</span>
                            <span className="text-[10px] text-slate-400">
                              {new Date(comment.created_at).toLocaleString()}
                            </span>
                          </div>
                          <p className="text-slate-600 dark:text-slate-400">{comment.content}</p>
                        </div>
                      ))
                    )}
                  </div>

                  {token && (
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={commentText}
                        onChange={(e) => setCommentText(e.target.value)}
                        placeholder="Write a comment..."
                        className="flex-1 text-xs px-3 py-2 border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-900 focus:outline-none focus:border-accent"
                      />
                      <button
                        onClick={() => void handleAddComment(material.id)}
                        className="px-4 py-2 bg-accent text-white text-xs font-semibold rounded-lg flex items-center gap-1 hover:bg-accent/90"
                      >
                        <Send size={12} /> Post
                      </button>
                    </div>
                  )}
                </div>
              )}
            </article>
          ))
        )}
      </section>
    </div>
  );
}
