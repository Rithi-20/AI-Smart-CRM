import React, { useState, useEffect } from 'react';
import { fetchLeads, fetchFilterOptions } from '../api.js';
import Pagination from '../components/Pagination.jsx';

export default function LeadsPage({ onOpenAiDrawer }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [status, setStatus] = useState('All');
    const [assignedTo, setAssignedTo] = useState('All');
    const [page, setPage] = useState(1);

    const [options, setOptions] = useState({ salespeople: [] });

    useEffect(() => {
        loadFilterOptions();
    }, []);

    useEffect(() => {
        loadLeads();
    }, [search, status, assignedTo, page]);

    async function loadFilterOptions() {
        try {
            const res = await fetchFilterOptions();
            setOptions(res);
        } catch (err) {
            console.error(err);
        }
    }

    async function loadLeads() {
        try {
            setLoading(true);
            const res = await fetchLeads(search, status, assignedTo, page);
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
        setAssignedTo('All');
        setPage(1);
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
                    <h2 className="text-base font-extrabold text-slate-900 font-outfit">Lead Workspace</h2>
                    <p className="text-xs text-slate-500">Track, score, and qualify inbound sales leads</p>
                </div>
                <button
                    onClick={() => onOpenAiDrawer('Lead', null)}
                    className="bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-indigo-700 font-bold px-3.5 py-1.5 rounded-lg text-xs flex items-center gap-1.5 transition-colors"
                >
                    <span>⚡</span> Ask AI Copilot
                </button>
            </div>

            {/* Visually Obvious Search Bar */}
            <div>
                <input
                    type="text"
                    value={search}
                    onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                    placeholder="🔍 Search lead customer, company, or email..."
                    className="w-full bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg px-4 py-2.5 text-xs text-slate-900 font-medium focus:outline-none focus:border-[#4F46E5] focus:ring-2 focus:ring-indigo-500/20 transition-all"
                />
            </div>

            {/* Filter Bar */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-200">
                <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Lead Status</label>
                    <select
                        value={status}
                        onChange={(e) => { setStatus(e.target.value); setPage(1); }}
                        className="w-full bg-white border border-slate-300 rounded-md px-2.5 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none"
                    >
                        <option value="All">All Statuses</option>
                        <option value="New">New</option>
                        <option value="Contacted">Contacted</option>
                        <option value="Qualified">Qualified</option>
                        <option value="Proposal">Proposal</option>
                        <option value="Won">Won</option>
                        <option value="Lost">Lost</option>
                    </select>
                </div>

                <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Assigned Salesperson</label>
                    <select
                        value={assignedTo}
                        onChange={(e) => { setAssignedTo(e.target.value); setPage(1); }}
                        className="w-full bg-white border border-slate-300 rounded-md px-2.5 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none"
                    >
                        <option value="All">All Salespeople</option>
                        {options.salespeople.map((sp) => (
                            <option key={sp} value={sp}>{sp}</option>
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
                <div className="py-8 text-center text-xs font-semibold text-slate-500">Loading leads...</div>
            ) : items.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-500">No matching leads found.</div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                        <thead>
                            <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                                <th className="py-2.5 px-3">Customer</th>
                                <th className="py-2.5 px-3">Company</th>
                                <th className="py-2.5 px-3">Source</th>
                                <th className="py-2.5 px-3">Status</th>
                                <th className="py-2.5 px-3 text-center">Score</th>
                                <th className="py-2.5 px-3 text-right">Expected Value</th>
                                <th className="py-2.5 px-3">Assigned To</th>
                                <th className="py-2.5 px-3">Created Date</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                            {items.map((l) => (
                                <tr key={l.id} className="hover:bg-slate-50 transition-colors">
                                    <td className="py-2.5 px-3 font-bold text-slate-900">{l.customer_name}</td>
                                    <td className="py-2.5 px-3">{l.customer_company}</td>
                                    <td className="py-2.5 px-3">{l.source}</td>
                                    <td className="py-2.5 px-3">
                                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                                            {l.status}
                                        </span>
                                    </td>
                                    <td className="py-2.5 px-3 text-center font-bold text-emerald-600">{l.lead_score}</td>
                                    <td className="py-2.5 px-3 text-right font-bold text-slate-900">₹{Number(l.expected_value).toLocaleString()}</td>
                                    <td className="py-2.5 px-3 font-semibold text-slate-800">{l.assigned_to_name || 'Unassigned'}</td>
                                    <td className="py-2.5 px-3 text-slate-500">{l.created_at}</td>
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
        </div>
    );
}
