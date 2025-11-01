'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useState, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { ChatContent } from './chat-content';
import { FilesPanel } from './files-panel';
import type { FileWithMetadata } from './files-panel';
import type { Citation } from '@/components/citations/citation-list';

interface ChatModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ChatModal({ isOpen, onClose }: ChatModalProps) {
  const [uploadedFiles, setUploadedFiles] = useState<FileWithMetadata[]>([]);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [showFilesPanel, setShowFilesPanel] = useState(false);
  const [selectedCitationUrl, setSelectedCitationUrl] = useState<string | undefined>(undefined);

  // Use refs to track previous values to avoid infinite loops
  const prevFilesRef = useRef<FileWithMetadata[]>([]);
  const prevCitationsRef = useRef<Citation[]>([]);

  const handleFilesChange = useCallback((files: FileWithMetadata[]) => {
    // Only update if files actually changed
    const filesChanged = files.length !== prevFilesRef.current.length ||
      files.some((file, index) => {
        const prevFile = prevFilesRef.current[index];
        return !prevFile || file.file.name !== prevFile.file.name || file.file.size !== prevFile.file.size;
      });

    if (filesChanged) {
      prevFilesRef.current = files;
      setUploadedFiles(files);
      // Show panel if we have files OR citations
      setShowFilesPanel(prev => {
        const hasFiles = files.length > 0;
        const hasCitations = prevCitationsRef.current.length > 0;
        return hasFiles || hasCitations;
      });
    }
  }, []);

  const handleCitationsChange = useCallback((newCitations: Citation[]) => {
    // Only update if citations actually changed
    const citationsChanged = newCitations.length !== prevCitationsRef.current.length ||
      newCitations.some((citation, index) => {
        const prevCitation = prevCitationsRef.current[index];
        return !prevCitation || citation.url !== prevCitation.url;
      });

    if (citationsChanged) {
      prevCitationsRef.current = newCitations;
      setCitations(newCitations);
      // Show panel if we have files OR citations
      setShowFilesPanel(prev => {
        const hasFiles = prevFilesRef.current.length > 0;
        const hasCitations = newCitations.length > 0;
        return hasFiles || hasCitations;
      });
    }
  }, []);

  const handleCitationClick = (citation: Citation) => {
    // Open files panel if not open
    if (!showFilesPanel) {
      setShowFilesPanel(true);
    }
    // Select the clicked citation
    setSelectedCitationUrl(citation.url);
  };

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
            className="fixed inset-0 bg-black/20 z-40"
          />

          {/* Modal Container */}
          <div className="fixed inset-0 z-50 pointer-events-none">
            <div className="h-full flex items-center justify-end pr-6 pb-6">
              {/* Combined Container: Files Panel + Chat Modal - Same div, connected */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
                onClick={(e) => e.stopPropagation()}
                className="pointer-events-auto h-[90vh] max-h-[800px] bg-white shadow-2xl overflow-hidden flex flex-col"
              >
                {/* Unified Header - spans across both panels */}
                <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-white flex-shrink-0">
                  <div className="flex items-center gap-6">
                    {showFilesPanel && (
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900">Files</span>
                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            setShowFilesPanel(false);
                            setUploadedFiles([]);
                          }}
                          className="text-gray-400 hover:text-gray-600 transition-colors"
                          type="button"
                        >
                          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    )}
                    <h2 className="text-lg font-semibold text-gray-900">Chat</h2>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onClose}
                    className="text-gray-600 hover:text-gray-900"
                  >
                    Close
                  </Button>
                </div>

                {/* Content Area - Files Panel + Chat */}
                <div className="flex-1 flex overflow-hidden">
                  {/* Files Panel - inside same container, extends left */}
                  <AnimatePresence>
                    {showFilesPanel && (
                      <motion.div
                        initial={{ width: 0, opacity: 0 }}
                        animate={{ width: 700, opacity: 1 }}
                        exit={{ width: 0, opacity: 0 }}
                        transition={{ duration: 0.3, ease: 'easeInOut' }}
                        className="flex-shrink-0"
                      >
                        <FilesPanel 
                          files={uploadedFiles} 
                          citations={citations}
                          selectedCitationUrl={selectedCitationUrl}
                          onClose={() => {
                            setShowFilesPanel(false);
                            setUploadedFiles([]);
                            setCitations([]);
                            setSelectedCitationUrl(undefined);
                          }}
                          hideHeader={true}
                        />
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Chat Modal - fixed width, doesn't move */}
                  <div className="flex-shrink-0 w-[720px] flex flex-col border-l border-gray-200">
                    <ChatContent 
                      onClose={onClose} 
                      onFilesChange={handleFilesChange}
                      onCitationsChange={handleCitationsChange}
                      onCitationClick={handleCitationClick}
                      hideHeader={true}
                    />
                  </div>
                </div>
              </motion.div>
            </div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}

