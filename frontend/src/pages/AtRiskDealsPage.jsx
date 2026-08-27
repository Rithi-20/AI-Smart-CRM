import React, { useState, useEffect } from 'react';
import { fetchAtRiskDeals } from '../api.js';
import Pagination from '../components/Pagination.jsx';

export default function AtRiskDealsPage({ onOpenAiDrawer }) {
    const [days, setDays] = useState(14);
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);

    useEffect(() => {
        loadAtRisk();
    }, [days, page]);

    async function loadAtRisk() {
        try {
            setLoading(true);
            const res = await fetchAtRiskDeals(days, page);
            setData(res);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    }

    const items = data?.items || [];
    const totalRecords = data?.total_records || 0;
    const totalPages = data?.total_pages || 1;

    return (
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs space-y-4">
            {/* Header + AI Copilot */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                    <h2 className="text-base font-extrabold text-slate-900 font-outfit">⚠️ At-Risk Deals BI Workspace</h2>
                    <p className="text-xs text-slate-500">Automated staleness detector & recommended follow-up actions</p>
                </div>
                <button
                    onClick={() => onOpenAiDrawer('AtRisk', null)}
                    className="bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-indigo-700 font-bold px-3.5 py-1.5 rounded-lg text-xs flex items-center gap-1.5 transition-colors"
                >
                    <span>⚡</span> Ask AI Copilot
                </button>
            </div>

            {/* Threshold Slider Card */}
            <div className="bg-rose-50/60 border border-rose-200 p-4 rounded-xl flex items-center justify-between">
                <div>
                    <h4 className="text-xs font-bold text-rose-900 uppercase tracking-wider">Inactivity Threshold (Days Stale)</h4>
                    <p className="text-xs text-rose-700 mt-0.5">Flag deals without activity updates for over {days} days</p>
                </div>
                <div className="flex items-center gap-3">
                    <input
                        type="range"
                        min="1"
                        max="60"
                        value={days}
                        onChange={(e) => { setDays(Number(e.target.value)); setPage(1); }}
                        className="w-36 accent-rose-600 cursor-pointer"
                    />
                    <span className="font-extrabold text-sm text-rose-900 bg-white border border-rose-200 px-3 py-1 rounded-lg">
                        {days} Days
                    </span>
                </div>
            </div>

            {/* At-Risk Table */}
            {loading ? (
                <div className="py-8 text-center text-xs font-semibold text-slate-500">Evaluating stale deal records...</div>
            ) : items.length === 0 ? (
                <div className="py-8 text-center text-xs text-emerald-600 font-bold bg-emerald-50 rounded-lg border border-emerald-200">
                    ✓ No deals exceed the current {days}-day inactivity threshold.
                </div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                        <thead>
                            <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                                <th className="py-2.5 px-3">Deal Title</th>
                                <th className="py-2.5 px-3">Customer</th>
                                <th className="py-2.5 px-3 text-right">Value</th>
                                <th className="py-2.5 px-3">Current Status</th>
                                <th className="py-2.5 px-3 text-center">Days Inactive</th>
                                <th className="py-2.5 px-3">Risk Level</th>
                                <th className="py-2.5 px-3">Recommended Next Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                            {items.map((d) => (
                                <tr key={d.id} className="hover:bg-slate-50 transition-colors">
                                    <td className="py-2.5 px-3 font-bold text-slate-900">{d.title}</td>
                                    <td className="py-2.5 px-3">{d.customer_name}</td>
                                    <td className="py-2.5 px-3 text-right font-bold text-slate-900">₹{Number(d.value).toLocaleString()}</td>
                                    <td className="py-2.5 px-3">
                                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                                            {d.status}
                                        </span>
                                    </td>
                                    <td className="py-2.5 px-3 text-center font-extrabold text-rose-600">{d.days_stale} days</td>
                                    <td className="py-2.5 px-3">
                                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800">
                                            {d.risk_level || 'High Risk'}
                                        </span>
                                    </td>
                                    <td className="py-2.5 px-3 text-slate-600 italic">{d.suggested_next_action || 'Reach out to customer immediately'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Pagination */}
            <Pagination
                currentRecordStart={items.length > 0 ? (page - 1) * 20 + 1 : 0}
                currentRecordEnd={items.length > 0 ? Math.min(page * 20, totalRecords) : 0}
                totalRecords={totalRecords}
                currentPage={page}
                totalPages={totalPages}
                onPageChange={(p) => setPage(p)}
            />
        </div>
    );
}
