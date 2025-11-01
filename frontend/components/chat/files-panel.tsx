'use client';

import { Button } from '@/components/ui/button';
import { X, FileText } from 'lucide-react';
import { useState, useEffect, useMemo } from 'react';

export interface FileWithMetadata {
  file: File;
  url?: string;
  uploadedAt: Date;
  status?: 'success' | 'error' | 'uploading';
}

interface FilesPanelProps {
  files: FileWithMetadata[];
  onClose: () => void;
  hideHeader?: boolean;
}

export function FilesPanel({ files, onClose, hideHeader = false }: FilesPanelProps) {
  const [fileUrls, setFileUrls] = useState<Map<string, string>>(new Map());
  const [selectedPdfIndex, setSelectedPdfIndex] = useState<number>(0);

  // Filter PDF files - memoize to prevent unnecessary re-renders
  const pdfFiles = useMemo(() => {
    return files.filter(fileData => 
      fileData.file.type === 'application/pdf' || 
      fileData.file.name.toLowerCase().endsWith('.pdf')
    );
  }, [files]);

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
  }, [pdfFiles]); // Only depend on pdfFiles, not selectedPdfIndex

  // Auto-select first PDF when PDFs become available (separate effect)
  useEffect(() => {
    if (pdfFiles.length > 0 && (selectedPdfIndex >= pdfFiles.length || selectedPdfIndex < 0)) {
      setSelectedPdfIndex(0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pdfFiles.length]); // Only depend on length to avoid infinite loops

  const selectedPdf = pdfFiles[selectedPdfIndex];
  const selectedPdfUrl = selectedPdf ? fileUrls.get(selectedPdf.file.name) : null;

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
        {/* PDF List Sidebar */}
        <div className="w-64 border-r border-gray-300 bg-gray-50 flex flex-col overflow-hidden">
          <div className="px-3 py-2 border-b border-gray-200 bg-white">
            <p className="text-xs font-medium text-gray-600">PDF Documents</p>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {pdfFiles.length === 0 ? (
              <p className="text-xs text-gray-500 text-center py-8">No PDF files uploaded</p>
            ) : (
              <div className="space-y-1">
                {pdfFiles.map((fileData, index) => {
                  const isSelected = index === selectedPdfIndex;
                  return (
                    <button
                      key={index}
                      onClick={() => setSelectedPdfIndex(index)}
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
                            {fileData.file.name}
                          </p>
                          <p className={`text-xs mt-1 ${
                            isSelected ? 'text-gray-300' : 'text-gray-500'
                          }`}>
                            {(fileData.file.size / 1024).toFixed(1)} KB
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

        {/* PDF Viewer */}
        <div className="flex-1 flex flex-col bg-gray-100">
          {selectedPdf && selectedPdfUrl ? (
            <>
              {/* PDF Viewer Header */}
              <div className="px-4 py-2 border-b border-gray-200 bg-white flex items-center justify-between flex-shrink-0">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-gray-600" />
                  <span className="text-sm font-medium text-gray-900 truncate">
                    {selectedPdf.file.name}
                  </span>
                </div>
              </div>

              {/* PDF iframe */}
              <div className="flex-1 overflow-hidden">
                <iframe
                  src={selectedPdfUrl}
                  className="w-full h-full border-0"
                  title={selectedPdf.file.name}
                />
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <FileText className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                <p className="text-sm text-gray-500">
                  {pdfFiles.length === 0 ? 'No PDF files to display' : 'Select a PDF to view'}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

