import React, { useState } from 'react';
import Sidebar from './components/Sidebar.jsx';
import Header from './components/Header.jsx';
import AiChatDrawer from './components/AiChatDrawer.jsx';

import OverviewPage from './pages/OverviewPage.jsx';
import AiAssistantPage from './pages/AiAssistantPage.jsx';
import CustomersPage from './pages/CustomersPage.jsx';
import LeadsPage from './pages/LeadsPage.jsx';
import DealsPage from './pages/DealsPage.jsx';
import AtRiskDealsPage from './pages/AtRiskDealsPage.jsx';
import AuditPage from './pages/AuditPage.jsx';

export default function App() {
    const [currentPage, setCurrentPage] = useState('overview');
    const [sessionId, setSessionId] = useState(() => 'sess_' + Math.random().toString(36).substring(2, 9));

    // AI Drawer Floating State
    const [isAiDrawerOpen, setIsAiDrawerOpen] = useState(false);
    const [drawerContext, setDrawerContext] = useState({ type: null, id: null });

    function handleOpenAiDrawer(type = null, id = null) {
        setDrawerContext({ type, id });
        setIsAiDrawerOpen(true);
    }

    function handleNavigate(pageKey) {
        setCurrentPage(pageKey);
    }

    return (
        <div className="flex min-h-screen bg-[#F7F8FC] text-[#0F172A] antialiased">
            {/* Sidebar Navigation */}
            <Sidebar currentPage={currentPage} onSelectPage={handleNavigate} />

            {/* Main Content Area */}
            <main className="flex-1 p-6 max-w-7xl mx-auto overflow-y-auto">
                <Header currentPage={currentPage} />

                {currentPage === 'overview' && <OverviewPage onNavigate={handleNavigate} />}
                {currentPage === 'ai-assistant' && (
                    <AiAssistantPage
                        activeSessionId={sessionId}
                        onSelectSession={(id) => setSessionId(id)}
                    />
                )}
                {currentPage === 'customers' && <CustomersPage onOpenAiDrawer={handleOpenAiDrawer} />}
                {currentPage === 'leads' && <LeadsPage onOpenAiDrawer={handleOpenAiDrawer} />}
                {currentPage === 'deals' && <DealsPage onOpenAiDrawer={handleOpenAiDrawer} />}
                {currentPage === 'at-risk' && <AtRiskDealsPage onOpenAiDrawer={handleOpenAiDrawer} />}
                {currentPage === 'audit' && <AuditPage onOpenAiDrawer={handleOpenAiDrawer} />}
            </main>

            {/* Global Floating AI Copilot Trigger Button (Bottom-Right) */}
            {currentPage !== 'ai-assistant' && (
                <button
                    onClick={() => setIsAiDrawerOpen(true)}
                    className="fixed bottom-6 right-6 bg-[#4F46E5] hover:bg-indigo-700 text-white font-extrabold px-4 py-3 rounded-full shadow-xl shadow-indigo-500/30 flex items-center gap-2 text-xs transition-all transform hover:scale-105 z-40"
                >
                    <span className="text-base">⚡</span> Ask AI Copilot
                </button>
            )}

            {/* Floating AI Side Drawer Overlay */}
            <AiChatDrawer
                isOpen={isAiDrawerOpen}
                onClose={() => setIsAiDrawerOpen(false)}
                contextType={drawerContext.type}
                contextId={drawerContext.id}
                sessionId={sessionId}
            />
        </div>
    );
}
