'use client';

import { useEffect, useRef } from 'react';
import type { Citation } from './citation-list';

interface CitationHighlighterProps {
  citation: Citation;
  url: string;
}

export function CitationHighlighter({ citation, url }: CitationHighlighterProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    // This component can be extended to highlight text in an iframe
    // For now, we'll rely on the browser's native Scroll-to-Text Fragment API
  }, [citation, url]);

  const openWithHighlight = () => {
    if (citation.highlightText) {
      // Use Scroll-to-Text Fragment API
      const highlightText = encodeURIComponent(citation.highlightText.substring(0, 100));
      window.open(`${url}#:~:text=${highlightText}`, '_blank');
    } else {
      window.open(url, '_blank');
    }
  };

  return null; // This component is used via the openWithHighlight function
}

// Helper function to create highlight URL
export function createHighlightUrl(citation: Citation): string {
  if (citation.highlightText) {
    const highlightText = encodeURIComponent(citation.highlightText.substring(0, 100));
    return `${citation.url}#:~:text=${highlightText}`;
  }
  return citation.url;
}

