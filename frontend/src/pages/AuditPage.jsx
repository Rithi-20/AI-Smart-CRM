import React, { useState, useEffect } from 'react';
import { fetchAuditLogs } from '../api.js';
import Pagination from '../components/Pagination.jsx';

export default function AuditPage({ onOpenAiDrawer }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [expandedId, setExpandedId] = useState(null);

    useEffect(() => {
        loadLogs();
    }, [page]);

    async function loadLogs() {
        try {
            setLoading(true);
            const res = await fetchAuditLogs(page);
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
    const startRec = data?.start_record || 0;
    const endRec = data?.end_record || 0;

    return (
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs space-y-4">
            {/* Header + AI Copilot */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                    <h2 className="text-base font-extrabold text-slate-900 font-outfit">📜 Audit & Activity Log</h2>
                    <p className="text-xs text-slate-500">Traceability record of all manual and AI-driven CRM database modifications</p>
                </div>
                <button
                    onClick={() => onOpenAiDrawer('Audit', null)}
                    className="bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-indigo-700 font-bold px-3.5 py-1.5 rounded-lg text-xs flex items-center gap-1.5 transition-colors"
                >
                    <span>⚡</span> Ask AI Copilot
                </button>
            </div>

            {/* Audit Log Table */}
            {loading ? (
                <div className="py-8 text-center text-xs font-semibold text-slate-500">Loading audit log stream...</div>
            ) : items.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-500">No audit log entries recorded.</div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                        <thead>
                            <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                                <th className="py-2.5 px-3">Timestamp</th>
                                <th className="py-2.5 px-3">Performed By</th>
                                <th className="py-2.5 px-3">Action Type</th>
                                <th className="py-2.5 px-3">Target Entity</th>
                                <th className="py-2.5 px-3">Updated Value</th>
                                <th className="py-2.5 px-3 text-center">Details</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                            {items.map((log) => {
                                const isExpanded = expandedId === log.id;
                                return (
                                    <React.Fragment key={log.id}>
                                        <tr className="hover:bg-slate-50 transition-colors">
                                            <td className="py-2.5 px-3 font-semibold text-slate-500">{log.timestamp}</td>
                                            <td className="py-2.5 px-3 font-bold text-indigo-700">{log.performed_by}</td>
                                            <td className="py-2.5 px-3">
                                                <span className="px-2 py-0.5 rounded text-[10px] font-extrabold bg-slate-100 text-slate-800 border border-slate-200">
                                                    {log.action_type}
                                                </span>
                                            </td>
                                            <td className="py-2.5 px-3 font-semibold text-slate-900">{log.target_table} #{log.target_id}</td>
                                            <td className="py-2.5 px-3 text-emerald-700 font-mono text-[11px] truncate max-w-[180px]">{log.after_value}</td>
                                            <td className="py-2.5 px-3 text-center">
                                                <button
                                                    onClick={() => setExpandedId(isExpanded ? null : log.id)}
                                                    className="px-2 py-0.5 bg-slate-100 hover:bg-slate-200 rounded font-bold text-[11px] text-slate-700"
                                                >
                                                    {isExpanded ? 'Hide' : 'View'}
                                                </button>
                                            </td>
                                        </tr>
                                        {isExpanded && (
                                            <tr className="bg-indigo-50/40">
                                                <td colSpan={6} className="p-3 text-xs">
                                                    <div className="bg-white border border-indigo-100 rounded-lg p-3 space-y-1 font-mono text-[11px]">
                                                        <div><strong>Log ID:</strong> {log.id}</div>
                                                        <div><strong>Target Table / ID:</strong> {log.target_table} ({log.target_id})</div>
                                                        <div><strong>After Mutation:</strong> {log.after_value}</div>
                                                        <div><strong>Audit Timestamp:</strong> {log.timestamp}</div>
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                    </React.Fragment>
                                );
                            })}
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
