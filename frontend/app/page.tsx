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
      <main className="min-h-[calc(100vh-80px)] bg-white">
        {/* Empty white space */}
      </main>

      {/* Chat Modal */}
      <ChatModal isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />
    </div>
  );
}
