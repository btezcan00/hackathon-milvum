'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { ChatContent } from './chat-content';
import { FilesPanel } from './files-panel';
import type { FileWithMetadata } from './files-panel';

interface ChatModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ChatModal({ isOpen, onClose }: ChatModalProps) {
  const [uploadedFiles, setUploadedFiles] = useState<FileWithMetadata[]>([]);
  const [showFilesPanel, setShowFilesPanel] = useState(false);

  const handleFilesChange = (files: FileWithMetadata[]) => {
    setUploadedFiles(files);
    setShowFilesPanel(files.length > 0);
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
                          onClose={() => {
                            setShowFilesPanel(false);
                            setUploadedFiles([]);
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

