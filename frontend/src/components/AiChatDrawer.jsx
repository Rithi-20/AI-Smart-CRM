import React, { useState, useEffect } from 'react';
import { sendAiChat, fetchChatMessages } from '../api.js';
import FormattedMessage from './FormattedMessage.jsx';

export default function AiChatDrawer({ isOpen, onClose, contextType, contextId, sessionId }) {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (isOpen && sessionId) {
            loadMessages();
        }
    }, [isOpen, sessionId]);

    async function loadMessages() {
        try {
            const data = await fetchChatMessages(sessionId);
            setMessages(data || []);
        } catch (err) {
            console.error(err);
        }
    }

    async function handleSubmit(e) {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userText = input.trim();
        setInput('');
        setMessages((prev) => [...prev, { role: 'user', content: userText }]);
        setLoading(true);

        try {
            const res = await sendAiChat(userText, sessionId, contextType, contextId);
            if (res && res.reply) {
                setMessages((prev) => [...prev, { role: 'assistant', content: res.reply }]);
            }
        } catch (err) {
            setMessages((prev) => [...prev, { role: 'assistant', content: `Error: ${err.message}` }]);
        } finally {
            setLoading(false);
        }
    }

    if (!isOpen) return null;

    return (
        <div className="fixed inset-y-0 right-0 w-[400px] bg-white border-l border-slate-200 shadow-2xl z-50 flex flex-col transition-all duration-200">
            {/* Drawer Header */}
            <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-indigo-50/50">
                <div className="flex items-center gap-2">
                    <span className="text-xl">⚡</span>
                    <div>
                        <h3 className="font-extrabold text-sm text-indigo-900 font-outfit">AI Copilot Assistant</h3>
                        {contextId ? (
                            <span className="text-[11px] text-indigo-600 font-medium">{contextType} #{contextId}</span>
                        ) : (
                            <span className="text-[11px] text-slate-500">Context-Aware Sales Advisor</span>
                        )}
                    </div>
                </div>

                <button
                    onClick={onClose}
                    className="w-7 h-7 rounded-full bg-slate-200/80 hover:bg-slate-300 flex items-center justify-center text-slate-600 font-bold text-sm"
                >
                    ×
                </button>
            </div>

            {/* Messages Scroll Area */}
            <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-slate-50/50">
                {messages.length === 0 ? (
                    <div className="text-center py-10 px-4">
                        <div className="text-3xl mb-2">⚡</div>
                        <h4 className="font-bold text-sm text-slate-800">SmartCRM AI Copilot</h4>
                        <p className="text-xs text-slate-500 mt-1">
                            Ask natural language queries, summarize records, or update deal statuses safely.
                        </p>
                    </div>
                ) : (
                    messages.map((m, idx) => (
                        <div
                            key={idx}
                            className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div
                                className={`max-w-[85%] rounded-xl p-3 text-xs leading-relaxed ${m.role === 'user'
                                    ? 'bg-indigo-600 text-white font-medium rounded-br-none shadow-2xs'
                                    : 'bg-white border border-slate-200 text-slate-800 rounded-bl-none shadow-2xs'
                                    }`}
                            >
                                {m.role === 'user' ? m.content : <FormattedMessage content={m.content} />}
                            </div>
                        </div>
                    ))
                )}
                {loading && (
                    <div className="flex justify-start">
                        <div className="bg-white border border-slate-200 text-slate-500 rounded-xl p-3 text-xs flex items-center gap-2">
                            <span className="animate-spin text-indigo-600">⚡</span> Thinking & querying database...
                        </div>
                    </div>
                )}
            </div>

            {/* Chat Input */}
            <form onSubmit={handleSubmit} className="p-3 border-t border-slate-200 bg-white flex items-center gap-2">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask AI copilot..."
                    className="flex-1 bg-slate-100 border border-slate-300 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 text-slate-900 font-medium"
                />
                <button
                    type="submit"
                    disabled={loading || !input.trim()}
                    className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold px-3 py-2 rounded-lg text-xs transition-colors"
                >
                    Send
                </button>
            </form>
        </div>
    );
}
