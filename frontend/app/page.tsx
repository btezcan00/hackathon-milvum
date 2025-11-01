'use client';

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ChatModal } from "@/components/chat/chat-modal";

export default function Home() {
  const [isChatOpen, setIsChatOpen] = useState(false);

  return (
    <div className="min-h-screen bg-white">
      {/* Simple header with Chat button */}
      <header className="border-b border-gray-200">
        <div className="max-w-full mx-auto px-6 py-4">
          <div className="flex items-center justify-end">
            <Button
              onClick={() => setIsChatOpen(true)}
              className="bg-black text-white hover:bg-gray-800 rounded-lg px-6 py-2"
            >
              Chat
            </Button>
          </div>
        </div>
      </header>

      {/* Main content - completely white */}
      <main className="h-full bg-white">
      <div className="flex justify-center items-center gap-10 py-16">
        <img
          src="/milvum-logo.png"
          alt="Milvum logo"
          className="h-32 w-auto object-contain"
          style={{ height: '128px' }}
        />
        <img
          src="/terminal-logo.svg"
          alt="Terminal Woo"
          className="h-32 w-auto object-contain"
          style={{ height: '128px' }}
        />
      </div>
      </main>

      {/* Chat Modal */}
      <ChatModal isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />
    </div>
  );
}
