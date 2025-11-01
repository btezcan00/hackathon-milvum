'use client';

import { useEffect, useState } from 'react';
import { X, FileText } from 'lucide-react';
import { useClientOnly } from '@/hooks/use-client-only';

interface PDFViewerProps {
  file: File | null;
  fileUrl: string | null;
  onClose: () => void;
}

export function PDFViewer({ file, fileUrl, onClose }: PDFViewerProps) {
  const isClient = useClientOnly();
  const [objectUrl, setObjectUrl] = useState<string | null>(null);

  // Create and manage object URL for file blobs
  useEffect(() => {
    if (!isClient || !file || file.type !== 'application/pdf') {
      setObjectUrl(null);
      return;
    }

    const url = URL.createObjectURL(file);
    setObjectUrl(url);
    
    return () => {
      URL.revokeObjectURL(url);
    };
  }, [file, isClient]);

  // Determine which URL to display
  const pdfUrl = objectUrl || fileUrl;

  if (!pdfUrl && !file) {
    return (
      <div className="w-full h-full bg-gray-50 flex items-center justify-center border-r-2 border-gray-300">
        <div className="text-center">
          <FileText className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600" style={{ fontFamily: 'Verdana, sans-serif' }}>
            Geen document geselecteerd
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col bg-white border-r-2 border-gray-300">
      {/* Header */}
      <div className="bg-[#154274] text-white px-4 py-3 flex items-center justify-between border-b border-gray-300">
        <div className="flex items-center gap-3">
          <FileText className="h-5 w-5" />
          <span className="font-bold text-sm" style={{ fontFamily: 'Verdana, sans-serif' }}>
            {file?.name || 'Document'}
          </span>
        </div>
        <button
          onClick={onClose}
          className="hover:bg-[#0f3054] p-1 rounded transition-colors"
          aria-label="Sluiten"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* PDF Content */}
      <div className="flex-1 overflow-auto bg-gray-100">
        {pdfUrl && (
          <iframe
            src={pdfUrl}
            className="w-full h-full border-0"
            title="PDF Viewer"
          />
        )}
      </div>
    </div>
  );
}

