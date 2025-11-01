'use client';

import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Loader2, Globe } from 'lucide-react';
import { useRef, useEffect, useState } from 'react';
import { CitationList, type Citation } from '@/components/citations/citation-list';
import { createHighlightUrl } from '@/components/citations/citation-highlighter';
import type { FileWithMetadata } from './files-panel';

interface ChatContentProps {
  onClose: () => void;
  onFilesChange: (files: FileWithMetadata[]) => void;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
}

export function ChatContent({ onClose, onFilesChange }: ChatContentProps) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [uploadedFiles, setUploadedFiles] = useState<FileWithMetadata[]>([]);
  const [uploading, setUploading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [researchMode, setResearchMode] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const messageIdCounter = useRef<number>(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    onFilesChange(uploadedFiles);
  }, [uploadedFiles, onFilesChange]);

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
      alert('Only PDF, TXT, DOC, DOCX and MD files are allowed.');
      return;
    }

    if (validFiles.length > 0) {
      setUploading(true);
      try {
        const fileData: FileWithMetadata[] = validFiles.map(file => ({
          file,
          uploadedAt: new Date()
        }));
        
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
        setUploadedFiles(prev => [...prev, ...fileData]);
      } catch (error) {
        console.error('Upload error:', error);
        alert('An error occurred while uploading files. Please try again.');
      } finally {
        setUploading(false);
      }
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
      // If research mode is enabled, try research endpoint
      // URLs will be automatically selected by the backend based on the query
      if (researchMode) {
        try {
          const response = await fetch('/api/research', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              query: content,
              // URLs not needed - backend will automatically select relevant government sources
              max_results: 5,
            }),
          });

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: response.statusText }));
            throw new Error(errorData.error || `Failed to get research response (${response.status})`);
          } else {
            const data = await response.json();
            messageIdCounter.current += 1;
            const assistantMessage: Message = {
              id: `assistant-${messageIdCounter.current}`,
              role: 'assistant',
              content: data.answer || 'No answer received.',
              citations: data.citations || [],
            };
            setMessages(prev => [...prev, assistantMessage]);
            setStreaming(false);
            return;
          }
        } catch (error) {
          // If research fails, fall back to regular chat
          console.log('Research mode failed, falling back to regular chat:', error);
        }
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
      let assistantMessage: Message = {
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
              if (!hasReceivedContent && !errorOccurred) {
                assistantMessage.content = 'No answer received. Please check your connection or try again.';
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
              
              if (json.type === 'error') {
                errorOccurred = true;
                assistantMessage.content = `Error: ${json.error || 'An error occurred'}`;
                setMessages(prev => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1] = { ...assistantMessage };
                  return newMessages;
                });
                break;
              }
              
              if (json.type === 'text' && json.text) {
                hasReceivedContent = true;
                assistantMessage.content += json.text;
                setMessages(prev => {
                  const newMessages = [...prev];
                  newMessages[newMessages.length - 1] = { ...assistantMessage };
                  return newMessages;
                });
              }
              
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

      if (!hasReceivedContent && !errorOccurred && assistantMessage.content === '') {
        assistantMessage.content = 'No answer received from server.';
        setMessages(prev => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1] = { ...assistantMessage };
          return newMessages;
        });
      }
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage = error instanceof Error ? error.message : 'An error occurred. Please try again.';
      alert(errorMessage);
      
      messageIdCounter.current += 1;
      const errorMsg: Message = {
        id: `error-${messageIdCounter.current}`,
        role: 'assistant',
        content: `Error: ${errorMessage}`,
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setStreaming(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Chat</h2>
        <Button
          variant="ghost"
          size="sm"
          onClick={onClose}
          className="text-gray-600 hover:text-gray-900"
        >
          Close
        </Button>
      </div>

      {/* Messages Area */}
      <div 
        className="flex-1 overflow-y-auto px-6 py-6"
        ref={scrollRef}
      >
        <div className="space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Start a conversation
              </h3>
              <p className="text-sm text-gray-600 max-w-md">
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
              <div
                className={`max-w-[80%] px-4 py-3 rounded-2xl ${
                  message.role === 'user'
                    ? 'bg-gray-900 text-white rounded-br-sm'
                    : 'bg-gray-100 text-gray-900 rounded-bl-sm'
                }`}
              >
                <p className="text-sm leading-relaxed whitespace-pre-wrap">
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
            </div>
          ))}

          {streaming && (
            <div className="flex gap-4 justify-start">
              <div className="px-4 py-3 bg-gray-100 rounded-2xl rounded-bl-sm">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-gray-600" />
                  <span className="text-sm text-gray-600">Processing...</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-gray-200 bg-white">
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.txt,.doc,.docx,.md"
          onChange={handleFileSelect}
          className="hidden"
        />

        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            {/* Upload Files Button */}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={openFileDialog}
              disabled={streaming || uploading}
              className="h-8 px-3 rounded-lg border border-gray-300 hover:bg-gray-50"
            >
              {uploading ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin mr-2" />
                  Uploading...
                </>
              ) : (
                'Upload Files'
              )}
            </Button>

            {/* Web Search Toggle */}
            <Button
              type="button"
              variant={researchMode ? "default" : "outline"}
              size="sm"
              onClick={() => setResearchMode(!researchMode)}
              disabled={streaming || uploading}
              className={`flex items-center gap-2 h-8 px-3 rounded-lg ${
                researchMode 
                  ? 'bg-gray-900 text-white hover:bg-gray-800' 
                  : 'border border-gray-300 hover:bg-gray-50'
              }`}
            >
              <Globe className="h-3.5 w-3.5" />
              <span className="text-xs font-medium">Web</span>
            </Button>
          </div>
          
          {uploadedFiles.length > 0 && (
            <span className="text-xs text-gray-500">
              {uploadedFiles.length} file{uploadedFiles.length > 1 ? 's' : ''}
            </span>
          )}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (input.trim() && !streaming && !uploading) {
              sendMessage(input);
              setInput('');
            }
          }}
          className="flex gap-3 items-end"
        >
          <div className="flex-1">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
              className="min-h-[60px] max-h-[120px] resize-none border-gray-300 focus:border-gray-900 rounded-xl"
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
            className="bg-gray-900 text-white hover:bg-gray-800 px-6 rounded-xl h-[60px]"
          >
            {streaming ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              'Send'
            )}
          </Button>
        </form>
      </div>
    </div>
  );
}

