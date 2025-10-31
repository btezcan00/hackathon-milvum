'use client';

import { ChatUI } from "@/components/chat/chat-ui";
import { PDFViewer } from "@/components/pdf-viewer";
import { useState } from "react";

export default function Home() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedFileUrl, setSelectedFileUrl] = useState<string | null>(null);

  const handleFileSelected = (file: File | null) => {
    setSelectedFile(file);
    if (file) {
      const url = URL.createObjectURL(file);
      setSelectedFileUrl(url);
    } else {
      if (selectedFileUrl) {
        URL.revokeObjectURL(selectedFileUrl);
      }
      setSelectedFileUrl(null);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-white">
      {/* Government Header */}
      <header className="bg-white border-b border-gray-200 flex-shrink-0">
        <div className="max-w-full mx-auto px-6 py-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-[#154274] flex items-center justify-center">
              <span className="text-white font-bold text-xs">NL</span>
            </div>
            <h1 className="text-[#154274] text-lg font-normal">Overheid.nl</h1>
          </div>
        </div>
      </header>

      {/* Navigation Bar */}
      <nav className="bg-[#154274] text-white flex-shrink-0">
        <div className="max-w-full mx-auto px-6 py-3">
          <div className="flex items-center justify-between">
            <div className="text-sm">
              Home &gt; Documenten &gt; Vraag stellen
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content - Split Layout */}
      <main className="flex flex-1 overflow-hidden bg-white">
        {/* PDF Viewer - 40% width on left */}
        <div className="w-[40%] flex-shrink-0 h-[calc(100vh-160px)] border-r-2 border-gray-300">
          <PDFViewer
            file={selectedFile}
            fileUrl={selectedFileUrl}
            onClose={() => {
              if (selectedFileUrl) {
                URL.revokeObjectURL(selectedFileUrl);
              }
              setSelectedFile(null);
              setSelectedFileUrl(null);
            }}
          />
        </div>

        {/* Chat Area - 60% width on right */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="px-6 py-6 flex-shrink-0">
            <h2 className="text-2xl font-bold text-black mb-2">
              Stel een vraag over uw documenten
            </h2>
            <p className="text-base text-gray-700">
              U kunt vragen stellen over geüploade documenten. Typ uw vraag in het veld hieronder.
            </p>
          </div>
          
          {/* Chat UI Container */}
          <div className="flex-1 px-6 pb-6 overflow-hidden">
            <div className="h-full">
              <ChatUI onFileSelected={handleFileSelected} />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
