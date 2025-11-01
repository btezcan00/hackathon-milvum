'use client';

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ChatModal } from "@/components/chat/chat-modal";
import { MessageSquare, FileText, Calendar, User, Mail, Phone, Building2, AlertCircle, Clock, CheckCircle, XCircle, Eye, Download, Send, Filter, Search } from "lucide-react";

// Mock data voor WOO verzoeken
const mockRequests = [
  {
    id: 'WOO-2024-1847',
    onderwerp: 'Documenten over infrastructuurproject A2-corridor',
    naam: 'Jan de Vries',
    email: 'j.devries@example.nl',
    organisatie: 'NRC Handelsblad',
    datum: '01-11-2024',
    status: 'nieuw',
    prioriteit: 'hoog',
    deadline: '29-11-2024',
    toelichting: 'Graag zou ik alle documenten willen ontvangen met betrekking tot de besluitvorming over de verbreding van de A2-corridor tussen Utrecht en Amsterdam in de periode 2020-2024. Dit betreft correspondentie, memo\'s, adviezen en besluitenlijsten.',
    voorkeursperiode: 'januari 2020 - december 2024',
    telefoon: '06-12345678'
  },
  {
    id: 'WOO-2024-1846',
    onderwerp: 'Subsidieaanvragen duurzame energie 2023',
    naam: 'Maria Jansen',
    email: 'm.jansen@example.nl',
    organisatie: 'Follow the Money',
    datum: '30-10-2024',
    status: 'in_behandeling',
    prioriteit: 'normaal',
    deadline: '27-11-2024',
    toelichting: 'Ik verzoek om inzage in alle subsidieaanvragen voor duurzame energieprojecten die in 2023 zijn ingediend, inclusief de beoordelingsrapporten en de uiteindelijke besluiten.',
    voorkeursperiode: 'geheel 2023',
    telefoon: '06-87654321'
  },
  {
    id: 'WOO-2024-1845',
    onderwerp: 'Beleidsstukken woningbouw Rotterdam',
    naam: 'Ahmed El Amrani',
    email: 'a.elamrani@example.nl',
    organisatie: 'Trouw',
    datum: '15-10-2024',
    status: 'afgerond',
    prioriteit: 'laag',
    deadline: '12-11-2024',
    toelichting: 'Alle beleidsstukken en adviezen die hebben geleid tot het nieuwe woningbouwplan in Rotterdam-Zuid.',
    voorkeursperiode: 'september 2023 - maart 2024',
    telefoon: '06-11223344'
  },
  {
    id: 'WOO-2024-1844',
    onderwerp: 'Correspondentie klimaatakkoord',
    naam: 'Sophie Bakker',
    email: 's.bakker@example.nl',
    organisatie: 'De Correspondent',
    datum: '22-10-2024',
    status: 'in_behandeling',
    prioriteit: 'hoog',
    deadline: '19-11-2024',
    toelichting: 'Alle correspondentie tussen het ministerie en bedrijven over het klimaatakkoord voor de industrie.',
    voorkeursperiode: 'januari 2023 - heden',
    telefoon: ''
  },
];

