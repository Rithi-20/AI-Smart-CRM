import React from 'react';

const NAV_ITEMS = [
    { id: 'overview', label: 'Overview', icon: '🏠' },
    { id: 'ai-assistant', label: 'AI Assistant', icon: '🤖' },
    { id: 'customers', label: 'Customers', icon: '👥' },
    { id: 'leads', label: 'Leads', icon: '🎯' },
    { id: 'deals', label: 'Deals', icon: '💰' },
    { id: 'at-risk', label: 'At-Risk Deals', icon: '⚠️' },
    { id: 'audit', label: 'Audit & Activity', icon: '📜' }
];

export default function Sidebar({ currentPage, onSelectPage }) {
    return (
        <aside className="w-[240px] bg-[#111827] border-r border-[#1F2937] flex flex-col h-screen sticky top-0 text-slate-100 select-none z-30">
            {/* Brand Header */}
            <div className="p-4 border-b border-[#1F2937] flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400 font-bold text-xl">
                    ⚡
                </div>
                <div>
                    <h1 className="font-extrabold text-base text-white tracking-tight leading-none font-outfit">
                        SmartCRM AI
                    </h1>
                    <span className="text-[11px] text-indigo-400 font-medium">Data-Driven CRM</span>
                </div>
            </div>

            {/* Navigation Links */}
            <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
                {NAV_ITEMS.map((item) => {
                    const isActive = currentPage === item.id;
                    return (
                        <button
                            key={item.id}
                            onClick={() => onSelectPage(item.id)}
                            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold transition-all duration-150 ${isActive
                                ? 'bg-[#4F46E5] text-white shadow-sm shadow-indigo-500/30'
                                : 'text-slate-400 hover:bg-[#1F2937] hover:text-white'
                                }`}
                        >
                            <span className="text-base">{item.icon}</span>
                            <span>{item.label}</span>
                        </button>
                    );
                })}
            </nav>

        </aside>
    );
}
