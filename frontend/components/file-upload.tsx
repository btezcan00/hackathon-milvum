'use client';

import { useState, useRef, DragEvent } from 'react';
import { Plus, File, X, Upload } from 'lucide-react';

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void;
  maxFiles?: number;
}

export function FileUpload({ onFilesSelected, maxFiles = 10 }: FileUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      handleFiles(files);
    }
  };

  const handleFiles = (files: File[]) => {
    const validFiles = files.filter(file => {
      const ext = file.name.split('.').pop()?.toLowerCase();
      const allowedTypes = ['pdf', 'txt', 'doc', 'docx', 'md'];
      const isValidExt = allowedTypes.includes(ext || '');
      // Also check MIME types for PDF
      const isValidMime = file.type === 'application/pdf' || 
                         file.type.startsWith('text/') ||
                         file.type.includes('document') ||
                         file.type.includes('word');
      return isValidExt || isValidMime;
    });

    const newFiles = [...selectedFiles, ...validFiles].slice(0, maxFiles);
    setSelectedFiles(newFiles);
    onFilesSelected(newFiles);
  };

  const removeFile = (index: number) => {
    const newFiles = selectedFiles.filter((_, i) => i !== index);
    setSelectedFiles(newFiles);
    onFilesSelected(newFiles);
  };

  const openFileDialog = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="space-y-3">
      {/* Upload Button */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={openFileDialog}
          className="w-10 h-10 bg-[#154274] hover:bg-[#0f3054] text-white flex items-center justify-center rounded transition-colors"
          aria-label="Bestand toevoegen"
        >
          <Plus className="h-5 w-5" />
        </button>
        
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.txt,.doc,.docx,.md"
          onChange={handleFileSelect}
          className="hidden"
        />

        <span className="text-sm text-gray-700" style={{ fontFamily: 'Verdana, sans-serif' }}>
          Bestanden toevoegen (PDF, TXT, DOC, DOCX, MD)
        </span>
      </div>

      {/* Drag and Drop Area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded p-6 text-center transition-colors ${
          isDragOver
            ? 'border-[#154274] bg-blue-50'
            : 'border-gray-300 bg-gray-50'
        }`}
      >
        <Upload className={`h-8 w-8 mx-auto mb-2 ${isDragOver ? 'text-[#154274]' : 'text-gray-400'}`} />
        <p className="text-sm text-gray-600" style={{ fontFamily: 'Verdana, sans-serif' }}>
          {isDragOver
            ? 'Laat bestanden hier los'
            : 'Sleep bestanden hierheen of klik op + om te selecteren'}
        </p>
      </div>

      {/* Selected Files List */}
      {selectedFiles.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-bold text-black" style={{ fontFamily: 'Verdana, sans-serif' }}>
            Geselecteerde bestanden ({selectedFiles.length}):
          </p>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {selectedFiles.map((file, index) => (
              <div
                key={`${file.name}-${index}`}
                className="flex items-center gap-2 p-2 bg-gray-50 border border-gray-300 rounded"
              >
                <File className="h-4 w-4 text-[#154274] flex-shrink-0" />
                <span className="text-xs text-black flex-1 truncate" style={{ fontFamily: 'Verdana, sans-serif' }}>
                  {file.name}
                </span>
                <span className="text-xs text-gray-500">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </span>
                <button
                  type="button"
                  onClick={() => removeFile(index)}
                  className="text-gray-500 hover:text-red-600 p-1"
                  aria-label="Bestand verwijderen"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

