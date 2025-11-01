'use client';

import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';
import { useState, useEffect } from 'react';

export interface FileWithMetadata {
  file: File;
  url?: string;
  uploadedAt: Date;
}

interface FilesPanelProps {
  files: FileWithMetadata[];
  onClose: () => void;
}

export function FilesPanel({ files, onClose }: FilesPanelProps) {
  const [fileUrls, setFileUrls] = useState<Map<string, string>>(new Map());

  useEffect(() => {
    // Create object URLs for files
    const urls = new Map<string, string>();
    files.forEach((fileData) => {
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
  }, [files]);

  return (
    <div className="h-full bg-gray-50 border-r border-gray-200 flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between bg-white">
        <h3 className="font-medium text-sm text-gray-900">Files</h3>
        <Button
          variant="ghost"
          size="sm"
          onClick={onClose}
          className="h-6 w-6 p-0"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Files List */}
      <div className="flex-1 overflow-y-auto p-4">
        {files.length === 0 ? (
          <p className="text-xs text-gray-500 text-center py-8">No files uploaded</p>
        ) : (
          <div className="space-y-2">
            {files.map((fileData, index) => (
              <div
                key={index}
                className="bg-white border border-gray-200 rounded-lg p-3 hover:border-gray-300 transition-colors"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {fileData.file.name}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {fileData.file.type || 'Unknown type'}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      {(fileData.file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

