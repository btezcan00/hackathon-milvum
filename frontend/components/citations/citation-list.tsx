'use client';

import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export interface Citation {
  id: string;
  url: string;
  title: string;
  snippet: string;
  relevanceScore: number;
  domain: string;
  crawledAt?: string;
  highlightText?: string;
  // PDF/document specific fields
  type?: 'document' | 'web';
  pageNumbers?: number[];
  documentName?: string;
  date?: string;
  uploadedAt?: string;
}

interface CitationListProps {
  citations: Citation[];
  onCitationClick?: (citation: Citation) => void;
}

export function CitationList({ citations, onCitationClick }: CitationListProps) {
  if (!citations || citations.length === 0) {
    return null;
  }

  const getScoreColor = (score: number): string => {
    if (score >= 0.8) return 'bg-green-500';
    if (score >= 0.6) return 'bg-yellow-500';
    return 'bg-gray-400';
  };

  const getScoreTextColor = (score: number): string => {
    if (score >= 0.8) return 'text-green-700';
    if (score >= 0.6) return 'text-yellow-700';
    return 'text-gray-700';
  };

  const formatScore = (score: number): string => {
    return `${Math.round(score * 100)}%`;
  };

  const handleCitationClick = (citation: Citation) => {
    if (onCitationClick) {
      onCitationClick(citation);
    } else {
      // Default: open in new tab with highlight
      const url = citation.url;
      if (citation.highlightText) {
        // Use Scroll-to-Text Fragment API if available
        const highlightText = encodeURIComponent(citation.highlightText.substring(0, 100));
        window.open(`${url}#:~:text=${highlightText}`, '_blank');
      } else {
        window.open(url, '_blank');
      }
    }
  };

  return (
      <div className="mt-4 space-y-3">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-medium text-gray-600">
            Sources ({citations.length}):
          </span>
        </div>
      
      {citations.map((citation, index) => (
        <Card
          key={citation.id}
          className="p-4 border-2 border-gray-300 hover:border-[#154274] transition-colors cursor-pointer bg-white"
          onClick={() => handleCitationClick(citation)}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-bold text-[#154274] bg-[#154274]/10 px-2 py-1 rounded">
                  [{index + 1}]
                </span>
                <h4 className="text-sm font-medium text-gray-900 truncate">
                  {citation.title}
                </h4>
              </div>
              
              <p className="text-xs text-gray-600 mb-2 line-clamp-2">
                {citation.snippet}
              </p>
              
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs text-gray-500">
                  {citation.domain}
                </span>
                {citation.pageNumbers && citation.pageNumbers.length > 0 && (
                  <span className="text-xs text-gray-500">
                  · Pages {citation.pageNumbers.join(', ')}
                </span>
                )}
                {citation.date && (
                  <span className="text-xs text-gray-500">
                    · {citation.date}
                  </span>
                )}
                {citation.type === 'document' && citation.url && citation.url.startsWith('http') && (
                  <a
                    href={citation.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-600 hover:underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    · Google Drive
                  </a>
                )}
                <Badge
                  className={`text-xs px-2 py-0.5 ${getScoreColor(citation.relevanceScore)} ${getScoreTextColor(citation.relevanceScore)} border-0`}
                >
                  {formatScore(citation.relevanceScore)}
                </Badge>
              </div>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

