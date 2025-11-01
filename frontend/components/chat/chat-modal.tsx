'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
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
              {/* Files Panel - extends left when files exist */}
              <AnimatePresence>
                {showFilesPanel && (
                  <motion.div
                    initial={{ width: 0, opacity: 0 }}
                    animate={{ width: 400, opacity: 1 }}
                    exit={{ width: 0, opacity: 0 }}
                    transition={{ duration: 0.3, ease: 'easeInOut' }}
                    className="pointer-events-auto h-full"
                  >
                    <FilesPanel files={uploadedFiles} onClose={() => setShowFilesPanel(false)} />
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Chat Modal - floats on the right with scale/fade animation */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
                onClick={(e) => e.stopPropagation()}
                className="pointer-events-auto w-full max-w-2xl h-[90vh] max-h-[800px] bg-white shadow-2xl  overflow-hidden flex flex-col"
              >
                <ChatContent 
                  onClose={onClose} 
                  onFilesChange={handleFilesChange}
                />
              </motion.div>
            </div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}

