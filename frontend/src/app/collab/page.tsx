'use client';

import { useEffect, useRef, useState } from 'react';

import AuthGate from '@/components/AuthGate';
import { useAuth } from '@/components/AuthProvider';
import {
  COOKIE_SESSION_TOKEN,
  createCollabSession,
  getRealtimeBaseUrl,
  getCollabSessions,
  joinCollabSession,
  postCollabMessage,
  type CollabMessageApi,
  type CollabSessionApi,
} from '@/lib/api';

function toWebSocketUrl(baseUrl: string) {
  if (baseUrl.startsWith('https://')) {
    return baseUrl.replace('https://', 'wss://');
  }
  return baseUrl.replace('http://', 'ws://');
}

function CollabPageContent() {
  const { token, user } = useAuth();
  const [sessions, setSessions] = useState<CollabSessionApi[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [activeSession, setActiveSession] = useState<CollabSessionApi | null>(null);
  const [code, setCode] = useState('');
  const [chatInput, setChatInput] = useState('');
  const [messages, setMessages] = useState<CollabMessageApi[]>([]);
  const [newSessionTitle, setNewSessionTitle] = useState('Mentoring Session');
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const socketRef = useRef<WebSocket | null>(null);

  const isStaff = ['admin', 'instructor', 'ta'].includes(user?.user_group ?? '');
  const canEdit = Boolean(
    activeSession?.participants.some(
      (participant) => participant.user_id === user?.id && participant.can_edit,
    ),
  );

  useEffect(() => {
    if (!token) {
      return;
    }
    const authToken: string = token;

    let isMounted = true;

    async function loadSessions() {
      setIsLoading(true);
      setErrorMessage('');

      try {
        const response = await getCollabSessions(authToken);
        if (isMounted) {
          setSessions(response);
          if (!selectedSessionId && response[0]) {
            setSelectedSessionId(response[0].id);
          }
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(
            error instanceof Error ? error.message : 'Failed to load sessions.',
          );
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadSessions();

    return () => {
      isMounted = false;
    };
  }, [selectedSessionId, token]);

  useEffect(() => {
    if (!token || !selectedSessionId || !activeSession) {
      return;
    }

    const realtimeBaseUrl = getRealtimeBaseUrl();
    const ws = new WebSocket(
      `${toWebSocketUrl(realtimeBaseUrl)}/ws/collab/sessions/${selectedSessionId}${token === COOKIE_SESSION_TOKEN ? '' : `?token=${token}`}`,
    );
    socketRef.current = ws;

    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data) as
        | { type: 'session_state'; code: string }
        | { type: 'code_update'; code: string }
        | { type: 'chat'; user_id: string; content: string }
        | { type: 'error'; detail: string };

      if (payload.type === 'session_state' || payload.type === 'code_update') {
        setCode(payload.code);
        return;
      }

      if (payload.type === 'chat') {
        setMessages((current) => [
          ...current,
          {
            id: Date.now(),
            session_id: selectedSessionId,
            user_id: payload.user_id,
            content: payload.content,
            created_at: new Date().toISOString(),
          },
        ]);
        return;
      }

      if (payload.type === 'error') {
        setErrorMessage(payload.detail);
      }
    };

    ws.onerror = () => {
      setErrorMessage('Real-time connection failed.');
    };

    return () => {
      ws.close();
      socketRef.current = null;
    };
  }, [activeSession, selectedSessionId, token]);

  const selectedSession =
    sessions.find((session) => session.id === selectedSessionId) ?? null;

  async function handleCreateSession() {
    if (!token) {
      return;
    }
    const authToken: string = token;

    try {
      const created = await createCollabSession(
        {
          title: newSessionTitle.trim() || 'Mentoring Session',
          initial_code: "print('start collaborating')\n",
        },
        authToken,
      );
      setSessions((current) => [created, ...current]);
      setSelectedSessionId(created.id);
      setActiveSession(created);
      setCode(created.current_code);
      setMessages([]);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : 'Failed to create session.',
      );
    }
  }

  async function handleJoinSession() {
    if (!token || !selectedSessionId) {
      return;
    }
    const authToken: string = token;

    try {
      const joined = await joinCollabSession(selectedSessionId, authToken);
      setActiveSession(joined);
      setCode(joined.current_code);
      setMessages([]);
      setErrorMessage('');
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : 'Failed to join session.',
      );
    }
  }

  function handleCodeChange(nextCode: string) {
    setCode(nextCode);
    socketRef.current?.send(
      JSON.stringify({
        type: 'code_update',
        code: nextCode,
      }),
    );
  }

  async function handleSendMessage() {
    const content = chatInput.trim();
    if (!token || !selectedSessionId || !content) {
      return;
    }
    const authToken: string = token;

    try {
      const socket = socketRef.current;
      if (socket && socket.readyState === WebSocket.OPEN) {
        // The websocket handler persists the message and echoes it back via
        // broadcast; calling the REST endpoint too would store it twice.
        socket.send(JSON.stringify({ type: 'chat', content }));
      } else {
        const created = await postCollabMessage(selectedSessionId, content, authToken);
        setMessages((current) => [...current, created]);
      }
      setChatInput('');
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : 'Failed to send message.',
      );
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-zinc-200 bg-white p-8 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <p className="text-sm font-semibold uppercase tracking-[0.25em] text-zinc-500 dark:text-zinc-400">
              Live Collaboration
            </p>
            <h1 className="text-3xl font-black text-zinc-950 dark:text-zinc-50">
              멘토링 세션과 실시간 코드 공유
            </h1>
            <p className="max-w-3xl text-sm leading-6 text-zinc-600 dark:text-zinc-300">
              참여자는 같은 코드를 실시간으로 보고 채팅으로 질문을 남길 수 있습니다.
            </p>
          </div>

          {isStaff ? (
            <div className="flex gap-3">
              <input
                value={newSessionTitle}
                onChange={(event) => setNewSessionTitle(event.target.value)}
                className="rounded-2xl border border-zinc-300 bg-white px-4 py-3 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
                placeholder="New session title"
              />
              <button
                type="button"
                onClick={() => void handleCreateSession()}
                className="rounded-2xl bg-zinc-950 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-zinc-800 dark:bg-white dark:text-zinc-950 dark:hover:bg-zinc-200"
              >
                세션 생성
              </button>
            </div>
          ) : null}
        </div>
      </section>

      {errorMessage ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-300">
          {errorMessage}
        </div>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
        <div className="rounded-3xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
          <div className="border-b border-zinc-200 px-5 py-4 dark:border-zinc-800">
            <h2 className="text-lg font-semibold text-zinc-950 dark:text-zinc-50">
              세션 목록
            </h2>
          </div>
          {isLoading ? (
            <div className="px-5 py-8 text-sm text-zinc-500 dark:text-zinc-400">
              Loading sessions...
            </div>
          ) : (
            <div className="divide-y divide-zinc-200 dark:divide-zinc-800">
              {sessions.map((session) => (
                <button
                  key={session.id}
                  type="button"
                  onClick={() => {
                    setSelectedSessionId(session.id);
                    setActiveSession(null);
                    setCode('');
                    setMessages([]);
                  }}
                  className={`block w-full px-5 py-4 text-left transition ${
                    selectedSessionId === session.id
                      ? 'bg-zinc-100 dark:bg-zinc-900'
                      : 'hover:bg-zinc-50 dark:hover:bg-zinc-900'
                  }`}
                >
                  <p className="font-semibold text-zinc-950 dark:text-zinc-50">
                    {session.title}
                  </p>
                  <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
                    {session.status} · {session.participants.length} participants
                  </p>
                </button>
              ))}
            </div>
          )}
          <div className="border-t border-zinc-200 px-5 py-4 dark:border-zinc-800">
            <button
              type="button"
              onClick={() => void handleJoinSession()}
              disabled={!selectedSession}
              className="w-full rounded-2xl bg-sky-700 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-sky-400"
            >
              선택한 세션 참가
            </button>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="rounded-3xl border border-zinc-200 bg-zinc-950 shadow-2xl dark:border-zinc-800">
            <div className="flex items-center justify-between border-b border-zinc-800 px-5 py-3 text-xs font-mono text-zinc-400">
              <span>{selectedSession?.title ?? 'No active session'}</span>
              <span>{canEdit ? 'editable' : 'read-only'}</span>
            </div>
            <textarea
              data-testid="collab-code-editor"
              value={code}
              onChange={(event) => handleCodeChange(event.target.value)}
              disabled={!activeSession || !canEdit}
              className="min-h-[480px] w-full resize-none bg-transparent p-6 font-mono text-sm leading-6 text-emerald-300 outline-none disabled:opacity-70"
              placeholder="Join a live session to start editing."
              spellCheck={false}
            />
          </div>

          <div className="rounded-3xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
            <div className="border-b border-zinc-200 px-5 py-4 dark:border-zinc-800">
              <h2 className="text-lg font-semibold text-zinc-950 dark:text-zinc-50">
                Chat
              </h2>
            </div>
            <div
              data-testid="collab-chat-log"
              className="flex min-h-[360px] flex-col gap-3 overflow-auto px-5 py-4"
            >
              {messages.length === 0 ? (
                <p className="text-sm text-zinc-500 dark:text-zinc-400">
                  실시간 채팅이 여기에 표시됩니다.
                </p>
              ) : (
                messages.map((message) => (
                  <div
                    key={`${message.user_id}-${message.created_at}-${message.id}`}
                    className="rounded-2xl bg-zinc-100 px-4 py-3 text-sm text-zinc-700 dark:bg-zinc-900 dark:text-zinc-200"
                  >
                    <div className="font-semibold">{message.user_id}</div>
                    <div className="mt-1">{message.content}</div>
                  </div>
                ))
              )}
            </div>
            <div className="border-t border-zinc-200 px-5 py-4 dark:border-zinc-800">
              <div className="flex gap-3">
                <input
                  value={chatInput}
                  onChange={(event) => setChatInput(event.target.value)}
                  className="flex-1 rounded-2xl border border-zinc-300 bg-white px-4 py-3 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
                  placeholder="Type a message"
                />
                <button
                  type="button"
                  onClick={() => void handleSendMessage()}
                  className="rounded-2xl bg-zinc-950 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-zinc-800 dark:bg-white dark:text-zinc-950 dark:hover:bg-zinc-200"
                >
                  전송
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default function CollabPage() {
  return (
    <AuthGate>
      <CollabPageContent />
    </AuthGate>
  );
}
