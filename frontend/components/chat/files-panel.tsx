'use client';

import { Button } from '@/components/ui/button';
import { X, FileText, Globe } from 'lucide-react';
import { useState, useEffect, useMemo } from 'react';
import type { Citation } from '@/components/citations/citation-list';

export interface FileWithMetadata {
  file: File;
  url?: string;
  uploadedAt: Date;
  status?: 'success' | 'error' | 'uploading';
}

type SourceItem = 
  | { type: 'file'; data: FileWithMetadata; index: number }
  | { type: 'citation'; data: Citation; index: number };

interface FilesPanelProps {
  files: FileWithMetadata[];
  citations?: Citation[];
  selectedCitationUrl?: string;
  onClose: () => void;
  hideHeader?: boolean;
}

export function FilesPanel({ files, citations = [], selectedCitationUrl, onClose, hideHeader = false }: FilesPanelProps) {
  const [fileUrls, setFileUrls] = useState<Map<string, string>>(new Map());
  const [selectedSourceIndex, setSelectedSourceIndex] = useState<number>(0);

  // Filter PDF files
  const pdfFiles = useMemo(() => {
    return files.filter(fileData => 
      fileData.file.type === 'application/pdf' || 
      fileData.file.name.toLowerCase().endsWith('.pdf')
    );
  }, [files]);

  // Combine files and citations into sources list
  const sources = useMemo(() => {
    const items: SourceItem[] = [];
    
    // Add PDF files
    pdfFiles.forEach((file, index) => {
      items.push({ type: 'file', data: file, index });
    });
    
    // Add citations
    citations.forEach((citation, index) => {
      items.push({ type: 'citation', data: citation, index });
    });
    
    return items;
  }, [pdfFiles, citations]);
  
  // Auto-select citation if provided
  useEffect(() => {
    if (selectedCitationUrl && sources.length > 0) {
      const citationIndex = sources.findIndex(s => 
        s.type === 'citation' && s.data.url === selectedCitationUrl
      );
      if (citationIndex !== -1) {
        setSelectedSourceIndex(citationIndex);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCitationUrl, sources.length]);

  // Create object URLs for PDF files
  useEffect(() => {
    const urls = new Map<string, string>();
    pdfFiles.forEach((fileData) => {
      if (!fileData.url && fileData.file) {
        const url = URL.createObjectURL(fileData.file);
        urls.set(fileData.file.name, url);
      }
    });
    setFileUrls(urls);

    // Cleanup on unmount
    return () => {
      urls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [pdfFiles]);

  // Auto-select first source when sources become available
  useEffect(() => {
    if (sources.length > 0 && (selectedSourceIndex >= sources.length || selectedSourceIndex < 0)) {
      setSelectedSourceIndex(0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sources.length]);

  const selectedSource = sources[selectedSourceIndex];
  
  // Get URL for selected source
  const selectedSourceUrl = useMemo(() => {
    if (!selectedSource) return null;
    
    if (selectedSource.type === 'file') {
      return fileUrls.get(selectedSource.data.file.name) || null;
    } else {
      // Citation - check if it's a web URL or internal document
      const url = selectedSource.data.url;
      console.log('Citation URL being processed:', url);
      console.log('Full citation data:', selectedSource.data);
      const isWebUrl = url.startsWith('http://') || url.startsWith('https://');
      
      if (isWebUrl) {
        console.log('Using web URL for iframe:', url);
        return url;
      } else {
        // Internal document - try to match with uploaded files
        const matchingFile = pdfFiles.find(f => {
          const fileName = f.file.name.toLowerCase();
          const title = selectedSource.data.title.toLowerCase();
          return title.includes(fileName) || fileName.includes(title);
        });
        
        if (matchingFile) {
          const fileUrl = fileUrls.get(matchingFile.file.name) || null;
          console.log('Using internal file URL:', fileUrl);
          return fileUrl;
        }
      }
      
      console.warn('No valid URL found for citation:', selectedSource.data);
      return null;
    }
  }, [selectedSource, fileUrls, pdfFiles]);


  return (
    <div className="h-full bg-white flex flex-col">
      {/* Header - only show if not hidden */}
      {!hideHeader && (
        <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between bg-white flex-shrink-0">
          <h3 className="font-medium text-sm text-gray-900">Files</h3>
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onClose();
            }}
            className="h-6 w-6 p-0"
            type="button"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Content: Sidebar + PDF Viewer */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sources List Sidebar */}
        <div className="w-64 border-r border-gray-300 bg-gray-50 flex flex-col overflow-hidden">
          <div className="px-3 py-2 border-b border-gray-200 bg-white">
            <p className="text-xs font-medium text-gray-600">Sources</p>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {sources.length === 0 ? (
              <p className="text-xs text-gray-500 text-center py-8">No sources available</p>
            ) : (
              <div className="space-y-1">
                {sources.map((source, index) => {
                  const isSelected = index === selectedSourceIndex;
                  const isFile = source.type === 'file';
                  const isCitation = source.type === 'citation';
                  
                  return (
                    <button
                      key={`${source.type}-${index}`}
                      onClick={() => setSelectedSourceIndex(index)}
                      className={`w-full text-left p-3 rounded-lg transition-colors ${
                        isSelected
                          ? 'bg-gray-900 text-white'
                          : 'bg-white hover:bg-gray-100 text-gray-900 border border-gray-200'
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        {isFile ? (
                          <FileText className={`h-4 w-4 flex-shrink-0 mt-0.5 ${
                            isSelected ? 'text-white' : 'text-gray-400'
                          }`} />
                        ) : (
                          <Globe className={`h-4 w-4 flex-shrink-0 mt-0.5 ${
                            isSelected ? 'text-white' : 'text-blue-500'
                          }`} />
                        )}
                        <div className="flex-1 min-w-0">
                          <p className={`text-sm font-medium truncate ${
                            isSelected ? 'text-white' : 'text-gray-900'
                          }`}>
                            {isFile ? source.data.file.name : source.data.title}
                          </p>
                          <p className={`text-xs mt-1 ${
                            isSelected ? 'text-gray-300' : 'text-gray-500'
                          }`}>
                            {isFile 
                              ? `${(source.data.file.size / 1024).toFixed(1)} KB`
                              : source.data.domain || 'Web Source'
                            }
                          </p>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Viewer */}
        <div className="flex-1 flex flex-col bg-gray-100">
          {selectedSource && selectedSourceUrl ? (
            <>
              {/* Viewer Header */}
              <div className="px-4 py-2 border-b border-gray-200 bg-white flex items-center justify-between flex-shrink-0">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  {selectedSource.type === 'file' ? (
                    <FileText className="h-4 w-4 text-gray-600 flex-shrink-0" />
                  ) : (
                    <Globe className="h-4 w-4 text-blue-600 flex-shrink-0" />
                  )}
                  <span className="text-sm font-medium text-gray-900 truncate">
                    {selectedSource.type === 'file' 
                      ? selectedSource.data.file.name 
                      : selectedSource.data.title}
                  </span>
                </div>
                {selectedSource.type === 'citation' && (
                  <a
                    href={selectedSource.data.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-2 px-2 py-1 text-xs font-medium text-blue-600 hover:text-blue-700 hover:underline flex-shrink-0"
                    title="Open in new tab"
                  >
                    ↗
                  </a>
                )}
              </div>

              {/* Viewer Content */}
              <div className="flex-1 overflow-hidden relative">
                {selectedSource.type === 'file' ? (
                  // PDF file - show in iframe
                  <iframe
                    src={selectedSourceUrl || undefined}
                    className="w-full h-full border-0"
                    title={selectedSource.data.file.name}
                  />
                ) : (
                  // Citation - show preview first, with option to try iframe
                  <>
                    {/* Default: Show citation preview with metadata */}
                    <div className="w-full h-full flex flex-col items-center justify-center p-6 bg-white overflow-y-auto">
                      <Globe className="h-16 w-16 text-blue-500 mb-4" />
                      <h3 className="text-base font-semibold text-gray-900 mb-2 text-center max-w-md">
                        {selectedSource.data.title}
                      </h3>
                      <p className="text-xs text-gray-500 mb-1">
                        {selectedSource.data.domain || 'Web Source'}
                      </p>
                      {selectedSource.data.snippet && (
                        <p className="text-xs text-gray-600 mb-6 mt-4 max-w-lg text-center leading-relaxed line-clamp-6">
                          {selectedSource.data.snippet}
                        </p>
                      )}
                      {selectedSource.data.relevanceScore !== undefined && (
                        <div className="mb-6">
                          <span className="text-xs font-medium text-gray-600">Relevance: </span>
                          <span className={`text-xs font-semibold ${
                            selectedSource.data.relevanceScore >= 0.8 ? 'text-green-600' :
                            selectedSource.data.relevanceScore >= 0.6 ? 'text-yellow-600' :
                            'text-gray-600'
                          }`}>
                            {Math.round(selectedSource.data.relevanceScore * 100)}%
                          </span>
                        </div>
                      )}
                      <div className="space-y-3 w-full max-w-sm">
                        <a
                          href={selectedSourceUrl || undefined}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block px-6 py-3 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors text-center"
                        >
                          Open in New Tab
                        </a>
                        <p className="text-xs text-gray-400 text-center px-4">
                          Many websites (including government sites) block embedding in iframes for security reasons. Click "Open in New Tab" to view the full page.
                        </p>
                        <p className="text-xs text-gray-400 text-center break-all px-4">
                          {selectedSourceUrl}
                        </p>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <FileText className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                <p className="text-sm text-gray-500">
                  {sources.length === 0 ? 'No sources to display' : 'Select a source to view'}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

