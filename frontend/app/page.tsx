import { ChatUI } from "@/components/chat/chat-ui";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-white">
      {/* Government Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-[#154274] flex items-center justify-center">
              <span className="text-white font-bold text-xs">NL</span>
            </div>
            <h1 className="text-[#154274] text-lg font-normal">Overheid.nl</h1>
          </div>
        </div>
      </header>

      {/* Navigation Bar */}
      <nav className="bg-[#154274] text-white">
        <div className="max-w-7xl mx-auto px-6 py-3">
          <div className="flex items-center justify-between">
            <div className="text-sm">
              Home &gt; Documenten &gt; Vraag stellen
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex flex-1 flex-col bg-white">
        <div className="max-w-4xl mx-auto w-full px-6 py-8">
          <h2 className="text-2xl font-bold text-black mb-4">
            Stel een vraag over uw documenten
          </h2>
          <p className="text-base text-gray-700 mb-6">
            U kunt vragen stellen over geüploade documenten. Typ uw vraag in het veld hieronder.
          </p>
          
          {/* Chat UI Container */}
          <div className="h-[calc(100vh-280px)] min-h-[600px]">
            <ChatUI />
          </div>
        </div>
      </main>
    </div>
  );
}
