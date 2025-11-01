'use client';

import React, { useMemo } from 'react';
import type { Citation } from './citation-list';

interface InlineCitationsProps {
  content: string;
  citations: Citation[];
  onCitationClick: (citation: Citation, index: number) => void;
}

export function InlineCitations({ content, citations, onCitationClick }: InlineCitationsProps) {
  // Parse content and replace [1], [2], etc. with clickable citations
  const parsedContent = useMemo(() => {
    if (!citations || citations.length === 0) {
      return [{ type: 'text', content }];
    }

    // Regex to match [1], [2], [10], etc.
    const citationRegex = /\[(\d+)\]/g;
    const parts: Array<{ type: 'text' | 'citation'; content: string; index?: number }> = [];
    let lastIndex = 0;
    let match;

    while ((match = citationRegex.exec(content)) !== null) {
      const citationIndex = parseInt(match[1], 10) - 1; // Convert to 0-based index
      
      // Add text before the citation
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          content: content.substring(lastIndex, match.index)
        });
      }

      // Add citation if it exists
      if (citationIndex >= 0 && citationIndex < citations.length) {
        parts.push({
          type: 'citation',
          content: match[0],
          index: citationIndex
        });
      } else {
        // Invalid citation number, just add as text
        parts.push({
          type: 'text',
          content: match[0]
        });
      }

      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < content.length) {
      parts.push({
        type: 'text',
        content: content.substring(lastIndex)
      });
    }

    return parts;
  }, [content, citations]);

  return (
    <>
      {parsedContent.map((part, i) => {
        if (part.type === 'text') {
          // Preserve line breaks in text
          return (
            <span key={i}>
              {part.content?.split('\n').map((line, lineIndex, lines) => (
                <React.Fragment key={lineIndex}>
                  {line}
                  {lineIndex < lines.length - 1 && <br />}
                </React.Fragment>
              ))}
            </span>
          );
        } else {
          const citation = citations[part.index!];
          return (
            <button
              key={i}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onCitationClick(citation, part.index!);
              }}
              className="inline-flex items-center justify-center px-1.5 py-0.5 mx-0.5 text-xs font-semibold text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-sm transition-colors cursor-pointer underline decoration-1 underline-offset-2"
              title={`${citation.type === 'document' ? 'Document' : 'Web'} source: ${citation.title}${citation.pageNumbers ? ` (Pages ${citation.pageNumbers.join(', ')})` : ''}`}
            >
              [{part.index! + 1}]
            </button>
          );
        }
      })}
    </>
  );
}

