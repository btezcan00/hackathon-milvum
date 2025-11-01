'use client';

import { Button } from '@/components/ui/button';
import { X, FileText } from 'lucide-react';
import { useState, useEffect, useMemo } from 'react';
import type { Citation } from '@/components/citations/citation-list';

export interface FileWithMetadata {
  file: File;
  url?: string;
  driveUrl?: string; // Google Drive link if available
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

  // Combine files and document citations into sources list (exclude web citations)
  const sources = useMemo(() => {
    const items: SourceItem[] = [];
    
    // Add PDF files
    pdfFiles.forEach((file, index) => {
      items.push({ type: 'file', data: file, index });
    });
    
    // Add only document citations (filter out web citations)
    citations.forEach((citation, index) => {
      // Only include document citations, not web citations
      if (citation.type === 'document' || (!citation.type && citation.domain === 'Internal Document')) {
        items.push({ type: 'citation', data: citation, index });
      }
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
      // Use existing URL if available, otherwise create new one
      if (fileData.url) {
        urls.set(fileData.file.name, fileData.url);
      } else if (fileData.file) {
        const url = URL.createObjectURL(fileData.file);
        urls.set(fileData.file.name, url);
        console.log('Created object URL for file:', fileData.file.name, url);
      }
    });
    setFileUrls(urls);
    console.log('File URLs map updated:', Array.from(urls.entries()));

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
    if (!selectedSource) {
      console.log('[FilesPanel] No selected source');
      return null;
    }
    
    if (selectedSource.type === 'file') {
      const fileName = selectedSource.data.file.name;
      const fileMetadata = selectedSource.data as FileWithMetadata;
      // Check if file has a Google Drive URL in metadata
      const driveUrl = fileMetadata.driveUrl || fileMetadata.url;
      if (driveUrl && typeof driveUrl === 'string' && driveUrl.includes('drive.google.com')) {
        console.log('[FilesPanel] File has Google Drive URL:', driveUrl);
        // Convert Google Drive share link to embeddable viewer URL
        const viewerUrl = convertDriveToViewerUrl(driveUrl);
        return viewerUrl || driveUrl;
      }
      // Otherwise, use local object URL
      const url = fileUrls.get(fileName);
      console.log('[FilesPanel] File source selected:', fileName);
      console.log('[FilesPanel] Available file URLs:', Array.from(fileUrls.keys()));
      console.log('[FilesPanel] URL for file:', url);
      return url || null;
    } else {
      // Citation - only handle document citations (web citations filtered out)
      const citation = selectedSource.data;
      const url = citation.url;
      
      console.log('[FilesPanel] Processing citation:', {
        title: citation.title,
        documentName: citation.documentName,
        url: url,
        type: citation.type,
        fullCitation: citation
      });
      console.log('[FilesPanel] Available pdfFiles:', pdfFiles.map(f => ({ name: f.file.name, hasDriveUrl: !!(f.driveUrl || f.url) })));
      console.log('[FilesPanel] Available fileUrls:', Array.from(fileUrls.keys()));
      
      // Check if it's a Google Drive URL
      if (url && typeof url === 'string' && url.includes('drive.google.com')) {
        // Google Drive link - convert to embeddable viewer URL
        console.log('[FilesPanel] Citation has Google Drive URL:', url);
        const viewerUrl = convertDriveToViewerUrl(url);
        if (viewerUrl) {
          console.log('[FilesPanel] Converted to viewer URL:', viewerUrl);
          return viewerUrl;
        }
        // Fallback: return original URL
        return url;
      }
      
      // Check if URL starts with file:// (local file reference from backend)
      if (url && typeof url === 'string' && url.startsWith('file://')) {
        // Backend sends file://{document_name}, try to match with uploaded files
        // Remove 'file://' prefix
        const docNameFromUrl = url.replace(/^file:\/\//, '').trim();
        console.log('[FilesPanel] Citation has file:// URL, trying to match:', docNameFromUrl);
        console.log('[FilesPanel] Available files:', pdfFiles.map(f => f.file.name));
        
        // Try multiple matching strategies
        const matchingFile = pdfFiles.find(f => {
          const fileName = f.file.name.toLowerCase();
          const docName = docNameFromUrl.toLowerCase();
          const title = citation.title?.toLowerCase() || '';
          const documentName = citation.documentName?.toLowerCase() || '';
          
          // Exact match
          if (fileName === docName || fileName === title || fileName === documentName) {
            return true;
          }
          
          // Contains match (remove extensions for comparison)
          const fileNameNoExt = fileName.replace(/\.(pdf|txt|doc|docx|md)$/i, '');
          const docNameNoExt = docName.replace(/\.(pdf|txt|doc|docx|md)$/i, '');
          const titleNoExt = title.replace(/\.(pdf|txt|doc|docx|md)$/i, '');
          
          if (fileNameNoExt === docNameNoExt || fileNameNoExt === titleNoExt || 
              fileName.includes(docNameNoExt) || docNameNoExt.includes(fileNameNoExt) ||
              fileName.includes(titleNoExt) || titleNoExt.includes(fileNameNoExt)) {
            return true;
          }
          
          // Partial match (check if document name contains file name or vice versa)
          if (docName.includes(fileName) || fileName.includes(docName) ||
              title.includes(fileName) || fileName.includes(title)) {
            return true;
          }
          
          return false;
        });
        
        if (matchingFile) {
          console.log('[FilesPanel] Matched citation to file:', matchingFile.file.name);
          // Check if matching file has Google Drive URL
          const driveUrl = matchingFile.driveUrl || matchingFile.url;
          if (driveUrl && typeof driveUrl === 'string' && driveUrl.includes('drive.google.com')) {
            const viewerUrl = convertDriveToViewerUrl(driveUrl);
            console.log('[FilesPanel] Matched file has Google Drive URL:', viewerUrl);
            return viewerUrl || driveUrl;
          }
          // Otherwise use local object URL
          const fileUrl = fileUrls.get(matchingFile.file.name) || null;
          if (fileUrl) {
            console.log('[FilesPanel] Using local file URL:', fileUrl);
            return fileUrl;
          }
          console.warn('[FilesPanel] Matched file but no URL available:', matchingFile.file.name);
        } else {
          console.warn('[FilesPanel] Could not match citation to any uploaded file:', {
            urlDocName: docNameFromUrl,
            citationTitle: citation.title,
            citationDocName: citation.documentName,
            availableFiles: pdfFiles.map(f => f.file.name)
          });
        }
      }
      
      // Try to match citation by document name/title with uploaded files
      const matchingFile = pdfFiles.find(f => {
        const fileName = f.file.name.toLowerCase();
        const title = citation.title?.toLowerCase() || '';
        const docName = citation.documentName?.toLowerCase() || '';
        return title.includes(fileName) || fileName.includes(title) || 
               docName.includes(fileName) || fileName.includes(docName);
      });
      
      if (matchingFile) {
        // Check if matching file has Google Drive URL
        const driveUrl = matchingFile.driveUrl || matchingFile.url;
        if (driveUrl && typeof driveUrl === 'string' && driveUrl.includes('drive.google.com')) {
          const viewerUrl = convertDriveToViewerUrl(driveUrl);
          console.log('[FilesPanel] Matched file by name has Google Drive URL:', viewerUrl);
          return viewerUrl || driveUrl;
        }
        // Otherwise use local object URL
        const fileUrl = fileUrls.get(matchingFile.file.name) || null;
        console.log('[FilesPanel] Citation matched to file by name:', matchingFile.file.name, 'URL:', fileUrl);
        return fileUrl;
      }
      
      // If we have a URL but no match, try to use it directly if it's a valid URL
      if (url && typeof url === 'string' && (url.startsWith('http://') || url.startsWith('https://'))) {
        // Check if it's a Google Drive URL we might have missed
        if (url.includes('drive.google.com')) {
          const viewerUrl = convertDriveToViewerUrl(url);
          if (viewerUrl) {
            return viewerUrl;
          }
        }
        // For other HTTP/HTTPS URLs (like signed URLs), return as-is
        console.log('[FilesPanel] Using citation URL directly:', url);
        return url;
      }
      
      console.log('[FilesPanel] No valid URL found for citation, returning null');
      return null;
    }
  }, [selectedSource, fileUrls, pdfFiles]);

  // Helper function to convert Google Drive share link to embeddable viewer URL
  const convertDriveToViewerUrl = (driveUrl: string): string | null => {
    try {
      // Extract file ID from Google Drive URL
      // Formats: 
      // https://drive.google.com/file/d/FILE_ID/view?usp=share_link
      // https://drive.google.com/open?id=FILE_ID
      // https://drive.google.com/file/d/FILE_ID/edit
      const match = driveUrl.match(/\/file\/d\/([a-zA-Z0-9_-]+)/);
      if (match && match[1]) {
        const fileId = match[1];
        // Return embeddable PDF viewer URL
        return `https://drive.google.com/file/d/${fileId}/preview`;
      }
      return null;
    } catch (e) {
      console.error('Error converting Drive URL:', e);
      return null;
    }
  };


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
        <div className="w-64 flex-shrink-0 flex-grow-0 border-r border-gray-300 bg-gray-50 flex flex-col overflow-hidden">
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
                        <FileText className={`h-4 w-4 flex-shrink-0 mt-0.5 ${
                          isSelected ? 'text-white' : 'text-gray-400'
                        }`} />
                        <div className="flex-1 min-w-0">
                          <p className={`text-sm font-medium truncate ${
                            isSelected ? 'text-white' : 'text-gray-900'
                          }`}>
                            {isFile ? source.data.file.name : source.data.title || source.data.documentName || 'Document'}
                          </p>
                          <p className={`text-xs mt-1 ${
                            isSelected ? 'text-gray-300' : 'text-gray-500'
                          }`}>
                            {isFile 
                              ? `${(source.data.file.size / 1024).toFixed(1)} KB`
                              : source.data.domain || 'Document'
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
          {selectedSource ? (
            <>
              {/* Viewer Header */}
              <div className="px-4 py-2 border-b border-gray-200 bg-white flex items-center justify-between flex-shrink-0">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <FileText className="h-4 w-4 text-gray-600 flex-shrink-0" />
                  <span className="text-sm font-medium text-gray-900 truncate">
                    {selectedSource.type === 'file' 
                      ? selectedSource.data.file.name 
                      : selectedSource.data.title || selectedSource.data.documentName || 'Document'}
                  </span>
                </div>
                {selectedSource.type === 'citation' && selectedSource.data.url && selectedSource.data.url.startsWith('http') && (
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
                {(() => {
                  console.log('[FilesPanel] Rendering viewer:', {
                    sourceType: selectedSource.type,
                    hasUrl: !!selectedSourceUrl,
                    url: selectedSourceUrl,
                    isFile: selectedSource.type === 'file',
                    isCitation: selectedSource.type === 'citation'
                  });
                  
                  if ((selectedSource.type === 'file' || selectedSource.type === 'citation') && selectedSourceUrl) {
                    // PDF file or citation with URL - show in iframe (works for both local files and Google Drive)
                    return (
                      <iframe
                        key={selectedSourceUrl} // Force re-render if URL changes
                        src={selectedSourceUrl}
                        className="w-full h-full border-0"
                        title={selectedSource.type === 'file' ? selectedSource.data.file.name : selectedSource.data.title || 'Document'}
                        allow="fullscreen"
                        onLoad={() => console.log('[FilesPanel] Iframe loaded:', selectedSourceUrl)}
                        onError={(e) => console.error('[FilesPanel] Iframe error:', e, selectedSourceUrl)}
                      />
                    );
                  } else if (selectedSource.type === 'file') {
                    // PDF file but URL not ready yet - show loading
                    return (
                      <div className="w-full h-full flex items-center justify-center bg-white">
                        <p className="text-sm text-gray-500">Loading PDF...</p>
                      </div>
                    );
                  } else {
                    // Citation without URL - show preview
                    return null; // Will be rendered below
                  }
                })() || (
                  // Citation - show document citation preview with metadata (no iframes)
                  selectedSource.type === 'citation' && (() => {
                    const citation = selectedSource.data as Citation;
                    return (
                      <>
                        <div className="w-full h-full flex flex-col items-center justify-center p-6 bg-white overflow-y-auto">
                          <FileText className="h-16 w-16 text-gray-600 mb-4" />
                          <h3 className="text-base font-semibold text-gray-900 mb-2 text-center max-w-md">
                            {citation.title || citation.documentName || 'Document'}
                          </h3>
                          <div className="flex flex-col items-center gap-1 mb-2">
                            <p className="text-xs text-gray-500">
                              {citation.domain || 'Document'}
                            </p>
                            {citation.pageNumbers && citation.pageNumbers.length > 0 && (
                              <p className="text-xs text-gray-500">
                                Pages: {citation.pageNumbers.join(', ')}
                              </p>
                            )}
                            {citation.date && (
                              <p className="text-xs text-gray-500">
                                Date: {citation.date}
                              </p>
                            )}
                          </div>
                          {citation.snippet && (
                            <p className="text-xs text-gray-600 mb-6 mt-4 max-w-lg text-center leading-relaxed line-clamp-6">
                              {citation.snippet}
                            </p>
                          )}
                          {citation.relevanceScore !== undefined && (
                            <div className="mb-6">
                              <span className="text-xs font-medium text-gray-600">Relevance: </span>
                              <span className={`text-xs font-semibold ${
                                citation.relevanceScore >= 0.8 ? 'text-green-600' :
                                citation.relevanceScore >= 0.6 ? 'text-yellow-600' :
                                'text-gray-600'
                              }`}>
                                {Math.round(citation.relevanceScore * 100)}%
                              </span>
                            </div>
                          )}
                          <div className="space-y-3 w-full max-w-sm">
                            {citation.url && citation.url.startsWith('http') && (
                              <a
                                href={citation.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="block px-6 py-3 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors text-center"
                              >
                                {citation.url.includes('drive.google.com') ? 'Open in Google Drive' : 'View Document'}
                              </a>
                            )}
                            {selectedSourceUrl && !citation.url?.startsWith('http') && (
                              <div className="text-center">
                                <p className="text-xs text-gray-400 mb-2">
                                  Document is available in the uploaded files list.
                                </p>
                              </div>
                            )}
                            {!selectedSourceUrl && !citation.url?.startsWith('http') && (
                              <div className="text-center">
                                <p className="text-xs text-gray-500 mb-2">
                                  No preview available. Check console logs for debugging.
                                </p>
                              </div>
                            )}
                          </div>
                        </div>
                      </>
                    );
                  })()
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

