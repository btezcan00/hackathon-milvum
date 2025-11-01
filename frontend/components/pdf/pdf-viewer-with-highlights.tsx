'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Viewer, Worker, SpecialZoomLevel, Plugin } from '@react-pdf-viewer/core';
import { defaultLayoutPlugin } from '@react-pdf-viewer/default-layout';
import type { PluginOnTextLayerRender } from '@react-pdf-viewer/core';
import { Loader2 } from 'lucide-react';

// Import styles
import '@react-pdf-viewer/core/lib/styles/index.css';
import '@react-pdf-viewer/default-layout/lib/styles/index.css';

interface PDFViewerWithHighlightsProps {
  url: string;
  highlightText?: string;
  pageNumbers?: number[];
  className?: string;
}

interface Sentence {
  text: string;
  normalizedText: string;
}

export function PDFViewerWithHighlights({
  url,
  highlightText,
  pageNumbers = [],
  className = ''
}: PDFViewerWithHighlightsProps) {
  const [sentences, setSentences] = useState<Sentence[]>([]);
  const [message, setMessage] = useState('');
  const [pdfUrl, setPdfUrl] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>('');

  // Debug: Log props on mount and when they change
  useEffect(() => {
    console.log('[PDFViewer] ===== COMPONENT PROPS =====');
    console.log('[PDFViewer] url:', url);
    console.log('[PDFViewer] highlightText:', highlightText);
    console.log('[PDFViewer] highlightText length:', highlightText?.length || 0);
    console.log('[PDFViewer] pageNumbers:', pageNumbers);
    console.log('[PDFViewer] ===========================');
  }, [url, highlightText, pageNumbers]);

  // Fetch PDF to handle CORS issues
  useEffect(() => {
    if (!url) return;

    setIsLoading(true);
    setError('');

    // If it's already a blob URL or local URL, use it directly
    if (url.startsWith('blob:') || url.startsWith('data:')) {
      setPdfUrl(url);
      setIsLoading(false);
      return;
    }

    // For remote URLs (like GCS), use proxy to bypass CORS
    const isRemoteUrl = url.startsWith('http://') || url.startsWith('https://');
    const fetchUrl = isRemoteUrl 
      ? `/api/proxy-pdf?url=${encodeURIComponent(url)}`
      : url;

    fetch(fetchUrl)
      .then(response => {
        if (!response.ok) {
          throw new Error(`Failed to fetch PDF: ${response.statusText}`);
        }
        return response.blob();
      })
      .then(blob => {
        const blobUrl = URL.createObjectURL(blob);
        setPdfUrl(blobUrl);
        setIsLoading(false);
      })
      .catch(err => {
        console.error('Error fetching PDF:', err);
        setError(`Failed to load PDF: ${err.message}`);
        setIsLoading(false);
      });

    // Cleanup
    return () => {
      if (pdfUrl && pdfUrl.startsWith('blob:')) {
        URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [url]);

  // Process highlight text into sentences
  useEffect(() => {
    if (!highlightText) {
      setSentences([]);
      setMessage('');
      return;
    }

    console.log('[PDFViewer] ==========================================');
    console.log('[PDFViewer] Highlight text received:', highlightText);
    console.log('[PDFViewer] Target page numbers:', pageNumbers);
    console.log('[PDFViewer] ==========================================');

    // Split by newlines and sentences - but also keep longer chunks
    const lines = highlightText.split(/\n+/);
    const allSentences: Sentence[] = [];
    
    lines.forEach(line => {
      const trimmedLine = line.trim();
      if (trimmedLine.length > 5) {
        // Add the whole line as one searchable chunk
        allSentences.push({
          text: trimmedLine,
          normalizedText: trimmedLine.toLowerCase()
            .replace(/\s+/g, ' ')
            .trim()
        });
        
        // Also split by sentence boundaries for more granular matching
        const parts = trimmedLine.split(/[.!?]\s+/);
        parts.forEach(part => {
          const cleaned = part.trim();
          if (cleaned.length > 10) {
            allSentences.push({
              text: cleaned,
              normalizedText: cleaned.toLowerCase()
                .replace(/\s+/g, ' ')
                .trim()
            });
          }
        });
      }
    });

    // Limit to first 3-6 sentences for cleaner highlighting
    const limitedSentences = allSentences.slice(3, 7);
    
    setSentences(limitedSentences);
    console.log('[PDFViewer] Processed sentences (limited to 6):', limitedSentences);

  }, [highlightText, pageNumbers]);

  // Custom plugin to highlight text
  const highlightTextPlugin = useCallback((): Plugin => {
    const onTextLayerRender = (e: PluginOnTextLayerRender) => {
      console.log('[PDFViewer] Text layer rendered for page:', e.pageIndex + 1);
      
      // Skip if no sentences to highlight
      if (sentences.length === 0) {
        console.log('[PDFViewer] No sentences to highlight, skipping');
        return;
      }
      
      // Note: We now search ALL pages, not just specific ones, for better matching
      // This is because page numbers from metadata might not always be accurate

      // Wait a bit for the text layer to be fully rendered
      setTimeout(() => {
        const textLayerDiv = e.ele as HTMLElement;
        if (!textLayerDiv) {
          console.log('[PDFViewer] No text layer div found');
          return;
        }

        // Get all text spans in the text layer - try multiple selectors
        let textSpans = textLayerDiv.querySelectorAll('span[role="presentation"]');
        if (textSpans.length === 0) {
          textSpans = textLayerDiv.querySelectorAll('span');
        }
        if (textSpans.length === 0) {
          textSpans = textLayerDiv.querySelectorAll('[class*="textLayer"] span');
        }
        
        console.log('[PDFViewer] Found', textSpans.length, 'text spans on page', e.pageIndex + 1);
        
        if (textSpans.length === 0 || sentences.length === 0) {
          console.log('[PDFViewer] No spans or sentences to process');
          return;
        }

        // Collect all text as-is for better matching
        const spanElements: HTMLElement[] = [];
        textSpans.forEach((span) => {
          spanElements.push(span as HTMLElement);
        });
        
        // Build full page text for context
        const fullPageText = spanElements.map(s => s.textContent || '').join(' ').toLowerCase();
        console.log('[PDFViewer] Page text sample:', fullPageText.substring(0, 300));

        let highlightCount = 0;
        const highlightedSpans = new Set<HTMLElement>();
        
        // For each sentence, use sliding window approach to find best matches
        sentences.forEach((sentence: Sentence, sentenceIdx: number) => {
          console.log(`[PDFViewer] Searching for sentence ${sentenceIdx + 1}:`, sentence.text.substring(0, 100));
          
          // Split sentence into words for partial matching
          const sentenceWords = sentence.text.toLowerCase().split(/\s+/).filter(w => w.length > 3);
          if (sentenceWords.length === 0) return;
          
          console.log(`[PDFViewer] Key words:`, sentenceWords.slice(0, 5));
          
          // Find spans that contain significant parts of the sentence
          let bestMatchStart = -1;
          let bestMatchEnd = -1;
          let bestMatchScore = 0;
          
          // Try to find a continuous run of spans that match the sentence
          for (let i = 0; i < spanElements.length; i++) {
            let currentMatchScore = 0;
            let matchedWords = 0;
            
            // Look ahead to find continuous matching region
            for (let j = i; j < Math.min(i + 30, spanElements.length); j++) {
              const spanText = (spanElements[j].textContent || '').toLowerCase();
              
              // Count how many sentence words appear in this span
              sentenceWords.forEach(word => {
                if (spanText.includes(word)) {
                  matchedWords++;
                  currentMatchScore += 1;
                }
              });
              
              // If we've found a good match region
              if (matchedWords >= Math.min(3, sentenceWords.length * 0.4)) {
                const matchLength = j - i + 1;
                const score = currentMatchScore / matchLength;
                
                if (score > bestMatchScore) {
                  bestMatchScore = score;
                  bestMatchStart = i;
                  bestMatchEnd = j;
                }
              }
            }
          }
          
          // Highlight the best matching region
          if (bestMatchStart !== -1 && bestMatchScore > 0.5) {
            console.log(`[PDFViewer] Found match at spans ${bestMatchStart}-${bestMatchEnd}, score: ${bestMatchScore.toFixed(2)}`);
            
            for (let i = bestMatchStart; i <= bestMatchEnd; i++) {
              if (!highlightedSpans.has(spanElements[i])) {
                spanElements[i].style.backgroundColor = 'rgba(255, 191, 88, 0.9)'; // Dutch government blue #154274
                spanElements[i].style.padding = '2px';
                spanElements[i].style.borderRadius = '2px';
                highlightedSpans.add(spanElements[i]);
                highlightCount++;
              }
            }
          } else {
            console.log(`[PDFViewer] No good match found for sentence ${sentenceIdx + 1}`);
          }
        });
        
        console.log('[PDFViewer] Highlighted', highlightCount, 'spans on page', e.pageIndex + 1);
      }, 200);
    };

    return {
      onTextLayerRender,
    };
  }, [sentences, pageNumbers]);

  const highlightPluginInstance = highlightTextPlugin();
  const defaultLayoutPluginInstance = defaultLayoutPlugin({
    sidebarTabs: () => [],
  });

  if (isLoading) {
    return (
      <div className={`flex flex-col items-center justify-center h-full ${className}`}>
        <Loader2 className="h-8 w-8 animate-spin text-gray-400 mb-2" />
        <p className="text-sm text-gray-500">Loading PDF...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex flex-col items-center justify-center h-full ${className}`}>
        <p className="text-sm text-red-500 mb-2">Error loading PDF</p>
        <p className="text-xs text-gray-500">{error}</p>
      </div>
    );
  }

  if (!pdfUrl) {
    return (
      <div className={`flex flex-col items-center justify-center h-full ${className}`}>
        <p className="text-sm text-gray-500">No PDF URL provided</p>
      </div>
    );
  }

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {message && (
        <div className="bg-blue-50 border-b border-blue-200 px-4 py-2 text-sm text-blue-700">
          {message}
        </div>
      )}
      <div className="flex-1 overflow-hidden">
        <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
          <Viewer
            fileUrl={pdfUrl}
            plugins={[defaultLayoutPluginInstance, highlightPluginInstance]}
            defaultScale={SpecialZoomLevel.PageFit}
            initialPage={0}
          />
        </Worker>
      </div>
    </div>
  );
}
