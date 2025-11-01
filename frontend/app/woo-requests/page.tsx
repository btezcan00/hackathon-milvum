'use client';

import { useState } from 'react';
import { WooRequestsTable } from '@/components/woo-requests/woo-requests-table';
import { WooRequestDetailModal } from '@/components/woo-requests/woo-request-detail-modal';
import { ChatModal } from '@/components/chat/chat-modal';
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

interface WooRequest {
  id: string;
  woo_request: string;
  contact_people: string;
  departments: string;
  documents: string;
  handled_date?: string;
}

export default function WooRequestsPage() {
  const [selectedRequest, setSelectedRequest] = useState<WooRequest | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showChatModal, setShowChatModal] = useState(false);
  const [chatContext, setChatContext] = useState<string>('');

  const handleViewDetails = (request: WooRequest) => {
    setSelectedRequest(request);
    setShowDetailModal(true);
  };

  const handleChat = (request: WooRequest) => {
    setSelectedRequest(request);
    setChatContext(request.woo_request);
    setShowChatModal(true);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/">
                <Button variant="ghost" size="sm" className="gap-2">
                  <ArrowLeft className="w-4 h-4" />
                  Back
                </Button>
              </Link>
              <h1 className="text-2xl font-bold text-gray-900">WOO Requests</h1>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="mb-6">
          <p className="text-gray-600">
            View and manage all previous WOO (Wet open overheid) requests.
            Click on a request to view details or chat about it.
          </p>
        </div>

        <WooRequestsTable
          onViewDetails={handleViewDetails}
          onChat={handleChat}
        />
      </main>

      {/* Modals */}
      <WooRequestDetailModal
        isOpen={showDetailModal}
        onClose={() => setShowDetailModal(false)}
        request={selectedRequest}
      />

      <ChatModal
        isOpen={showChatModal}
        onClose={() => setShowChatModal(false)}
      />
    </div>
  );
}
