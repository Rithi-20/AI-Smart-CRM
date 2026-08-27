import React, { useState, useEffect, useRef } from 'react';
import { sendAiChat, fetchConversations, fetchChatMessages, deleteConversation } from '../api.js';
import FormattedMessage from '../components/FormattedMessage.jsx';

export default function AiAssistantPage({ activeSessionId, onSelectSession }) {
    const [sessions, setSessions] = useState([]);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        loadSessions();
    }, []);

    useEffect(() => {
        if (activeSessionId) {
            loadMessages(activeSessionId);
        }
    }, [activeSessionId]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, loading]);

    async function loadSessions() {
        try {
            const data = await fetchConversations();
            setSessions(data || []);

            // Check if saved session in localStorage exists
            const savedId = localStorage.getItem('active_chat_id');
            if (savedId && data && data.some((s) => s.id === savedId) && savedId !== activeSessionId) {
                onSelectSession(savedId);
            }
        } catch (err) {
            console.error(err);
        }
    }

    async function loadMessages(sessId) {
        try {
            const data = await fetchChatMessages(sessId);
            setMessages(data || []);
        } catch (err) {
            console.error(err);
        }
    }

    async function sendMessage(text, candidateId = null, candidateIndex = null, action = null) {
        if (!text || loading) return;
        const userText = text.trim();
        setInput('');
        setMessages((prev) => [...prev, { role: 'user', content: userText }]);
        setLoading(true);

        try {
            const res = await sendAiChat(userText, activeSessionId, null, null, candidateId, candidateIndex, action);
            if (res && res.reply) {
                setMessages((prev) => [
                    ...prev,
                    {
                        role: 'assistant',
                        content: res.reply,
                        options: res.options,
                        requires_confirmation: res.requires_confirmation,
                        state: res.state
                    }
                ]);
                loadSessions();
            }
        } catch (err) {
            setMessages((prev) => [...prev, { role: 'assistant', content: `Error: ${err.message}` }]);
        } finally {
            setLoading(false);
        }
    }

    async function handleSend(e) {
        e.preventDefault();
        sendMessage(input);
    }

    function handleNewSession() {
        const newId = 'sess_' + Math.random().toString(36).substring(2, 9);
        localStorage.removeItem('active_chat_id');
        onSelectSession(newId);
        setMessages([]);
    }

    function handleSelectSession(sessId) {
        localStorage.setItem('active_chat_id', sessId);
        onSelectSession(sessId);
    }

    async function handleDeleteSession(e, sessId) {
        e.stopPropagation();
        try {
            await deleteConversation(sessId);
            const updated = sessions.filter((s) => s.id !== sessId);
            setSessions(updated);
            if (activeSessionId === sessId) {
                if (updated.length > 0) {
                    handleSelectSession(updated[0].id);
                } else {
                    handleNewSession();
                }
            }
        } catch (err) {
            console.error('Failed to delete session', err);
        }
    }

    function formatTime(isoStr) {
        if (!isoStr) return '';
        try {
            const dt = new Date(isoStr);
            return dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } catch {
            return '';
        }
    }

    return (
        <div className="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden flex h-[76vh]">
            {/* Left Column: Conversation History Sidebar */}
            <div className="w-[300px] border-r border-slate-200 bg-slate-50/70 p-4 flex flex-col">
                <button
                    onClick={handleNewSession}
                    className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2.5 px-3 rounded-lg text-xs flex items-center justify-center gap-2 shadow-2xs transition-all transform hover:scale-[1.01] mb-4"
                >
                    <span>➕</span> New Chat Session
                </button>

                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Conversation History</h4>
                <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
                    {sessions.length === 0 ? (
                        <p className="text-xs text-slate-400 italic py-4 text-center">No past chats recorded.</p>
                    ) : (
                        sessions.map((s) => {
                            const isActive = s.id === activeSessionId;
                            const timeStr = formatTime(s.updated_at || s.created_at);
                            return (
                                <div
                                    key={s.id}
                                    onClick={() => handleSelectSession(s.id)}
                                    className={`group relative w-full text-left p-3 rounded-lg text-xs font-semibold cursor-pointer transition-all border ${isActive
                                        ? 'bg-indigo-50/90 border-indigo-300 text-indigo-900 shadow-2xs'
                                        : 'bg-white/60 border-slate-200/80 text-slate-700 hover:bg-slate-100 hover:border-slate-300'
                                        }`}
                                >
                                    <div className="flex items-center justify-between gap-1">
                                        <div className="flex items-center gap-1.5 min-w-0 flex-1">
                                            <span className="text-indigo-600 shrink-0">💬</span>
                                            <span className="truncate font-bold text-slate-900">{s.title || 'Conversation Session'}</span>
                                        </div>
                                        <button
                                            onClick={(e) => handleDeleteSession(e, s.id)}
                                            title="Delete Session"
                                            className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-600 p-0.5 rounded transition-opacity"
                                        >
                                            🗑️
                                        </button>
                                    </div>
                                    {timeStr && (
                                        <div className="text-[10px] text-slate-400 mt-1 font-normal flex items-center gap-1">
                                            <span>🕒</span> {timeStr}
                                        </div>
                                    )}
                                </div>
                            );
                        })
                    )}
                </div>
            </div>

            {/* Right Column: Interactive Chat Workspace */}
            <div className="flex-1 flex flex-col bg-white">
                <div className="p-3.5 border-b border-slate-200 bg-slate-50/40 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <span className="text-lg">🤖</span>
                        <div>
                            <h3 className="font-extrabold text-sm text-slate-900 font-outfit">AI Sales Advisor Workspace</h3>
                            <p className="text-[11px] text-slate-500">Query CRM records, evaluate risks, or execute safe mutations</p>
                        </div>
                    </div>
                </div>

                {/* Message Thread */}
                <div className="flex-1 p-4 overflow-y-auto space-y-3">
                    {messages.length === 0 ? (
                        <div className="text-center py-16 max-w-md mx-auto">
                            <div className="text-4xl mb-3">🤖</div>
                            <h3 className="text-base font-extrabold text-slate-800 font-outfit">How can I assist your sales team today?</h3>
                            <p className="text-xs text-slate-500 mt-1">
                                Try asking: "Show me deals over ₹20,000", "Summarize Rahul's account", or "Move deal #DEAL001 to Won".
                            </p>
                        </div>
                    ) : (
                        messages.map((m, idx) => (
                            <div
                                key={idx}
                                className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                            >
                                <div
                                    className={`max-w-[80%] rounded-xl p-3.5 text-xs leading-relaxed ${m.role === 'user'
                                        ? 'bg-indigo-600 text-white font-medium rounded-br-none shadow-2xs'
                                        : 'bg-slate-100 border border-slate-200 text-slate-900 rounded-bl-none'
                                        }`}
                                >
                                    {m.role === 'user' ? (
                                        m.content
                                    ) : (
                                        <>
                                            <FormattedMessage content={m.content} />
                                            {(() => {
                                                let opts = m.options || [];
                                                if (opts.length === 0 && m.content && (m.content.includes("Option 1:") || m.content.includes("Which one do you mean"))) {
                                                    const matches = [...m.content.matchAll(/Option (\d+):\s*([^\n\*]+)/g)];
                                                    if (matches.length > 0) {
                                                        opts = matches.map((match) => ({
                                                            id: `opt_${match[1]}`,
                                                            opt_idx: parseInt(match[1], 10),
                                                            title: match[2].trim().replace(/^🔹\s*/, '')
                                                        }));
                                                    }
                                                }
                                                if (opts.length === 0) return null;
                                                return (
                                                    <div className="flex flex-col gap-2 mt-3 pt-2.5 border-t border-slate-200/80">
                                                        {opts.map((opt, oIdx) => {
                                                            const targetIdx = opt.opt_idx || (oIdx + 1);
                                                            return (
                                                                <button
                                                                    key={opt.id || oIdx}
                                                                    onClick={() => sendMessage(`Option ${targetIdx}`, opt.id, targetIdx, 'select_candidate')}
                                                                    data-candidate-id={opt.id}
                                                                    data-candidate-index={targetIdx}
                                                                    className="w-full text-left bg-indigo-50 hover:bg-indigo-100 text-indigo-900 font-bold border border-indigo-200 text-xs px-3.5 py-2.5 rounded-xl transition-all flex items-center justify-between shadow-2xs group"
                                                                >
                                                                    <div className="flex items-center gap-2">
                                                                        <span className="bg-indigo-600 text-white text-[10px] px-2 py-0.5 rounded-md font-black shrink-0">Option {targetIdx}</span>
                                                                        <span className="font-semibold text-slate-800">{opt.title}</span>
                                                                    </div>
                                                                    <span className="text-indigo-600 group-hover:translate-x-0.5 transition-transform shrink-0">➔</span>
                                                                </button>
                                                            );
                                                        })}
                                                    </div>
                                                );
                                            })()}
                                            {m.requires_confirmation && (
                                                <div className="flex gap-2 mt-3 pt-2.5 border-t border-slate-200/80">
                                                    <button
                                                        onClick={() => sendMessage('Confirm', null, null, 'confirm')}
                                                        className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[11px] px-3.5 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 shadow-2xs"
                                                    >
                                                        <span>✅</span> Confirm Action
                                                    </button>
                                                    <button
                                                        onClick={() => sendMessage('Cancel', null, null, 'cancel')}
                                                        className="bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold text-[11px] px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1"
                                                    >
                                                        <span>❌</span> Cancel Action
                                                    </button>
                                                </div>
                                            )}
                                        </>
                                    )}
                                </div>
                            </div>
                        ))
                    )}
                    {loading && (
                        <div className="flex justify-start">
                            <div className="bg-slate-100 border border-slate-200 text-slate-500 rounded-xl p-3 text-xs flex items-center gap-2">
                                <span className="animate-spin text-indigo-600">⚡</span> Processing tool execution & LLM reasoning...
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Form Input */}
                <form onSubmit={handleSend} className="p-3 border-t border-slate-200 flex gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Type your natural language request..."
                        className="flex-1 bg-slate-50 border border-slate-300 rounded-lg px-4 py-2.5 text-xs focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 text-slate-900 font-medium"
                    />
                    <button
                        type="submit"
                        disabled={loading || !input.trim()}
                        className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold px-5 py-2.5 rounded-lg text-xs transition-colors"
                    >
                        Send Request
                    </button>
                </form>
            </div>
        </div>
    );
}