export default function Home() {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState(mockRequests[0]);
  const [filterStatus, setFilterStatus] = useState('alle');

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'nieuw': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'in_behandeling': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'afgerond': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'nieuw': return <Clock className="h-4 w-4" />;
      case 'in_behandeling': return <AlertCircle className="h-4 w-4" />;
      case 'afgerond': return <CheckCircle className="h-4 w-4" />;
      default: return null;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'nieuw': return 'Nieuw';
      case 'in_behandeling': return 'In behandeling';
      case 'afgerond': return 'Afgerond';
      default: return status;
    }
  };

  const getPrioriteitColor = (prioriteit: string) => {
    switch (prioriteit) {
      case 'hoog': return 'text-red-600';
      case 'normaal': return 'text-gray-600';
      case 'laag': return 'text-green-600';
      default: return 'text-gray-600';
    }
  };

  const filteredRequests = filterStatus === 'alle' 
    ? mockRequests 
    : mockRequests.filter(r => r.status === filterStatus);

  return (
    <div className="min-h-screen bg-gray-50 relative">
      {/* Internal System Header */}
      <header className="bg-[#154273] text-white border-b-4 border-[#01689b]">
        <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <FileText className="h-8 w-8" />
              <div>
                <h1 className="text-lg font-bold">WOO Verzoeken Beheer</h1>
                <p className="text-xs text-white/80">Intern systeem • Ministerie van Algemene Zaken</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm">Ingelogd als: <span className="font-semibold">J. Administrateur</span></span>
              <a
                href="/woo-requests"
                className="text-white hover:text-gray-200 text-sm transition-colors"
              >
                Publiek overzicht
              </a>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Stats Overview */}
        

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: List of Requests */}
          <div className="lg:col-span-1 space-y-4">
            {/* Filters */}
            <div className="bg-white p-4 rounded border border-gray-200">
              <h3 className="font-bold text-gray-900 mb-3 flex items-center gap-2">
                <Filter className="h-4 w-4" />
                Filters
              </h3>
              <div className="space-y-2">
                <button
                  onClick={() => setFilterStatus('alle')}
                  className={`w-full text-left px-3 py-2 rounded text-sm ${
                    filterStatus === 'alle' ? 'bg-[#154273] text-white' : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  Alle verzoeken ({mockRequests.length})
                </button>
                <button
                  onClick={() => setFilterStatus('nieuw')}
                  className={`w-full text-left px-3 py-2 rounded text-sm ${
                    filterStatus === 'nieuw' ? 'bg-[#154273] text-white' : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  Nieuw ({mockRequests.filter(r => r.status === 'nieuw').length})
                </button>
                <button
                  onClick={() => setFilterStatus('in_behandeling')}
                  className={`w-full text-left px-3 py-2 rounded text-sm ${
                    filterStatus === 'in_behandeling' ? 'bg-[#154273] text-white' : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  In behandeling ({mockRequests.filter(r => r.status === 'in_behandeling').length})
                </button>
                <button
                  onClick={() => setFilterStatus('afgerond')}
                  className={`w-full text-left px-3 py-2 rounded text-sm ${
                    filterStatus === 'afgerond' ? 'bg-[#154273] text-white' : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  Afgerond ({mockRequests.filter(r => r.status === 'afgerond').length})
                </button>
              </div>
            </div>

            {/* List */}
            <div className="space-y-2">
              {filteredRequests.map((request) => (
                <button
                  key={request.id}
                  onClick={() => setSelectedRequest(request)}
                  className={`w-full text-left p-4 rounded border-2 transition-all ${
                    selectedRequest.id === request.id
                      ? 'border-[#01689b] bg-blue-50'
                      : 'border-gray-200 bg-white hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <span className="text-xs font-mono text-gray-500">{request.id}</span>
                    <div className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs border ${getStatusColor(request.status)}`}>
                      {getStatusIcon(request.status)}
                      <span className="font-medium">{getStatusText(request.status)}</span>
                    </div>
                  </div>
                  <h4 className="font-semibold text-gray-900 mb-1 line-clamp-2">{request.onderwerp}</h4>
                  <div className="flex items-center gap-2 text-xs text-gray-600">
                    <User className="h-3 w-3" />
                    <span>{request.naam}</span>
                  </div>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-xs text-gray-500" suppressHydrationWarning>{request.datum}</span>
                    <span className={`text-xs font-medium ${getPrioriteitColor(request.prioriteit)}`}>
                      {request.prioriteit.charAt(0).toUpperCase() + request.prioriteit.slice(1)}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Right: Request Detail */}
          <div className="lg:col-span-2">
            <div className="bg-white border border-gray-200 rounded shadow-sm">
              {/* Header */}
              <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="text-xl font-bold text-[#154273] mb-1">{selectedRequest.onderwerp}</h2>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-mono text-gray-600">{selectedRequest.id}</span>
                      <span className="text-gray-300">•</span>
                      <span className="text-sm text-gray-600" suppressHydrationWarning>Ontvangen: {selectedRequest.datum}</span>
                      <span className="text-gray-300">•</span>
                      <span className={`text-sm font-medium ${getPrioriteitColor(selectedRequest.prioriteit)}`}>
                        Prioriteit: {selectedRequest.prioriteit}
                      </span>
                    </div>
                  </div>
                  <div className={`flex items-center gap-2 px-3 py-1.5 rounded border ${getStatusColor(selectedRequest.status)}`}>
                    {getStatusIcon(selectedRequest.status)}
                    <span className="font-semibold">{getStatusText(selectedRequest.status)}</span>
                  </div>
                </div>
              </div>

              {/* Content */}
              <div className="p-6 space-y-6">
                {/* Verzoek Details */}
                <div>
                  <h3 className="text-sm font-bold text-gray-900 mb-3">Toelichting</h3>
                  <p className="text-sm text-gray-700 leading-relaxed bg-gray-50 p-4 rounded border border-gray-200">
                    {selectedRequest.toelichting}
                  </p>
                </div>

                {/* Tijdsperiode */}
                <div>
                  <h3 className="text-sm font-bold text-gray-900 mb-2">Gevraagde periode</h3>
                  <div className="flex items-center gap-2 text-sm text-gray-700">
                    <Calendar className="h-4 w-4 text-gray-400" />
                    <span>{selectedRequest.voorkeursperiode}</span>
                  </div>
                </div>

                {/* Deadline */}
                <div className="bg-yellow-50 border border-yellow-200 p-4 rounded">
                  <div className="flex items-center gap-2">
                    <Clock className="h-5 w-5 text-yellow-600" />
                    <div>
                      <p className="text-sm font-bold text-gray-900">Behandeltermijn</p>
                      <p className="text-sm text-gray-700" suppressHydrationWarning>Uiterste reactiedatum: <span className="font-semibold">{selectedRequest.deadline}</span></p>
                    </div>
                  </div>
                </div>

                {/* Aanvrager */}
                <div className="border-t pt-6">
                  <h3 className="text-sm font-bold text-gray-900 mb-4">Gegevens aanvrager</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs text-gray-600 mb-1">Naam</p>
                      <div className="flex items-center gap-2">
                        <User className="h-4 w-4 text-gray-400" />
                        <p className="text-sm font-medium text-gray-900">{selectedRequest.naam}</p>
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-gray-600 mb-1">Organisatie</p>
                      <div className="flex items-center gap-2">
                        <Building2 className="h-4 w-4 text-gray-400" />
                        <p className="text-sm font-medium text-gray-900">{selectedRequest.organisatie}</p>
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-gray-600 mb-1">E-mail</p>
                      <div className="flex items-center gap-2">
                        <Mail className="h-4 w-4 text-gray-400" />
                        <p className="text-sm font-medium text-gray-900">{selectedRequest.email}</p>
                      </div>
                    </div>
                    <div>
                      <p className="text-xs text-gray-600 mb-1">Telefoon</p>
                      <div className="flex items-center gap-2">
                        <Phone className="h-4 w-4 text-gray-400" />
                        <p className="text-sm font-medium text-gray-900">
                          {selectedRequest.telefoon || 'Niet opgegeven'}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between gap-3">
                <div className="flex gap-2">
                  <Button
                    onClick={() => alert('AI Assistent starten voor dit verzoek...')}
                    className="bg-[#01689b] hover:bg-[#154273] text-white flex items-center gap-2"
                  >
                    <MessageSquare className="h-4 w-4" />
                    Chat starten
                  </Button>
                  <Button
                    onClick={() => alert('Documenten zoeken in archief...')}
                    variant="outline"
                    className="flex items-center gap-2"
                  >
                    <Search className="h-4 w-4" />
                    Documenten zoeken
                  </Button>
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={() => alert('Status wijzigen naar In behandeling')}
                    variant="outline"
                    className="text-sm"
                  >
                    Status wijzigen
                  </Button>
                  <Button
                    onClick={() => alert('Reactie opstellen')}
                    className="bg-green-600 hover:bg-green-700 text-white flex items-center gap-2"
                  >
                    <Send className="h-4 w-4" />
                    Reageren
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Floating Chat Button - Bottom Right */}
      <button
        onClick={() => setIsChatOpen(true)}
        className="fixed bottom-6 right-6 bg-[#01689b] hover:bg-[#154273] text-white rounded-full p-4 shadow-lg hover:shadow-xl transition-all duration-300 z-50 group"
        aria-label="Open chat"
      >
        <MessageSquare className="h-6 w-6" />
        <span className="absolute right-full mr-3 top-1/2 -translate-y-1/2 bg-gray-900 text-white px-3 py-1.5 rounded-md text-sm font-medium whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
          Chat met AI Assistent
        </span>
      </button>

      {/* Chat Modal */}
      <ChatModal isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />
    </div>
  );
}
