'use client';

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { ChatModal } from "@/components/chat/chat-modal";
import { AnimatedBeamMultipleOutputDemo } from "@/components/animated-beam-demo";
import { Confetti, type ConfettiRef } from "@/components/ui/confetti";

export default function Home() {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const confettiRef = useRef<ConfettiRef>(null);

  return (
    <div className="min-h-screen bg-white relative">
    
      {/* Simple header with Chat button */}
      <header className="border-b border-gray-200">
        <div className="max-w-full mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <a
                href="/woo-requests"
                className="text-gray-700 hover:text-gray-900 font-medium transition-colors"
              >
                WOO Requests
              </a>
            </div>
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
      <div className="flex justify-center items-center gap-10 pt-16 pb-4">
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
      
      {/* <div className="flex flex-col justify-center items-center">

        <AnimatedBeamMultipleOutputDemo />
      </div> */}
      </main>

      {/* Chat Modal */}
      <ChatModal isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />
    </div>
  );
}
