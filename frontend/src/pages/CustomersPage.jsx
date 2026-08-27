import React, { useState, useEffect } from 'react';
import { fetchCustomers, fetchCustomerDetail, fetchFilterOptions } from '../api.js';
import Pagination from '../components/Pagination.jsx';

export default function CustomersPage({ onOpenAiDrawer }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [industry, setIndustry] = useState('All');
    const [location, setLocation] = useState('All');
    const [typeFilter, setTypeFilter] = useState('All');
    const [page, setPage] = useState(1);

    const [options, setOptions] = useState({ industries: [], locations: [], customer_types: [] });
    const [selectedCustId, setSelectedCustId] = useState(null);
    const [cust360, setCust360] = useState(null);

    useEffect(() => {
        loadFilterOptions();
    }, []);

    useEffect(() => {
        loadCustomers();
    }, [search, industry, location, typeFilter, page]);

    useEffect(() => {
        if (selectedCustId) {
            load360(selectedCustId);
        }
    }, [selectedCustId]);

    async function loadFilterOptions() {
        try {
            const res = await fetchFilterOptions();
            setOptions(res);
        } catch (err) {
            console.error(err);
        }
    }

    async function loadCustomers() {
        try {
            setLoading(true);
            const res = await fetchCustomers(search, industry, location, page);
            setData(res);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    }

    async function load360(id) {
        try {
            const res = await fetchCustomerDetail(id);
            setCust360(res);
        } catch (err) {
            console.error(err);
        }
    }

    function handleClearFilters() {
        setSearch('');
        setIndustry('All');
        setLocation('All');
        setTypeFilter('All');
        setPage(1);
    }

    const items = data?.items || [];
    const totalRecords = data?.total_records || 0;
    const totalPages = data?.total_pages || 1;
    const startRec = data?.start_record || 0;
    const endRec = data?.end_record || 0;

    return (
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs space-y-4">
            {/* Header + AI Copilot Button */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                    <h2 className="text-base font-extrabold text-slate-900 font-outfit">Customer Directory</h2>
                    <p className="text-xs text-slate-500">Real-time view of customer accounts & 360° relationships</p>
                </div>
                <button
                    onClick={() => onOpenAiDrawer('Customer', selectedCustId)}
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
                    placeholder="🔍 Search customers, companies, emails or phone..."
                    className="w-full bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg px-4 py-2.5 text-xs text-slate-900 font-medium focus:outline-none focus:border-[#4F46E5] focus:ring-2 focus:ring-indigo-500/20 transition-all"
                />
            </div>

            {/* Dynamic Toolbar Filters */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-200">
                <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Industry</label>
                    <select
                        value={industry}
                        onChange={(e) => { setIndustry(e.target.value); setPage(1); }}
                        className="w-full bg-white border border-slate-300 rounded-md px-2.5 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none"
                    >
                        <option value="All">All Industries</option>
                        {options.industries.map((i) => (
                            <option key={i} value={i}>{i}</option>
                        ))}
                    </select>
                </div>

                <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Location</label>
                    <select
                        value={location}
                        onChange={(e) => { setLocation(e.target.value); setPage(1); }}
                        className="w-full bg-white border border-slate-300 rounded-md px-2.5 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none"
                    >
                        <option value="All">All Locations</option>
                        {options.locations.map((l) => (
                            <option key={l} value={l}>{l}</option>
                        ))}
                    </select>
                </div>

                <div>
                    <label className="block text-[10px] font-bold text-slate-500 uppercase mb-1">Customer Type</label>
                    <select
                        value={typeFilter}
                        onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
                        className="w-full bg-white border border-slate-300 rounded-md px-2.5 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none"
                    >
                        <option value="All">All Account Types</option>
                        {options.customer_types.map((t) => (
                            <option key={t} value={t}>{t}</option>
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

            {/* Customer Data Table */}
            {loading ? (
                <div className="py-8 text-center text-xs font-semibold text-slate-500">Loading customers...</div>
            ) : items.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-500">No matching customers found.</div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                        <thead>
                            <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                                <th className="py-2.5 px-3">Customer</th>
                                <th className="py-2.5 px-3">Company</th>
                                <th className="py-2.5 px-3">Industry</th>
                                <th className="py-2.5 px-3">Location</th>
                                <th className="py-2.5 px-3">Email</th>
                                <th className="py-2.5 px-3">Phone</th>
                                <th className="py-2.5 px-3">Type</th>
                                <th className="py-2.5 px-3 text-center">Active Deals</th>
                                <th className="py-2.5 px-3 text-right">Total Value</th>
                                <th className="py-2.5 px-3 text-center">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                            {items.map((c) => (
                                <tr key={c.id} className="hover:bg-slate-50 transition-colors">
                                    <td className="py-2.5 px-3 font-bold text-slate-900">{c.name}</td>
                                    <td className="py-2.5 px-3">{c.company}</td>
                                    <td className="py-2.5 px-3">{c.industry}</td>
                                    <td className="py-2.5 px-3">{c.location}</td>
                                    <td className="py-2.5 px-3 text-slate-600">{c.email}</td>
                                    <td className="py-2.5 px-3 text-slate-600">{c.phone}</td>
                                    <td className="py-2.5 px-3">
                                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                                            {c.customer_type}
                                        </span>
                                    </td>
                                    <td className="py-2.5 px-3 text-center font-bold text-slate-900">{c.active_deals}</td>
                                    <td className="py-2.5 px-3 text-right font-bold text-slate-900">₹{Number(c.total_deal_value).toLocaleString()}</td>
                                    <td className="py-2.5 px-3 text-center">
                                        <button
                                            onClick={() => setSelectedCustId(c.id)}
                                            className="px-2.5 py-1 rounded bg-slate-100 hover:bg-indigo-600 hover:text-white font-bold text-[11px] text-slate-700 transition-colors"
                                        >
                                            360° View
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Pagination Controls */}
            <Pagination
                currentRecordStart={startRec}
                currentRecordEnd={endRec}
                totalRecords={totalRecords}
                currentPage={page}
                totalPages={totalPages}
                onPageChange={(p) => setPage(p)}
            />

            {/* Customer 360° Profile Inspector */}
            {cust360 && (
                <div className="mt-6 pt-4 border-t border-slate-200 bg-slate-50/70 p-4 rounded-xl space-y-4">
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-base font-extrabold text-slate-900 font-outfit">
                                🏢 {cust360.customer.name} — {cust360.customer.company}
                            </h3>
                            <p className="text-xs text-slate-600 mt-0.5">
                                {cust360.customer.email} | {cust360.customer.phone} | {cust360.customer.industry} | {cust360.customer.location}
                            </p>
                        </div>
                        <button
                            onClick={() => setCust360(null)}
                            className="text-xs font-bold text-slate-500 hover:text-slate-800"
                        >
                            Close 360°
                        </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Active Deals */}
                        <div className="bg-white p-3 rounded-lg border border-slate-200">
                            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2">Active Deals</h4>
                            {cust360.deals.length === 0 ? (
                                <p className="text-xs text-slate-400">No active deals.</p>
                            ) : (
                                <div className="space-y-1.5">
                                    {cust360.deals.map((d) => (
                                        <div key={d.id} className="flex items-center justify-between text-xs p-2 bg-slate-50 rounded border border-slate-100">
                                            <div>
                                                <div className="font-bold text-slate-900">{d.title}</div>
                                                <div className="text-[10px] text-slate-500">{d.status} • Prob {d.probability}%</div>
                                            </div>
                                            <div className="font-bold text-indigo-600">₹{Number(d.value).toLocaleString()}</div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Notes History */}
                        <div className="bg-white p-3 rounded-lg border border-slate-200">
                            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2">Interaction Notes</h4>
                            {cust360.notes.length === 0 ? (
                                <p className="text-xs text-slate-400">No notes recorded.</p>
                            ) : (
                                <div className="space-y-1.5 max-h-36 overflow-y-auto">
                                    {cust360.notes.map((n) => (
                                        <div key={n.id} className="text-xs p-2 bg-slate-50 rounded border border-slate-100">
                                            <div className="text-[10px] text-slate-400 font-semibold">{n.created_at}</div>
                                            <div className="text-slate-800 font-medium">{n.content}</div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
