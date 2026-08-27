import React, { useState, useEffect } from 'react';
import { fetchDeals, updateDealStatus, fetchFilterOptions } from '../api.js';
import Pagination from '../components/Pagination.jsx';

export default function DealsPage({ onOpenAiDrawer }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [status, setStatus] = useState('All');
    const [owner, setOwner] = useState('All');
    const [industry, setIndustry] = useState('All');
    const [page, setPage] = useState(1);

    const [options, setOptions] = useState({ salespeople: [], industries: [] });

    // Status Update Quick Action State
    const [selectedDeal, setSelectedDeal] = useState(null);
    const [newStatus, setNewStatus] = useState('Won');
    const [updating, setUpdating] = useState(false);
    const [msg, setMsg] = useState(null);

    useEffect(() => {
        loadFilterOptions();
    }, []);

    useEffect(() => {
        loadDeals();
    }, [search, status, owner, industry, page]);

    async function loadFilterOptions() {
        try {
            const res = await fetchFilterOptions();
            setOptions(res);
        } catch (err) {
            console.error(err);
        }
    }

    async function loadDeals() {
        try {
            setLoading(true);
            const res = await fetchDeals(search, status, owner, industry, page);
            setData(res);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    }

    function handleClearFilters() {
        setSearch('');
        setStatus('All');
        setOwner('All');
        setIndustry('All');
        setPage(1);
    }

    async function handleStatusUpdateSubmit(e) {
        e.preventDefault();
        if (!selectedDeal || updating) return;

        try {
            setUpdating(true);
            const res = await updateDealStatus(selectedDeal.id, newStatus);
            setMsg(res.message);
            setSelectedDeal(null);
            loadDeals();
        } catch (err) {
            setMsg(`Error: ${err.message}`);
        } finally {
            setUpdating(false);
        }
    }

    const items = data?.items || [];
    const totalRecords = data?.total_records || 0;
    const totalPages = data?.total_pages || 1;
    const startRec = data?.start_record || 0;
    const endRec = data?.end_record || 0;

    return (
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs space-y-4">
            {/* Header + AI Copilot */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                    <h2 className="text-base font-extrabold text-slate-900 font-outfit">Deals & Pipeline</h2>
                    <p className="text-xs text-slate-500">Monitor active deal stages, values, and sales ownership</p>
                </div>
                <button
                    onClick={() => onOpenAiDrawer('Deal', selectedDeal?.id)}
                    className="bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-indigo-700 font-bold px-3.5 py-1.5 rounded-lg text-xs flex items-center gap-1.5 transition-colors"
                >
                    <span>⚡</span> Ask AI Copilot
                </button>
            </div>

            {/* Message Notification Banner */}
            {msg && (
                <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs font-semibold flex items-center justify-between">
                    <span>{msg}</span>
                    <button onClick={() => setMsg(null)} className="font-bold text-emerald-600">×</button>
                </div>
            )}

            {/* Visually Obvious Search Bar */}
            <div>
                <input
                    type="text"
                    value={search}
                    onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                    placeholder="🔍 Search deal title, customer, or company..."
                    className="w-full bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg px-4 py-2.5 text-xs text-slate-900 font-medium focus:outline-none focus:border-[#4F46E5] focus:ring-2 focus:ring-indigo-500/20 transition-all"
                />
            </div>

            {/* Dynamic Toolbar Filters */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-200">
                <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Deal Stage</label>
                    <select
                        value={status}
                        onChange={(e) => { setStatus(e.target.value); setPage(1); }}
                        className="w-full bg-white border border-slate-300 rounded-md px-2.5 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none"
                    >
                        <option value="All">All Stages</option>
                        <option value="New">New</option>
                        <option value="Contacted">Contacted</option>
                        <option value="Qualified">Qualified</option>
                        <option value="Proposal">Proposal</option>
                        <option value="Won">Won</option>
                        <option value="Lost">Lost</option>
                    </select>
                </div>

                <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Salesperson</label>
                    <select
                        value={owner}
                        onChange={(e) => { setOwner(e.target.value); setPage(1); }}
                        className="w-full bg-white border border-slate-300 rounded-md px-2.5 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none"
                    >
                        <option value="All">All Salespeople</option>
                        {options.salespeople.map((sp) => (
                            <option key={sp} value={sp}>{sp}</option>
                        ))}
                    </select>
                </div>

                <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Industry</label>
                    <select
                        value={industry}
                        onChange={(e) => { setIndustry(e.target.value); setPage(1); }}
                        className="w-full bg-white border border-slate-300 rounded-md px-2.5 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none"
                    >
                        <option value="All">All Industries</option>
                        {options.industries.map((ind) => (
                            <option key={ind} value={ind}>{ind}</option>
                        ))}
                    </select>
                </div>

                <div className="flex items-end">
                    <button
                        onClick={handleClearFilters}
                        className="w-full bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold py-1.5 px-3 rounded-md text-xs transition-colors"
                    >
                        Clear Filters
                    </button>
                </div>
            </div>

            {/* Data Table */}
            {loading ? (
                <div className="py-8 text-center text-xs font-semibold text-slate-500">Loading deals...</div>
            ) : items.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-500">No matching deals found.</div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                        <thead>
                            <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                                <th className="py-2.5 px-3">Deal Title</th>
                                <th className="py-2.5 px-3">Customer</th>
                                <th className="py-2.5 px-3 text-right">Value</th>
                                <th className="py-2.5 px-3">Status</th>
                                <th className="py-2.5 px-3 text-center">Prob (%)</th>
                                <th className="py-2.5 px-3">Salesperson</th>
                                <th className="py-2.5 px-3">Expected Close</th>
                                <th className="py-2.5 px-3">Risk Status</th>
                                <th className="py-2.5 px-3 text-center">Quick Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                            {items.map((d) => (
                                <tr key={d.id} className="hover:bg-slate-50 transition-colors">
                                    <td className="py-2.5 px-3 font-bold text-slate-900">{d.title}</td>
                                    <td className="py-2.5 px-3">{d.customer_name}</td>
                                    <td className="py-2.5 px-3 text-right font-bold text-slate-900">₹{Number(d.value).toLocaleString()}</td>
                                    <td className="py-2.5 px-3">
                                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${d.status === 'Won' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                                                d.status === 'Lost' ? 'bg-rose-50 text-rose-700 border border-rose-200' :
                                                    'bg-indigo-50 text-indigo-700 border border-indigo-200'
                                            }`}>
                                            {d.status}
                                        </span>
                                    </td>
                                    <td className="py-2.5 px-3 text-center font-semibold text-slate-700">{d.probability}%</td>
                                    <td className="py-2.5 px-3 font-semibold text-slate-800">{d.owner_name}</td>
                                    <td className="py-2.5 px-3 text-slate-500">{d.expected_close}</td>
                                    <td className="py-2.5 px-3">
                                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${d.risk === 'Normal' ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'
                                            }`}>
                                            {d.risk}
                                        </span>
                                    </td>
                                    <td className="py-2.5 px-3 text-center">
                                        <button
                                            onClick={() => { setSelectedDeal(d); setNewStatus(d.status); }}
                                            className="px-2 py-1 bg-slate-100 hover:bg-indigo-600 hover:text-white rounded font-bold text-[11px] text-slate-700 transition-colors"
                                        >
                                            Update Stage
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Pagination */}
            <Pagination
                currentRecordStart={startRec}
                currentRecordEnd={endRec}
                totalRecords={totalRecords}
                currentPage={page}
                totalPages={totalPages}
                onPageChange={(p) => setPage(p)}
            />

            {/* Status Update Quick Action Modal */}
            {selectedDeal && (
                <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-2xs flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl max-w-md w-full p-5 border border-slate-200 shadow-2xl space-y-4">
                        <h3 className="text-base font-extrabold text-slate-900 font-outfit">Update Deal Status Stage</h3>
                        <p className="text-xs text-slate-600">
                            Updating status for <span className="font-bold text-slate-900">{selectedDeal.title}</span> ({selectedDeal.customer_name})
                        </p>

                        <form onSubmit={handleStatusUpdateSubmit} className="space-y-3">
                            <div>
                                <label className="block text-xs font-bold text-slate-700 mb-1">New Stage</label>
                                <select
                                    value={newStatus}
                                    onChange={(e) => setNewStatus(e.target.value)}
                                    className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-xs font-semibold text-slate-800"
                                >
                                    <option value="New">New</option>
                                    <option value="Contacted">Contacted</option>
                                    <option value="Qualified">Qualified</option>
                                    <option value="Proposal">Proposal</option>
                                    <option value="Won">Won</option>
                                    <option value="Lost">Lost</option>
                                </select>
                            </div>

                            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                                <button
                                    type="button"
                                    onClick={() => setSelectedDeal(null)}
                                    className="px-3.5 py-1.5 rounded-lg border border-slate-300 text-xs font-bold text-slate-700 hover:bg-slate-50"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={updating}
                                    className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-xs font-bold text-white shadow-2xs"
                                >
                                    {updating ? 'Updating...' : 'Commit Change'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
