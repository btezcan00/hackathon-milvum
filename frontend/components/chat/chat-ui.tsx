'use client';

import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport } from 'ai';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { FileUpload } from '@/components/file-upload';
import { Send, Loader2 } from 'lucide-react';
import { useRef, useEffect, useState } from 'react';

interface ChatUIProps {
  onFileSelected?: (file: File | null) => void;
}

export function ChatUI({ onFileSelected }: ChatUIProps) {
  const [input, setInput] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
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

  const handleFilesSelected = async (files: File[]) => {
    setSelectedFiles(files);
    
    // Upload files to backend
    if (files.length > 0) {
      setUploading(true);
      try {
        const uploadPromises = files.map(async (file) => {
          const formData = new FormData();
          formData.append('file', file);
          
          const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData,
          });
          
          if (!response.ok) {
            throw new Error(`Failed to upload ${file.name}`);
          }
          
          return response.json();
        });

        await Promise.all(uploadPromises);
        
        // If first file is PDF, select it for viewing
        const firstPdf = files.find(f => f.type === 'application/pdf');
        if (firstPdf && onFileSelected) {
          onFileSelected(firstPdf);
        }
        
        // Note: We don't auto-send a message here to avoid interfering with chat flow
      } catch (error) {
        console.error('Upload error:', error);
        alert(`Er is een fout opgetreden bij het uploaden van de bestanden. Probeer het opnieuw.`);
      } finally {
        setUploading(false);
        setSelectedFiles([]);
      }
    } else if (onFileSelected) {
      onFileSelected(null);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white border border-gray-300">
      {/* Chat Header - Government Style */}
      <div className="px-6 py-4 bg-[#154274] text-white">
        <h2 className="text-lg font-bold text-white">Chat Assistent</h2>
        <p className="text-sm text-white/90 mt-1">Vraag informatie over uw documenten</p>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6" ref={scrollRef}>
        <div className="space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="mb-6 p-4 bg-gray-100">
                <Send className="h-8 w-8 text-[#154274]" />
              </div>
              <h3 className="text-lg font-bold text-black mb-3">
                Start een gesprek
              </h3>
              <p className="text-sm text-gray-700 max-w-md">
                Stel vragen over uw geüploade documenten om te beginnen.
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
                <div className="w-8 h-8 bg-[#154274] flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-xs font-bold">AI</span>
                </div>
              )}

              <div
                className={`max-w-[75%] px-5 py-3 border ${
                  message.role === 'user'
                    ? 'bg-white border-[#154274] text-black border-2'
                    : 'bg-gray-50 border-gray-300 text-black'
                }`}
              >
                <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ fontFamily: 'Verdana, sans-serif' }}>
                  {message.parts
                    .filter((part): part is { type: 'text'; text: string } => part.type === 'text')
                    .map((part) => part.text)
                    .join('')}
                </p>
              </div>

              {message.role === 'user' && (
                <div className="w-8 h-8 bg-gray-400 flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-xs font-bold">U</span>
                </div>
              )}
            </div>
          ))}

          {status === 'streaming' && (
            <div className="flex gap-4 justify-start">
              <div className="w-8 h-8 bg-[#154274] flex items-center justify-center flex-shrink-0">
                <span className="text-white text-xs font-bold">AI</span>
              </div>
              <div className="px-5 py-3 bg-gray-50 border border-gray-300">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-[#154274]" />
                  <span className="text-sm text-black">Bezig met verwerken...</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* File Upload Section */}
      <div className="px-5 py-4 border-t-2 border-gray-300 bg-gray-50">
        <FileUpload onFilesSelected={handleFilesSelected} maxFiles={10} />
      </div>

      {/* Input Area - Government Style */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (input.trim() && status !== 'streaming' && !uploading) {
            sendMessage({ text: input });
            setInput('');
          }
        }}
        className="p-5 border-t-2 border-gray-300 bg-white"
      >
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label htmlFor="chat-input" className="block text-sm font-bold text-black mb-2">
              Uw vraag:
            </label>
            <Textarea
              id="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Typ uw vraag hier..."
              className="min-h-[70px] max-h-[150px] resize-none border-2 border-gray-400 focus:border-[#154274] focus:ring-2 focus:ring-[#154274] bg-white text-black placeholder:text-gray-500"
              style={{ fontFamily: 'Verdana, sans-serif', fontSize: '14px' }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  if (input.trim() && status !== 'streaming' && !uploading) {
                    sendMessage({ text: input });
                    setInput('');
                  }
                }
              }}
              disabled={status === 'streaming' || uploading}
            />
          </div>
          <Button
            type="submit"
            disabled={status === 'streaming' || !input.trim() || uploading}
            className="h-[70px] px-8 bg-[#154274] hover:bg-[#0f3054] text-white border-0 font-bold disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            style={{ fontFamily: 'Verdana, sans-serif' }}
          >
            {uploading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin mr-2" />
                Uploaden...
              </>
            ) : status === 'streaming' ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <>
                <Send className="h-5 w-5 mr-2" />
                Verzenden
              </>
            )}
          </Button>
        </div>
        <p className="text-xs text-gray-600 mt-3 text-left" style={{ fontFamily: 'Verdana, sans-serif' }}>
          Druk op Enter om te verzenden, Shift+Enter voor een nieuwe regel
        </p>
      </form>
    </div>
  );
}

