'use client';

import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport } from 'ai';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Send, Loader2 } from 'lucide-react';
import { useRef, useEffect, useState } from 'react';

export function ChatUI() {
  const [input, setInput] = useState('');
  const { messages, sendMessage, status } = useChat({
    transport: new DefaultChatTransport({
      api: '/api/chat',
    }),
  });

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="flex flex-col h-full bg-white border border-gray-200 rounded-lg shadow-sm">
      {/* Chat Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-white rounded-t-lg">
        <h2 className="text-xl font-semibold text-gray-900">Chat Assistant</h2>
        <p className="text-sm text-gray-500 mt-1">Ask questions about your documents</p>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6" ref={scrollRef}>
        <div className="space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="mb-4 p-3 bg-gray-100 rounded-full">
                <Send className="h-6 w-6 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Start a conversation
              </h3>
              <p className="text-sm text-gray-500 max-w-sm">
                Ask questions about your uploaded documents to get started.
              </p>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-4 ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {message.role === 'assistant' && (
                <Avatar className="h-8 w-8 bg-blue-100 border border-blue-200">
                  <AvatarFallback className="bg-blue-100 text-blue-600 text-xs font-medium">
                    AI
                  </AvatarFallback>
                </Avatar>
              )}

              <Card
                className={`max-w-[80%] px-4 py-3 ${
                  message.role === 'user'
                    ? 'bg-blue-50 border-blue-200 text-blue-900'
                    : 'bg-gray-50 border-gray-200 text-gray-900'
                }`}
              >
                <p className="text-sm leading-relaxed whitespace-pre-wrap">
                  {message.parts
                    .filter((part): part is { type: 'text'; text: string } => part.type === 'text')
                    .map((part) => part.text)
                    .join('')}
                </p>
              </Card>

              {message.role === 'user' && (
                <Avatar className="h-8 w-8 bg-gray-100 border border-gray-200">
                  <AvatarFallback className="bg-gray-200 text-gray-600 text-xs font-medium">
                    You
                  </AvatarFallback>
                </Avatar>
              )}
            </div>
          ))}

          {status === 'streaming' && (
            <div className="flex gap-4 justify-start">
              <Avatar className="h-8 w-8 bg-blue-100 border border-blue-200">
                <AvatarFallback className="bg-blue-100 text-blue-600 text-xs font-medium">
                  AI
                </AvatarFallback>
              </Avatar>
              <Card className="px-4 py-3 bg-gray-50 border-gray-200">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
                  <span className="text-sm text-gray-500">Thinking...</span>
                </div>
              </Card>
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (input.trim() && status !== 'streaming') {
            sendMessage({ text: input });
            setInput('');
          }
        }}
        className="p-4 border-t border-gray-200 bg-white rounded-b-lg"
      >
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
              className="min-h-[60px] max-h-[120px] resize-none border-gray-300 focus:border-blue-400 focus:ring-blue-400 bg-white text-gray-900 placeholder:text-gray-400"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  if (input.trim() && status !== 'streaming') {
                    sendMessage({ text: input });
                    setInput('');
                  }
                }
              }}
              disabled={status === 'streaming'}
            />
          </div>
          <Button
            type="submit"
            disabled={status === 'streaming' || !input.trim()}
            className="h-[60px] px-6 bg-blue-600 hover:bg-blue-700 text-white border-0 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {status === 'streaming' ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </Button>
        </div>
        <p className="text-xs text-gray-400 mt-2 text-center">
          Press Enter to send, Shift+Enter for new line
        </p>
      </form>
    </div>
  );
}

