'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { useEffect, useState } from 'react';

interface WooDocument {
  id: string;
  score: number;
  woo_request: string;
  contact_people?: string;
  departments?: string;
  documents?: string;
  metadata?: Record<string, any>;
}

interface WooHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  wooRequest: string;
}

export function WooHistoryModal({ isOpen, onClose, wooRequest }: WooHistoryModalProps) {
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState<WooDocument[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && wooRequest) {
      fetchSimilarDocuments();
    }
  }, [isOpen, wooRequest]);

  const fetchSimilarDocuments = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:5001/api/woo-history', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          woo_request: wooRequest,
          top_k: 3,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch similar documents');
      }

      const data = await response.json();
      setDocuments(data.similar_documents || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
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
            className="fixed inset-0 bg-black/20 z-[60]"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            onClick={(e) => e.stopPropagation()}
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-[70] w-[90vw] max-w-3xl max-h-[80vh] bg-white rounded-lg shadow-2xl overflow-hidden flex flex-col"
          >
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-white flex-shrink-0">
              <h2 className="text-lg font-semibold text-gray-900">WOO History - Similar Documents</h2>
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="text-gray-600 hover:text-gray-900"
              >
                Close
              </Button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {loading && (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
              )}

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
                  <p className="font-medium">Error</p>
                  <p className="text-sm mt-1">{error}</p>
                </div>
              )}

              {!loading && !error && documents.length === 0 && (
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center text-gray-600">
                  <p>No similar documents found.</p>
                </div>
              )}

              {!loading && !error && documents.length > 0 && (
                <div className="space-y-4">
                  {documents.map((doc, index) => (
                    <div
                      key={doc.id}
                      className="bg-gray-50 border border-gray-200 rounded-lg p-5 hover:border-blue-400 transition-colors"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-start gap-2">
                          <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-bold flex-shrink-0 mt-0.5">
                            {index + 1}
                          </span>
                          <div className="flex-1">
                            <h3 className="font-semibold text-gray-900 text-sm mb-1">
                              Similar WOO Request
                            </h3>
                            <p className="text-sm text-gray-700 leading-relaxed">
                              {doc.woo_request}
                            </p>
                          </div>
                        </div>
                        <span className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-1 rounded flex-shrink-0 ml-2">
                          {(doc.score * 100).toFixed(1)}% match
                        </span>
                      </div>

                      <div className="mt-3 pt-3 border-t border-gray-200 space-y-2">
                        {doc.contact_people && (
                          <div className="flex gap-2">
                            <span className="text-xs font-medium text-gray-500 w-24 flex-shrink-0">Contact:</span>
                            <span className="text-xs text-gray-700">{doc.contact_people}</span>
                          </div>
                        )}
                        {doc.departments && (
                          <div className="flex gap-2">
                            <span className="text-xs font-medium text-gray-500 w-24 flex-shrink-0">Departments:</span>
                            <span className="text-xs text-gray-700">{doc.departments}</span>
                          </div>
                        )}
                        {doc.documents && (
                          <div className="flex gap-2">
                            <span className="text-xs font-medium text-gray-500 w-24 flex-shrink-0">Documents:</span>
                            <span className="text-xs text-gray-700 break-all">{doc.documents}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
