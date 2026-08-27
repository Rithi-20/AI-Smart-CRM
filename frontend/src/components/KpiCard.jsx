import React from 'react';

export default function KpiCard({ title, icon, value, trend, isWarning, onClick }) {
    return (
        <div className="bg-white border border-slate-200 rounded-xl p-3.5 shadow-2xs flex flex-col justify-between hover:border-slate-300 transition-all">
            <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                    <span>{icon}</span> {title}
                </span>
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${isWarning ? 'bg-rose-50 text-rose-600 border border-rose-200' : 'bg-emerald-50 text-emerald-600 border border-emerald-200'}`}>
                    {trend || 'Live'}
                </span>
            </div>

            <div className="my-2">
                <div className={`text-2xl font-extrabold tracking-tight font-outfit whitespace-nowrap ${isWarning ? 'text-rose-600' : 'text-slate-900'}`}>
                    {value}
                </div>
            </div>

            {onClick && (
                <button
                    onClick={onClick}
                    className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center justify-between pt-1 border-t border-slate-100 mt-1 transition-colors"
                >
                    <span>View Details</span>
                    <span>→</span>
                </button>
            )}
        </div>
    );
}
