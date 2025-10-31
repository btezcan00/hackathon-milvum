import { ChatUI } from "@/components/chat/chat-ui";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-br from-gray-50 to-blue-50">
      <main className="flex flex-1 flex-col">
        {/* Chat UI - Full Screen Focus */}
        <div className="flex flex-1 items-center justify-center p-4 sm:p-6 lg:p-8">
          <div className="w-full max-w-6xl h-full max-h-[90vh]">
            <ChatUI />
          </div>
        </div>
      </main>
    </div>
  );
}
