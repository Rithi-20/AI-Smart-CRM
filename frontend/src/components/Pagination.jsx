import React from 'react';

export default function Pagination({ currentRecordStart, currentRecordEnd, totalRecords, currentPage, totalPages, onPageChange }) {
    if (totalRecords <= 0) return null;

    return (
        <div className="flex items-center justify-between pt-4 mt-4 border-t border-slate-200 text-xs">
            <div className="text-slate-500 font-medium">
                Showing <span className="font-bold text-slate-800">{currentRecordStart}–{currentRecordEnd}</span> of <span className="font-bold text-slate-800">{totalRecords}</span> records
            </div>

            <div className="flex items-center gap-2">
                <button
                    onClick={() => onPageChange(currentPage - 1)}
                    disabled={currentPage <= 1}
                    className="px-3 py-1.5 rounded-lg border border-slate-300 font-semibold text-slate-700 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                >
                    ← Previous
                </button>

                <span className="px-2 font-semibold text-slate-600">
                    Page <span className="text-slate-900 font-bold">{currentPage}</span> of <span className="text-slate-900 font-bold">{totalPages}</span>
                </span>

                <button
                    onClick={() => onPageChange(currentPage + 1)}
                    disabled={currentPage >= totalPages}
                    className="px-3 py-1.5 rounded-lg border border-slate-300 font-semibold text-slate-700 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                >
                    Next →
                </button>
            </div>
        </div>
    );
}
