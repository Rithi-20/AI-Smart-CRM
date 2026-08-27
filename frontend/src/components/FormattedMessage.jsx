import React from 'react';

export default function FormattedMessage({ content }) {
    if (!content) return null;

    const lines = content.split('\n');

    return (
        <div className="space-y-1 text-xs leading-relaxed text-slate-800">
            {lines.map((line, idx) => {
                const trimmed = line.trim();

                if (!trimmed) {
                    return <div key={idx} className="h-1" />;
                }

                // Headings (# Heading, ## Heading, ### Heading)
                if (trimmed.startsWith('#')) {
                    const level = (trimmed.match(/^#+/) || ['#'])[0].length;
                    const headingText = trimmed.replace(/^#+\s*/, '');
                    const sizeClass = level === 1 ? 'text-base' : level === 2 ? 'text-sm' : 'text-xs';
                    return (
                        <div key={idx} className={`font-extrabold text-indigo-950 mt-2 mb-1 ${sizeClass}`}>
                            {parseInline(headingText)}
                        </div>
                    );
                }

                // Bullet items (* item, - item, • item, 🔹 item)
                if (trimmed.startsWith('* ') || trimmed.startsWith('- ') || trimmed.startsWith('• ') || trimmed.startsWith('🔹 ')) {
                    const itemText = trimmed.replace(/^([\*\-\•]|🔹)\s*/, '');
                    const isOption = trimmed.startsWith('🔹 ');
                    return (
                        <div key={idx} className={`flex items-start gap-1.5 ml-1 my-0.5 ${isOption ? 'bg-indigo-50/80 p-1.5 rounded border border-indigo-100' : ''}`}>
                            <span className="text-indigo-500 font-bold shrink-0">{isOption ? '🔹' : '•'}</span>
                            <span>{parseInline(itemText)}</span>
                        </div>
                    );
                }

                // Numbered list items (1. item, 2. item)
                if (/^\d+\.\s/.test(trimmed)) {
                    const numMatch = trimmed.match(/^(\d+)\.\s/);
                    const num = numMatch ? numMatch[1] : '1';
                    const itemText = trimmed.replace(/^\d+\.\s*/, '');
                    return (
                        <div key={idx} className="flex items-start gap-1.5 ml-1 my-0.5">
                            <span className="font-bold text-indigo-600 shrink-0">{num}.</span>
                            <span>{parseInline(itemText)}</span>
                        </div>
                    );
                }

                // Horizontal Rule (--- or ***)
                if (trimmed === '---' || trimmed === '***') {
                    return <hr key={idx} className="border-slate-200 my-2" />;
                }

                // Blockquotes or Warning Callouts (> text or ⚠️ text or ✅ text or ❌ text)
                if (trimmed.startsWith('>') || trimmed.startsWith('⚠️') || trimmed.startsWith('✅') || trimmed.startsWith('❌')) {
                    const text = trimmed.replace(/^>\s*/, '');
                    return (
                        <div key={idx} className="border-l-2 border-indigo-500 bg-slate-50 px-2.5 py-1 my-1 rounded-r text-slate-800">
                            {parseInline(text)}
                        </div>
                    );
                }

                // Default Paragraph
                return (
                    <div key={idx} className="my-0.5">
                        {parseInline(line)}
                    </div>
                );
            })}
        </div>
    );
}

function parseInline(text) {
    if (!text) return null;

    // Strip leading or residual heading markers like ### if present
    let clean = text.replace(/^#+\s*/, '');

    // Pattern matches ***bold-italic***, **bold**, *italic*, `code`
    const parts = clean.split(/(\*\*\*.*?\*\*\*|\*\*.*?\*\*|\*.*?\*|`.*?`)/g);

    return parts.map((part, index) => {
        if (!part) return null;

        if (part.startsWith('***') && part.endsWith('***') && part.length >= 6) {
            return (
                <strong key={index} className="font-extrabold italic text-slate-900">
                    {part.slice(3, -3)}
                </strong>
            );
        }
        if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
            return (
                <strong key={index} className="font-bold text-slate-900">
                    {part.slice(2, -2)}
                </strong>
            );
        }
        if (part.startsWith('*') && part.endsWith('*') && !part.startsWith('**') && part.length >= 2) {
            return (
                <em key={index} className="italic text-slate-800">
                    {part.slice(1, -1)}
                </em>
            );
        }
        if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
            return (
                <code key={index} className="bg-slate-200/80 px-1 py-0.5 rounded text-[11px] font-mono text-indigo-900 font-semibold">
                    {part.slice(1, -1)}
                </code>
            );
        }
        // Remove any orphan markdown asterisks or hashes from plain text chunks
        return part.replace(/[\#\*]{2,}/g, '');
    });
}
