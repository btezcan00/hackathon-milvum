'use client';

import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Send, Loader2, Plus, Search } from 'lucide-react';
import { useRef, useEffect, useState, DragEvent } from 'react';
import { CitationList, type Citation } from '@/components/citations/citation-list';
import { createHighlightUrl } from '@/components/citations/citation-highlighter';
import { CrawlingWebsites, type CrawlingWebsite } from '@/components/chat/crawling-websites';

interface ChatUIProps {
  onFileSelected?: (file: File | null) => void;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
}

export function ChatUI({ onFileSelected }: ChatUIProps) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [researchMode, setResearchMode] = useState(false);
  const [researchUrls, setResearchUrls] = useState<string>('');
  const [crawlingWebsites, setCrawlingWebsites] = useState<CrawlingWebsite[]>([]);
  const [isCrawling, setIsCrawling] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const messageIdCounter = useRef<number>(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const validateFiles = (files: File[]): File[] => {
    return files.filter(file => {
      const ext = file.name.split('.').pop()?.toLowerCase();
      const allowedTypes = ['pdf', 'txt', 'doc', 'docx', 'md'];
      const isValidExt = allowedTypes.includes(ext || '');
      const isValidMime = file.type === 'application/pdf' || 
                         file.type.startsWith('text/') ||
                         file.type.includes('document') ||
                         file.type.includes('word');
      return isValidExt || isValidMime;
    });
  };

  const handleFilesSelected = async (files: File[]) => {
    const validFiles = validateFiles(files);
    
    if (validFiles.length === 0 && files.length > 0) {
      alert('Alleen PDF, TXT, DOC, DOCX en MD bestanden zijn toegestaan.');
      return;
    }

    setSelectedFiles(validFiles);

    // Upload files to backend
    if (validFiles.length > 0) {
      setUploading(true);
      try {
        const uploadPromises = validFiles.map(async (file) => {
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
        const firstPdf = validFiles.find(f => f.type === 'application/pdf');
        if (firstPdf && onFileSelected) {
          onFileSelected(firstPdf);
        }
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

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFilesSelected(files);
    }
  };

  const openFileDialog = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      handleFilesSelected(files);
    }
  };

  const sendMessage = async (content: string) => {
    if (!content.trim() || streaming) return;

    messageIdCounter.current += 1;
    const userMessage: Message = {
      id: `user-${messageIdCounter.current}`,
      role: 'user',
      content,
    };

    setMessages(prev => [...prev, userMessage]);
    setStreaming(true);

    try {
      // If research mode is enabled, use research endpoint
      if (researchMode) {
        const urls = researchUrls.trim() ? researchUrls.split('\n').filter(url => url.trim()).map(url => url.trim()) : [];
        
        // Show crawling indicator
        setIsCrawling(true);
        setCrawlingWebsites([]); // Clear previous websites
        
        const response = await fetch('/api/research', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query: content,
            urls: urls.length > 0 ? urls : undefined, // Only send if provided
            max_results: 5,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ error: response.statusText }));
          setIsCrawling(false);
          throw new Error(errorData.error || `Failed to get research response (${response.status})`);
        }

        const data = await response.json();
        
        // Update crawling websites from response
        if (data.selected_websites && Array.isArray(data.selected_websites)) {
          setCrawlingWebsites(data.selected_websites);
        }
        setIsCrawling(false);

        messageIdCounter.current += 1;
        const assistantMessage: Message = {
          id: `assistant-${messageIdCounter.current}`,
          role: 'assistant',
          content: data.answer || 'Geen antwoord ontvangen.',
          citations: data.citations || [],
        };

        setMessages(prev => [...prev, assistantMessage]);
        setStreaming(false);
        return;
      }

      // Regular chat mode
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: [...messages, userMessage],
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      // Read the stream
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('No response body');
      }

      messageIdCounter.current += 1;
      const assistantMessage: Message = {
        id: `assistant-${messageIdCounter.current}`,
        role: 'assistant',
        content: '',
      };

      setMessages(prev => [...prev, assistantMessage]);

      let hasReceivedContent = false;
      let errorOccurred = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(line => line.trim() !== '');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              // Stream is complete
              // If no content was received, show an error
              if (!hasReceivedContent && !errorOccurred) {
                assistantMessage.content = '⚠️ Geen antwoord ontvangen. Controleer uw verbinding of probeer het opnieuw.';
                setMessages(prev => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1] = { ...assistantMessage };
                  return newMessages;
                });
              }
              continue;
            }

            try {
              const json = JSON.parse(data);
              
              // Handle error messages
              if (json.type === 'error') {
                errorOccurred = true;
                assistantMessage.content = `⚠️ ${json.error || 'Er is een fout opgetreden'}`;
                setMessages(prev => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1] = { ...assistantMessage };
                  return newMessages;
                });
                break; // Stop reading stream on error
              }
              
              // Handle text content
              if (json.type === 'text' && json.text) {
                hasReceivedContent = true;
                assistantMessage.content += json.text;
                setMessages(prev => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1] = { ...assistantMessage };
                  return newMessages;
                });
              }
              
              // Fallback: support Groq format for compatibility
              if (!json.type && json.choices?.[0]?.delta?.content) {
                hasReceivedContent = true;
                const content = json.choices[0].delta.content;
                assistantMessage.content += content;
                setMessages(prev => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1] = { ...assistantMessage };
                  return newMessages;
                });
              }
            } catch (e) {
              console.error('Error parsing SSE:', e, 'Data:', data);
            }
          }
        }
      }

      // Final check: if we still have no content and no error, show a message
      if (!hasReceivedContent && !errorOccurred && assistantMessage.content === '') {
        assistantMessage.content = '⚠️ Geen antwoord ontvangen van de server.';
        setMessages(prev => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1] = { ...assistantMessage };
          return newMessages;
        });
      }
      } catch (error) {
        console.error('Chat error:', error);
        const errorMessage = error instanceof Error ? error.message : 'Er is een fout opgetreden. Probeer het opnieuw.';
        alert(errorMessage);
        
        // Show error message in chat
        messageIdCounter.current += 1;
        const errorMsg: Message = {
          id: `error-${messageIdCounter.current}`,
          role: 'assistant',
          content: `⚠️ Fout: ${errorMessage}`,
        };
        setMessages(prev => [...prev, errorMsg]);
      } finally {
      setStreaming(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white border border-gray-300">
      {/* Chat Header - Government Style */}
      <div className="px-6 py-4 bg-[#154274] text-white">
        <h2 className="text-lg font-bold text-white">Chat Assistent</h2>
        <p className="text-sm text-white/90 mt-1">Vraag informatie over uw documenten</p>
      </div>

      {/* Messages Area - with drag and drop */}
      <div 
        className="flex-1 overflow-y-auto px-4 py-6 relative"
        ref={scrollRef}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Drag overlay - shown when dragging files */}
        {isDragOver && (
          <div className="absolute inset-0 bg-[#154274]/10 border-4 border-dashed border-[#154274] flex items-center justify-center z-50 pointer-events-none">
            <div className="bg-white px-6 py-4 rounded-lg shadow-lg border-2 border-[#154274]">
              <p className="text-lg font-bold text-[#154274]" style={{ fontFamily: 'Verdana, sans-serif' }}>
                Laat bestanden hier los om te uploaden
              </p>
            </div>
          </div>
        )}
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
                  {message.content}
                </p>
                {message.role === 'assistant' && message.citations && message.citations.length > 0 && (
                  <CitationList
                    citations={message.citations}
                    onCitationClick={(citation) => {
                      const url = createHighlightUrl(citation);
                      window.open(url, '_blank');
                    }}
                  />
                )}
              </div>

              {message.role === 'user' && (
                <div className="w-8 h-8 bg-gray-400 flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-xs font-bold">U</span>
                </div>
              )}
            </div>
          ))}

          {streaming && (
            <div className="flex flex-col gap-3">
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
              {/* Show crawling websites if in research mode */}
              {researchMode && (isCrawling || crawlingWebsites.length > 0) && (
                <div className="ml-12">
                  <CrawlingWebsites 
                    websites={crawlingWebsites} 
                    isCrawling={isCrawling}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Input Area - Government Style */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (input.trim() && !streaming && !uploading) {
            sendMessage(input);
            setInput('');
          }
        }}
        className="p-5 border-t-2 border-gray-300 bg-white"
      >
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.txt,.doc,.docx,.md"
          onChange={handleFileSelect}
          className="hidden"
        />

        {/* Research Mode Toggle */}
        <div className="mb-3 flex items-center gap-2">
          <button
            type="button"
            onClick={() => setResearchMode(!researchMode)}
            disabled={streaming || uploading}
            className={`flex items-center gap-2 px-3 py-1.5 rounded border-2 transition-colors ${
              researchMode
                ? 'bg-[#154274] text-white border-[#154274]'
                : 'bg-white text-[#154274] border-[#154274] hover:bg-[#154274]/10'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
            style={{ fontFamily: 'Verdana, sans-serif', fontSize: '12px' }}
          >
            <Search className="h-3 w-3" />
            <span>Diep Onderzoek</span>
          </button>
          {researchMode && (
            <div className="flex-1">
              <Textarea
                placeholder="Voer URLs in (één per regel)"
                value={researchUrls}
                onChange={(e) => setResearchUrls(e.target.value)}
                disabled={streaming || uploading}
                className="min-h-[40px] max-h-[80px] resize-none px-3 py-1.5 border-2 border-gray-400 focus:border-[#154274] focus:ring-2 focus:ring-[#154274] bg-white text-black placeholder:text-gray-500 text-xs"
                style={{ fontFamily: 'Verdana, sans-serif' }}
              />
            </div>
          )}
        </div>

        <div className="flex gap-3 items-end">
          {/* Plus button on the left - centered with textarea */}
          <button
            type="button"
            onClick={openFileDialog}
            disabled={streaming || uploading}
            className="w-8 h-8 bg-[#154274] hover:bg-[#0f3054] text-white flex items-center justify-center rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
            aria-label="Bestand toevoegen"
          >
            <Plus className="h-4 w-4" />
          </button>

          <div className="flex-1">
            <label htmlFor="chat-input" className="block text-sm font-bold text-black mb-2">
              Uw vraag:
            </label>
            <Textarea
              id="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Typ uw vraag hier..."
              className="min-h-[50px] max-h-[120px] resize-none border-2 border-gray-400 focus:border-[#154274] focus:ring-2 focus:ring-[#154274] bg-white text-black placeholder:text-gray-500"
              style={{ fontFamily: 'Verdana, sans-serif', fontSize: '14px' }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  if (input.trim() && !streaming && !uploading) {
                    sendMessage(input);
                    setInput('');
                  }
                }
              }}
              disabled={streaming || uploading}
            />
          </div>
          <Button
            type="submit"
            disabled={streaming || !input.trim() || uploading}
            className="h-[50px] px-6 bg-[#154274] hover:bg-[#0f3054] text-white border-0 font-bold disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-shrink-0"
            style={{ fontFamily: 'Verdana, sans-serif' }}
          >
            {uploading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin mr-2" />
                Uploaden...
              </>
            ) : streaming ? (
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
