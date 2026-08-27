import React from 'react';

const PAGE_TITLES = {
    'overview': { title: 'Overview Dashboard', desc: 'Real-time pipeline metrics and key sales performance indicators' },
    'ai-assistant': { title: 'AI Assistant Workspace', desc: 'Natural language CRM querying, tool calling, and action execution' },
    'customers': { title: 'Customer Directory', desc: 'Manage customer accounts, details, and 360° profile views' },
    'leads': { title: 'Lead Management', desc: 'Track sales leads, qualification status, and pipeline assignments' },
    'deals': { title: 'Deals & Pipeline', desc: 'Monitor active deal stages, values, and sales ownership' },
    'at-risk': { title: 'At-Risk Deals BI', desc: 'Stale deal detector and automated follow-up recommendations' },
    'audit': { title: 'Audit & Activity Log', desc: 'Traceability record of manual and AI-driven database actions' }
};

export default function Header({ currentPage }) {
    const info = PAGE_TITLES[currentPage] || { title: 'SmartCRM AI', desc: 'Enterprise CRM Workspace' };

    return (
        <header className="flex items-center justify-between pb-4 mb-4 border-b border-slate-200">
            <div>
                <h1 className="text-xl font-extrabold text-slate-900 tracking-tight font-outfit">
                    {info.title}
                </h1>
                <p className="text-xs text-slate-500 mt-0.5">{info.desc}</p>
            </div>

            <div className="flex items-center gap-4">
                {/* Notification Bell */}
                <div className="relative cursor-pointer p-2 rounded-full hover:bg-slate-200/60 transition-colors">
                    <span className="text-lg">🔔</span>
                    <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-rose-500 rounded-full ring-2 ring-white"></span>
                </div>

                {/* User Identity Indicator */}
                <div className="flex items-center gap-2.5 bg-white border border-slate-200 rounded-full py-1 px-3 shadow-2xs">
                    <div className="w-7 h-7 rounded-full bg-indigo-600 text-white font-bold text-xs flex items-center justify-center">
                        CU
                    </div>
                    <div className="text-left pr-1">
                        <div className="text-xs font-bold text-slate-900 leading-none">CRM User</div>
                        <div className="text-[10px] text-slate-500 font-medium">Sales Manager</div>
                    </div>
                </div>
            </div>
        </header>
    );
}
