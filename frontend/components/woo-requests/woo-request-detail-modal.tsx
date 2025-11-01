'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { X, FileText, Users, Building2, Calendar } from 'lucide-react';

interface WooRequest {
  id: string;
  woo_request: string;
  contact_people: string;
  departments: string;
  documents: string;
  handled_date?: string;
}

interface WooRequestDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  request: WooRequest | null;
}

export function WooRequestDetailModal({ isOpen, onClose, request }: WooRequestDetailModalProps) {
  if (!request) return null;

  const contactPeople = request.contact_people.split(',').map(c => c.trim());
  const departments = request.departments.split(',').map(d => d.trim());
  const documents = request.documents.split(',').map(d => d.trim());

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
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-[70] w-[90vw] max-w-3xl max-h-[85vh] bg-white rounded-lg shadow-2xl overflow-hidden flex flex-col"
          >
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-white flex-shrink-0">
              <h2 className="text-lg font-semibold text-gray-900">WOO Request Details</h2>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
              <div className="space-y-6">
                {/* WOO Request */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                    <FileText className="w-4 h-4" />
                    WOO Request
                  </h3>
                  <p className="text-sm text-gray-900 leading-relaxed bg-gray-50 p-4 rounded-lg">
                    {request.woo_request}
                  </p>
                </div>

                {/* Contact People */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                    <Users className="w-4 h-4" />
                    Handled By
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {contactPeople.map((person, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                      >
                        {person}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Departments */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                    <Building2 className="w-4 h-4" />
                    Departments
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {departments.map((dept, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800"
                      >
                        {dept}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Documents */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                    <FileText className="w-4 h-4" />
                    Attached Documents ({documents.length})
                  </h3>
                  <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                    {documents.map((doc, index) => (
                      <div
                        key={index}
                        className="flex items-center gap-2 text-sm text-gray-700"
                      >
                        <div className="w-2 h-2 rounded-full bg-gray-400"></div>
                        <span className="break-all">{doc}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Date Handled */}
                {request.handled_date && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                      <Calendar className="w-4 h-4" />
                      Date Handled
                    </h3>
                    <p className="text-sm text-gray-900">
                      {new Date(request.handled_date).toLocaleDateString('nl-NL', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                      })}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-end">
              <Button
                onClick={onClose}
                variant="outline"
              >
                Close
              </Button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
