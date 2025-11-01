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
    console.log('[PDFViewer] PDF URL:', url);
    console.log('[PDFViewer] PDF filename:', url?.split('/').pop()?.split('?')[0]);
    console.log('[PDFViewer] highlightText:', highlightText);
    console.log('[PDFViewer] highlightText length:', highlightText?.length || 0);
    console.log('[PDFViewer] highlightText preview:', highlightText?.substring(0, 100));
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

    let blobUrl: string | null = null;

    fetch(fetchUrl)
      .then(response => {
        if (!response.ok) {
          throw new Error(`Failed to fetch PDF: ${response.statusText}`);
        }
        return response.blob();
      })
      .then(blob => {
        blobUrl = URL.createObjectURL(blob);
        setPdfUrl(blobUrl);
        setIsLoading(false);
      })
      .catch(err => {
        console.error('Error fetching PDF:', err);
        setError(`Failed to load PDF: ${err.message}`);
        setIsLoading(false);
      });

    // Cleanup - revoke the blob URL created in this effect
    return () => {
      if (blobUrl && blobUrl.startsWith('blob:')) {
        URL.revokeObjectURL(blobUrl);
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

    const normalize = (text: string) => text.toLowerCase().replace(/\s+/g, ' ').trim();

    // Split by dots to get sentences
    const sentenceTexts = highlightText
      .split('.')
      .map(s => normalize(s))
      .filter(s => s.length > 20); // Only keep sentences with 20+ chars
    
    const processedSentences = sentenceTexts.map(text => ({
      text: text,
      normalizedText: text.toLowerCase().replace(/\s+/g, ' ').trim()
    }));
    
    setSentences(processedSentences);
    console.log('[PDFViewer] Split into', processedSentences.length, 'sentences');
    console.log('[PDFViewer] Sentences:', processedSentences.map(s => s.text.substring(0, 50)));
    setMessage(`Searching for ${processedSentences.length} sentences`);
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
          normalizedText: string;
          startPos: number;
          endPos: number;
        }
        
        const spanInfos: SpanInfo[] = [];
        let position = 0;
        
        textSpans.forEach((span) => {
          const element = span as HTMLElement;
          const text = element.textContent || '';
          // Normalize: lowercase and collapse whitespace
          const normalized = text.toLowerCase().replace(/\s+/g, ' ').trim();
          
          spanInfos.push({
            element,
            normalizedText: normalized,
            startPos: position,
            endPos: position + normalized.length
          });
          position += normalized.length + 1; // +1 for space between spans
        });
        
        // Build full page text from normalized spans and collapse double spaces
        const fullPageText = spanInfos.map(s => s.normalizedText).join(' ')
          .replace(/\s+/g, ' ')  // Normalize again after joining
          .trim();
        console.log('[PDFViewer] Page text (normalized):', fullPageText.substring(0, 300));
        console.log('[PDFViewer] Full page text length:', fullPageText.length, 'chars');

        let highlightCount = 0;
        const highlightedSpans = new Set<HTMLElement>();
        
        // Search for exact sentences in the PDF
        sentences.forEach((sentence: Sentence, sentenceIdx: number) => {
          console.log(`\n[PDFViewer] === Sentence ${sentenceIdx + 1} ===`);
          console.log(`[PDFViewer] Looking for: "${sentence.text.substring(0, 60)}..."`);
          
          const searchText = sentence.normalizedText;
          
          // Try to find exact match in page text
          const matchIndex = fullPageText.indexOf(searchText);
          
          if (matchIndex !== -1) {
            console.log(`[PDFViewer] ✅ FOUND at character position ${matchIndex}`);
            console.log(`[PDFViewer] Context: "...${fullPageText.substring(Math.max(0, matchIndex - 30), matchIndex + 80)}..."`);
            
            // Find all spans that overlap with this match
            const matchEnd = matchIndex + searchText.length;
            
            spanInfos.forEach((spanInfo) => {
              if (spanInfo.endPos > matchIndex && spanInfo.startPos < matchEnd) {
                if (!highlightedSpans.has(spanInfo.element)) {
                  spanInfo.element.style.backgroundColor = 'rgba(255, 191, 88, 0.9)';
                  spanInfo.element.style.padding = '2px';
                  spanInfo.element.style.borderRadius = '2px';
                  highlightedSpans.add(spanInfo.element);
                  highlightCount++;
                }
              }
            });
          } else {
            console.log(`[PDFViewer] ❌ NOT FOUND on this page`);
            // Show if we can find any of the key words
            const words = searchText.split(' ').filter(w => w.length > 5).slice(0, 3);
            console.log(`[PDFViewer] Checking for key words:`, words);
            words.forEach(word => {
              const wordIndex = fullPageText.indexOf(word);
              if (wordIndex !== -1) {
                console.log(`[PDFViewer]   - Found "${word}" at position ${wordIndex}`);
              } else {
                console.log(`[PDFViewer]   - Word "${word}" not found`);
              }
            });
          }
        });
        
        console.log('[PDFViewer] Highlighted', highlightCount, 'spans on page', e.pageIndex + 1);
      }, 200);
    };

    return {
      onTextLayerRender,
    };
  }, [sentences]);

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
