'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { X, FileText, Globe } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useEffect, useState } from 'react';
import type { Citation } from './citation-list';

interface CitationViewerProps {
  citation: Citation | null;
  isOpen: boolean;
  onClose: () => void;
  uploadedFiles?: Array<{ file: File; name?: string }>;
}

// Helper function to clean HTML/markdown from text
function cleanText(text: string): string {
  if (!text) return '';
  
  // Remove markdown links [text](url)
  let cleaned = text.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
  
  // Remove HTML tags
  cleaned = cleaned.replace(/<[^>]+>/g, '');
  
  // Remove markdown images ![alt](url)
  cleaned = cleaned.replace(/!\[([^\]]*)\]\([^)]+\)/g, '');
  
  // Decode HTML entities
  const textarea = document.createElement('textarea');
  textarea.innerHTML = cleaned;
  cleaned = textarea.value;
  
  // Clean up extra whitespace
  cleaned = cleaned.replace(/\s+/g, ' ').trim();
  
  return cleaned;
}

export function CitationViewer({ citation, isOpen, onClose, uploadedFiles = [] }: CitationViewerProps) {
  const [iframeError, setIframeError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [showIframe, setShowIframe] = useState(false);
  const [internalFileUrl, setInternalFileUrl] = useState<string | null>(null);

  // Check if this citation is from an uploaded document
  const matchingFile = citation ? uploadedFiles.find(f => {
    const fileName = f.name || f.file.name;
    const fileNameLower = fileName.toLowerCase();
    const titleLower = citation.title.toLowerCase();
    return titleLower.includes(fileNameLower) || fileNameLower.includes(titleLower);
  }) : null;

  const isInternalDocument = citation ? (!!matchingFile || citation.url.startsWith('file://') || citation.url.startsWith('blob:')) : false;
  const isPDF = citation ? (matchingFile?.file.type === 'application/pdf' || 
                citation.url.toLowerCase().endsWith('.pdf') ||
                (matchingFile && (matchingFile.name || matchingFile.file.name).toLowerCase().endsWith('.pdf'))) : false;
  const isWebUrl = citation ? (citation.url.startsWith('http://') || citation.url.startsWith('https://')) : false;
  
  // Reset states when citation changes
  useEffect(() => {
    if (isOpen && citation) {
      console.log('Citation viewer opened with URL:', citation.url);
      setIframeError(false);
      setIsLoading(true);
      setShowIframe(false);
      
      // Check if URL is valid
      try {
        const url = new URL(citation.url);
        console.log('URL is valid:', url.href);
      } catch (e) {
        console.error('Invalid URL:', citation.url, e);
        setIframeError(true);
        setIsLoading(false);
      }
    }
  }, [isOpen, citation]);

  // Get file URL for internal documents
  useEffect(() => {
    if (matchingFile && isOpen) {
      const url = URL.createObjectURL(matchingFile.file);
      setInternalFileUrl(url);
      return () => {
        URL.revokeObjectURL(url);
      };
    } else {
      setInternalFileUrl(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, matchingFile?.file.name]);

  if (!citation) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/20 z-50"
          />

          {/* Viewer Panel - slides in from right */}
          <motion.div
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            onClick={(e) => e.stopPropagation()}
            className="fixed right-0 top-0 h-full w-[600px] bg-white shadow-2xl z-50 flex flex-col"
          >
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-white flex-shrink-0">
              <div className="flex items-center gap-3 flex-1 min-w-0">
                {isWebUrl ? (
                  <Globe className="h-5 w-5 text-blue-600 flex-shrink-0" />
                ) : (
                  <FileText className="h-5 w-5 text-gray-600 flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-gray-900 truncate">
                    {citation.title}
                  </h3>
                  <p className="text-xs text-gray-500 truncate mt-0.5">
                    {citation.domain || 'Source'}
                  </p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="h-8 w-8 p-0 flex-shrink-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden flex flex-col">
              {/* Metadata */}
              <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-gray-600">Relevance Score</span>
                    <span className={`text-xs font-semibold ${
                      citation.relevanceScore >= 0.8 ? 'text-green-600' :
                      citation.relevanceScore >= 0.6 ? 'text-yellow-600' :
                      'text-gray-600'
                    }`}>
                      {Math.round(citation.relevanceScore * 100)}%
                    </span>
                  </div>
                  {citation.snippet && (
                    <div>
                      <span className="text-xs font-medium text-gray-600">Snippet:</span>
                      <p className="text-xs text-gray-700 mt-1 leading-relaxed whitespace-pre-wrap break-words">
                        {cleanText(citation.snippet)}
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Viewer */}
              <div className="flex-1 overflow-hidden bg-gray-100 relative">
                {isWebUrl ? (
                  // Web URL - show preview or iframe
                  <>
                    {!showIframe ? (
                      // Default: Show preview with option to try iframe
                      <div className="w-full h-full flex flex-col items-center justify-center p-6 bg-white">
                        <Globe className="h-16 w-16 text-gray-400 mb-4" />
                        <h3 className="text-base font-semibold text-gray-900 mb-2">
                          {citation.title}
                        </h3>
                        <p className="text-xs text-gray-500 mb-1">
                          {citation.domain}
                        </p>
                        {citation.snippet && (
                          <p className="text-xs text-gray-600 mb-6 mt-4 max-w-md text-center line-clamp-4">
                            {cleanText(citation.snippet)}
                          </p>
                        )}
                        <div className="space-y-2">
                          <a
                            href={citation.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="block px-6 py-3 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors text-center"
                          >
                            Open in New Tab
                          </a>
                          <button
                            onClick={() => {
                              console.log('Trying to show iframe for:', citation.url);
                              setShowIframe(true);
                              setIsLoading(true);
                            }}
                            className="block w-full px-6 py-2 bg-gray-100 text-gray-700 text-xs font-medium rounded-lg hover:bg-gray-200 transition-colors text-center"
                          >
                            Try Preview (may not work)
                          </button>
                          <p className="text-xs text-gray-400 text-center max-w-xs">
                            Many websites block embedding. If preview doesn&apos;t work, use &quot;Open in New Tab&quot;.
                          </p>
                        </div>
                      </div>
                    ) : (
                      // Try to show iframe
                      <>
                        {isLoading && !iframeError && (
                          <div className="absolute inset-0 flex items-center justify-center bg-gray-50 z-5">
                            <div className="text-center">
                              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-2"></div>
                              <p className="text-xs text-gray-600">Loading page...</p>
                            </div>
                          </div>
                        )}
                        <iframe
                          src={citation.url}
                          className={`w-full h-full border-0 ${iframeError ? 'opacity-0 pointer-events-none' : ''}`}
                          title={citation.title}
                          onError={(e) => {
                            console.error('Iframe error:', e);
                            setIframeError(true);
                            setIsLoading(false);
                          }}
                          onLoad={() => {
                            console.log('Iframe onLoad triggered');
                            setIsLoading(false);
                          }}
                          allow="fullscreen"
                        />
                        {iframeError && (
                          <div className="absolute inset-0 flex flex-col items-center justify-center p-6 bg-white z-10">
                            <Globe className="h-16 w-16 text-gray-400 mb-4" />
                            <p className="text-sm font-medium text-gray-900 mb-2">
                              Cannot display this page
                            </p>
                            <p className="text-xs text-gray-600 mb-4 text-center max-w-sm">
                              This website cannot be embedded due to security restrictions (X-Frame-Options or Content-Security-Policy). This is common for government websites.
                            </p>
                            <div className="space-y-2">
                              <a
                                href={citation.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="block px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors text-center"
                              >
                                Open in New Tab
                              </a>
                              <button
                                onClick={() => setShowIframe(false)}
                                className="block w-full px-4 py-2 bg-gray-100 text-gray-700 text-xs rounded-lg hover:bg-gray-200 transition-colors text-center"
                              >
                                Back to Preview
                              </button>
                            </div>
                          </div>
                        )}
                        {/* Show back button and open button */}
                        <div className="absolute top-4 right-4 z-20 flex gap-2">
                          <button
                            onClick={() => setShowIframe(false)}
                            className="px-3 py-1.5 bg-white/90 hover:bg-white border border-gray-300 text-xs font-medium text-gray-700 rounded-lg shadow-sm hover:shadow transition-all"
                          >
                            ← Back
                          </button>
                          <a
                            href={citation.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-3 py-1.5 bg-white/90 hover:bg-white border border-gray-300 text-xs font-medium text-gray-700 rounded-lg shadow-sm hover:shadow transition-all"
                            title="Open in new tab"
                          >
                            ↗ Open
                          </a>
                        </div>
                      </>
                    )}
                  </>
                ) : isPDF && isInternalDocument && internalFileUrl ? (
                  // Internal PDF - show in iframe
                  <iframe
                    src={internalFileUrl}
                    className="w-full h-full border-0"
                    title={citation.title}
                  />
                ) : isInternalDocument ? (
                  // Other internal document
                  <div className="w-full h-full flex items-center justify-center">
                    <div className="text-center">
                      <FileText className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                      <p className="text-sm text-gray-600 mb-2">{citation.title}</p>
                      <p className="text-xs text-gray-500 mb-4">{citation.snippet}</p>
                      {internalFileUrl && (
                        <a
                          href={internalFileUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-blue-600 hover:underline"
                        >
                          Open in new tab
                        </a>
                      )}
                    </div>
                  </div>
                ) : (
                  // Other internal document or fallback
                  <div className="w-full h-full flex items-center justify-center p-6">
                    <div className="text-center">
                      <FileText className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                      <p className="text-sm text-gray-600 mb-2">{citation.title}</p>
                      <p className="text-xs text-gray-500 mb-4">{citation.snippet}</p>
                      <a
                        href={citation.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-blue-600 hover:underline"
                      >
                        Open source
                      </a>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

