'use client';

import { useEffect, useState } from 'react';
import { HelpCircle, Lock, MessageCircle, Plus, Send, User } from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';

type QAAnswer = {
  id: number;
  post_id: number;
  author_id: string;
  author_name: string | null;
  content: string;
  created_at: string;
};

type QAPost = {
  id: number;
  title: string;
  content: string;
  is_private: boolean;
  author_id: string;
  author_name: string | null;
  answers: QAAnswer[];
  created_at: string;
};

export default function QAPage() {
  const { token } = useAuth();
  const [posts, setPosts] = useState<QAPost[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newContent, setNewContent] = useState('');
  const [newIsPrivate, setNewIsPrivate] = useState(false);

  const [activePostId, setActivePostId] = useState<number | null>(null);
  const [answerText, setAnswerText] = useState('');

  const fetchPosts = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || ''}/api/qa`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.ok) {
        const data: QAPost[] = await res.json();
        setPosts(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void fetchPosts();
  }, [token]);

  const handleCreatePost = async () => {
    if (!token || !newTitle.trim() || !newContent.trim()) return;

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || ''}/api/qa`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          title: newTitle,
          content: newContent,
          is_private: newIsPrivate,
        }),
      });

      if (res.ok) {
        setShowCreateModal(false);
        setNewTitle('');
        setNewContent('');
        setNewIsPrivate(false);
        void fetchPosts();
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to post question');
    }
  };

  const handleAddAnswer = async (postId: number) => {
    if (!token || !answerText.trim()) return;

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || ''}/api/qa/${postId}/answers`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ content: answerText }),
      });

      if (res.ok) {
        const updatedPost: QAPost = await res.json();
        setPosts((prev) => prev.map((p) => (p.id === postId ? updatedPost : p)));
        setAnswerText('');
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to add answer');
    }
  };

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
            <HelpCircle className="text-accent" size={24} />
            Question & Answer Forum
          </h1>
          <p className="text-slate-500 text-sm">
            Ask questions regarding assignments, lectures, or system issues.
          </p>
        </div>

        {token && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-accent text-white font-semibold rounded-lg text-xs hover:bg-accent/90 transition-colors shadow-sm"
          >
            <Plus size={14} /> Ask Question
          </button>
        )}
      </div>

      {showCreateModal && (
        <div className="card-simple p-6 border-accent/30 space-y-4">
          <h3 className="text-base font-bold text-slate-900 dark:text-white">Ask a New Question</h3>
          <input
            type="text"
            placeholder="Question Title"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            className="w-full text-xs p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900"
          />
          <textarea
            placeholder="Describe your question in detail..."
            value={newContent}
            onChange={(e) => setNewContent(e.target.value)}
            rows={4}
            className="w-full text-xs p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900"
          />
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400 cursor-pointer">
              <input
                type="checkbox"
                checked={newIsPrivate}
                onChange={(e) => setNewIsPrivate(e.target.checked)}
                className="rounded border-slate-300 text-accent focus:ring-accent"
              />
              Private Question (Visible only to instructors and yourself)
            </label>

            <div className="flex gap-2">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 text-xs font-semibold rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={() => void handleCreatePost()}
                className="px-4 py-2 bg-accent text-white text-xs font-semibold rounded-lg"
              >
                Submit
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-4">
        {isLoading ? (
          <div className="text-center py-12 text-slate-400 text-xs">Loading Q&A discussions...</div>
        ) : posts.length === 0 ? (
          <div className="card-simple text-center py-16 border-dashed text-slate-400 text-xs">
            No questions posted yet.
          </div>
        ) : (
          posts.map((post) => (
            <div key={post.id} className="card-simple space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    {post.is_private && (
                      <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-rose-100 text-rose-700 dark:bg-rose-950/30 dark:text-rose-400 font-bold">
                        <Lock size={10} /> Private
                      </span>
                    )}
                    <span className="text-[11px] text-slate-400 font-medium flex items-center gap-1">
                      <User size={12} /> {post.author_name || post.author_id}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      • {new Date(post.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">{post.title}</h2>
                  <p className="mt-2 text-sm text-slate-600 dark:text-slate-300 whitespace-pre-wrap">
                    {post.content}
                  </p>
                </div>

                <button
                  onClick={() => setActivePostId(activePostId === post.id ? null : post.id)}
                  className="text-xs text-slate-500 hover:text-accent flex items-center gap-1 px-3 py-1.5 border border-slate-200 dark:border-slate-700 rounded-lg"
                >
                  <MessageCircle size={13} /> Answers ({post.answers.length})
                </button>
              </div>

              {activePostId === post.id && (
                <div className="pt-4 border-t border-slate-100 dark:border-slate-800 space-y-4">
                  <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300">Answers & Thread</h4>
                  <div className="space-y-2">
                    {post.answers.length === 0 ? (
                      <p className="text-xs text-slate-400 italic">No answers posted yet.</p>
                    ) : (
                      post.answers.map((ans) => (
                        <div key={ans.id} className="p-3 bg-slate-50 dark:bg-slate-900 rounded-lg text-xs space-y-1">
                          <div className="flex justify-between font-semibold text-slate-700 dark:text-slate-300">
                            <span>{ans.author_name || ans.author_id}</span>
                            <span className="text-[10px] text-slate-400">
                              {new Date(ans.created_at).toLocaleString()}
                            </span>
                          </div>
                          <p className="text-slate-600 dark:text-slate-400 whitespace-pre-wrap">{ans.content}</p>
                        </div>
                      ))
                    )}
                  </div>

                  {token && (
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={answerText}
                        onChange={(e) => setAnswerText(e.target.value)}
                        placeholder="Write your answer..."
                        className="flex-1 text-xs px-3 py-2 border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-900 focus:outline-none focus:border-accent"
                      />
                      <button
                        onClick={() => void handleAddAnswer(post.id)}
                        className="px-4 py-2 bg-accent text-white text-xs font-semibold rounded-lg flex items-center gap-1 hover:bg-accent/90"
                      >
                        <Send size={12} /> Post Answer
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
