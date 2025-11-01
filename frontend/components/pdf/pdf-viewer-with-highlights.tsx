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

  // Process highlight text - just use the entire text as-is
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

    // Just use the entire text - no splitting or processing
    const normalizedText = highlightText.toLowerCase()
      .replace(/\s+/g, '.')
      .trim();
    
    setSentences([{
      text: highlightText,
      normalizedText: normalizedText
    }]);
    
    console.log('[PDFViewer] Will highlight entire text');
    setMessage('Highlighting citation text');
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

        // Build position map with span elements
        interface SpanInfo {
          element: HTMLElement;
          text: string;
          startPos: number;
          endPos: number;
        }
        
        const spanInfos: SpanInfo[] = [];
        let position = 0;
        
        textSpans.forEach((span) => {
          const element = span as HTMLElement;
          const text = element.textContent || '';
          spanInfos.push({
            element,
            text,
            startPos: position,
            endPos: position + text.length
          });
          position += text.length + 1; // +1 for space
        });
        
        // Build full page text
        const fullPageText = spanInfos.map(s => s.text).join(' ').toLowerCase();
        console.log('[PDFViewer] Page text sample:', fullPageText.substring(0, 300));

        let highlightCount = 0;
        const highlightedSpans = new Set<HTMLElement>();
        
        // Extract meaningful keywords (5+ chars, filter common words)
        const commonWords = ['deze', 'heeft', 'zijn', 'wordt', 'werd', 'waren', 'hebben', 'kunnen', 'zullen', 'moeten', 'voor', 'naar', 'over', 'door', 'maar', 'omdat', 'wanneer', 'waar', 'meer', 'veel', 'daar', 'hier', 'andere', 'tussen', 'eerst', 'totaal'];
        
        sentences.forEach((sentence: Sentence, sentenceIdx: number) => {
          console.log(`[PDFViewer] Searching for sentence ${sentenceIdx + 1}:`, sentence.text.substring(0, 100));
          
          const searchText = sentence.text.toLowerCase();
          
          // Extract top keywords (words 6+ chars, not common, take top 5 most unique)
          const keywords = searchText
            .split(/\s+/)
            .filter(word => word.length >= 6)
            .filter(word => !commonWords.includes(word))
            .filter(word => /^[a-z]+$/.test(word)) // Only letters
            .slice(0, 5); // Only use top 5 keywords
          
          console.log(`[PDFViewer] Top keywords to find:`, keywords);
          
          if (keywords.length === 0) {
            console.log(`[PDFViewer] No valid keywords found`);
            return;
          }
          
          // Calculate keyword density in sliding windows
          const WINDOW_SIZE = 20; // Look at 20 spans at a time
          const densityScores: Array<{ startIdx: number, endIdx: number, score: number }> = [];
          
          for (let i = 0; i < spanInfos.length - WINDOW_SIZE; i++) {
            let score = 0;
            const windowText = spanInfos
              .slice(i, i + WINDOW_SIZE)
              .map(s => s.text)
              .join(' ')
              .toLowerCase();
            
            // Count how many keywords appear in this window
            keywords.forEach(keyword => {
              if (windowText.includes(keyword)) {
                score += 1;
              }
            });
            
            if (score > 0) {
              densityScores.push({ startIdx: i, endIdx: i + WINDOW_SIZE, score });
            }
          }
          
          // Sort by score and take only top 2 regions
          densityScores.sort((a, b) => b.score - a.score);
          const topRegions = densityScores.slice(0, 2);
          
          console.log(`[PDFViewer] Found ${topRegions.length} high-density regions`);
          
          // Highlight only the top density regions
          topRegions.forEach(region => {
            console.log(`[PDFViewer] Highlighting region ${region.startIdx}-${region.endIdx} (score: ${region.score})`);
            for (let i = region.startIdx; i < region.endIdx; i++) {
              const spanInfo = spanInfos[i];
              if (!highlightedSpans.has(spanInfo.element)) {
                spanInfo.element.style.backgroundColor = 'rgba(255, 191, 88, 0.9)';
                spanInfo.element.style.padding = '2px';
                spanInfo.element.style.borderRadius = '2px';
                highlightedSpans.add(spanInfo.element);
                highlightCount++;
              }
            }
          });
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
            initialPage={pageNumbers.length > 0 ? parseInt(String(pageNumbers[0]), 10) - 1 : 0}
          />
        </Worker>
      </div>
    </div>
  );
}
