import React, { useState, useEffect } from 'react';
import { fetchOverview } from '../api.js';
import KpiCard from '../components/KpiCard.jsx';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, PieChart, Pie, Cell } from 'recharts';

const COLORS = ['#4F46E5', '#818CF8', '#F59E0B', '#06B6D4', '#10B981', '#EF4444'];

export default function OverviewPage({ onNavigate }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadData();
    }, []);

    async function loadData() {
        try {
            setLoading(true);
            const res = await fetchOverview();
            setData(res);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    }

    if (loading) {
        return <div className="p-8 text-center text-sm font-semibold text-slate-500">Loading overview metrics from SQLite...</div>;
    }

    const kpis = data?.kpis || {};
    const pipelineStatus = data?.pipeline_by_status || [];
    const leadsStatus = data?.leads_by_status || [];
    const pipelineSp = data?.pipeline_by_salesperson || [];
    const atRiskList = data?.deals_requiring_attention || [];

    return (
        <div className="space-y-5">
            {/* 5 KPI Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-3.5">
                <KpiCard
                    title="Customers"
                    icon="👥"
                    value={kpis.total_customers ?? 0}
                    trend="↑ SQLite"
                    onClick={() => onNavigate('customers')}
                />
                <KpiCard
                    title="Total Leads"
                    icon="🎯"
                    value={kpis.total_leads ?? 0}
                    trend="↑ SQLite"
                    onClick={() => onNavigate('leads')}
                />
                <KpiCard
                    title="Active Deals"
                    icon="🤝"
                    value={kpis.active_deals ?? 0}
                    trend="↑ Active"
                    onClick={() => onNavigate('deals')}
                />
                <KpiCard
                    title="Pipeline Value"
                    icon="💰"
                    value={`₹${(kpis.pipeline_value || 0).toLocaleString()}`}
                    trend="↑ Active"
                    onClick={() => onNavigate('deals')}
                />
                <KpiCard
                    title="At-Risk Deals"
                    icon="⚠️"
                    value={kpis.at_risk_count ?? 0}
                    isWarning={true}
                    trend="Action Required"
                    onClick={() => onNavigate('at-risk')}
                />
            </div>

            {/* 3 Recharts Charts Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Chart 1: Deals by Status */}
                <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs">
                    <h3 className="text-sm font-extrabold text-slate-900 font-outfit mb-3">Deals by Status Stage</h3>
                    <div className="h-48">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={pipelineStatus}>
                                <XAxis dataKey="status" tick={{ fontSize: 10, fill: '#64748B' }} />
                                <YAxis tick={{ fontSize: 10, fill: '#64748B' }} />
                                <Tooltip />
                                <Bar dataKey="count" fill="#4F46E5" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Chart 2: Pipeline by Salesperson */}
                <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs">
                    <h3 className="text-sm font-extrabold text-slate-900 font-outfit mb-3">Pipeline Value by Salesperson</h3>
                    <div className="h-48">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={pipelineSp}>
                                <XAxis dataKey="salesperson" tick={{ fontSize: 10, fill: '#64748B' }} />
                                <YAxis tick={{ fontSize: 10, fill: '#64748B' }} />
                                <Tooltip formatter={(v) => `₹${Number(v).toLocaleString()}`} />
                                <Bar dataKey="total_value" fill="#818CF8" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Chart 3: Leads by Status */}
                <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs">
                    <h3 className="text-sm font-extrabold text-slate-900 font-outfit mb-3">Leads Conversion Pipeline</h3>
                    <div className="h-48">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie data={leadsStatus} dataKey="count" nameKey="status" cx="50%" cy="50%" outerRadius={65} label>
                                    {leadsStatus.map((_, idx) => (
                                        <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Deals Requiring Attention Table */}
            <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs">
                <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-extrabold text-slate-900 font-outfit flex items-center gap-2">
                        <span>⚠️</span> Deals Requiring Immediate Follow-Up
                    </h3>
                    <button
                        onClick={() => onNavigate('at-risk')}
                        className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                    >
                        View All →
                    </button>
                </div>

                {atRiskList.length === 0 ? (
                    <p className="text-xs text-slate-500 py-4 text-center">No at-risk deals currently flagged.</p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs">
                            <thead>
                                <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                                    <th className="py-2.5 px-3">Deal Title</th>
                                    <th className="py-2.5 px-3">Customer</th>
                                    <th className="py-2.5 px-3">Value</th>
                                    <th className="py-2.5 px-3">Status</th>
                                    <th className="py-2.5 px-3">Days Inactive</th>
                                    <th className="py-2.5 px-3">Recommended Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                                {atRiskList.map((d) => (
                                    <tr key={d.id} className="hover:bg-slate-50/80 transition-colors">
                                        <td className="py-2.5 px-3 font-bold text-slate-900">{d.title}</td>
                                        <td className="py-2.5 px-3">{d.customer_name}</td>
                                        <td className="py-2.5 px-3 font-semibold text-slate-900">₹{Number(d.value).toLocaleString()}</td>
                                        <td className="py-2.5 px-3">
                                            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                                                {d.status}
                                            </span>
                                        </td>
                                        <td className="py-2.5 px-3 text-rose-600 font-bold">{d.days_stale} days</td>
                                        <td className="py-2.5 px-3 text-slate-600 italic">{d.suggested_next_action || 'Follow up immediately'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
