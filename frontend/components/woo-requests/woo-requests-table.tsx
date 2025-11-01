'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { MessageSquare } from 'lucide-react';

interface WooRequest {
  id: string;
  woo_request: string;
  contact_people: string;
  departments: string;
  documents: string;
  handled_date?: string;
}

interface WooRequestsTableProps {
  onViewDetails: (request: WooRequest) => void;
  onChat: (request: WooRequest) => void;
}

export function WooRequestsTable({ onViewDetails, onChat }: WooRequestsTableProps) {
  const [requests, setRequests] = useState<WooRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchWooRequests();
  }, []);

  const fetchWooRequests = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:5001/api/woo-requests');

      if (!response.ok) {
        throw new Error('Failed to fetch WOO requests');
      }

      const data = await response.json();
      setRequests(data.woo_requests || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const getTaskName = (wooRequest: string) => {
    // Extract first 80 characters as task name
    return wooRequest.length > 80 ? wooRequest.substring(0, 80) + '...' : wooRequest;
  };

  const getHandlerName = (contactPeople: string) => {
    // Get first contact person
    const contacts = contactPeople.split(',');
    return contacts[0]?.trim() || 'Unknown';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
        <p className="font-medium">Error</p>
        <p className="text-sm mt-1">{error}</p>
      </div>
    );
  }

  if (requests.length === 0) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center text-gray-600">
        <p>No WOO requests found.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Task / WOO Request
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Handled By
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Department
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {requests.map((request) => (
            <tr
              key={request.id}
              className="hover:bg-gray-50 cursor-pointer transition-colors"
              onClick={() => onViewDetails(request)}
            >
              <td className="px-6 py-4">
                <div className="text-sm font-medium text-gray-900">
                  {getTaskName(request.woo_request)}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-gray-700">
                  {getHandlerName(request.contact_people)}
                </div>
              </td>
              <td className="px-6 py-4">
                <div className="text-sm text-gray-700">
                  {request.departments.split(',')[0]?.trim() || 'N/A'}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    onChat(request);
                  }}
                  className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                >
                  <MessageSquare className="w-4 h-4" />
                  Chat
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
