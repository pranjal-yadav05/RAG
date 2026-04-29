'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function ChatPanel({
  messages,
  loading,
  fileHash,
  onSendMessage,
}) {
  const [inputValue, setInputValue] = useState('')
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = () => {
    if (inputValue.trim() && fileHash && !loading) {
      onSendMessage(inputValue)
      setInputValue('')
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && fileHash && !loading) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex-1 flex flex-col bg-background border-r border-border overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border/50">
        <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Chat
        </h2>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center px-6 text-center">
            <div className="w-12 h-12 rounded-lg bg-muted/50 flex items-center justify-center mb-4">
              <svg
                className="w-6 h-6 text-muted-foreground"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M12 8v4m0 4v.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <p className="text-sm font-medium text-foreground">
              {fileHash ? 'Start asking questions' : 'Upload a PDF to get started'}
            </p>
            <p className="text-xs text-muted-foreground mt-1 max-w-xs">
              Ask anything about your document and get instant answers with visual evidence
            </p>
          </div>
        ) : (
          <div className="p-6 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                } animate-in fade-in slide-in-from-bottom-2 duration-300`}
              >
                <div
                  className={`max-w-sm rounded-lg px-4 py-3 ${
                    message.role === 'user'
                      ? 'bg-primary text-primary-foreground rounded-br-none'
                      : 'bg-card border border-border rounded-bl-none'
                  }`}
                >
                  <p className="text-sm leading-relaxed">{message.content}</p>
                  {message.highlights && message.highlights.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-border/30">
                      <p className="text-xs font-medium mb-1 opacity-75">Highlights:</p>
                      <div className="flex flex-wrap gap-1">
                        {message.highlights.map((h, i) => (
                          <span
                            key={i}
                            className="inline-block text-xs bg-primary/20 px-2 py-1 rounded"
                          >
                            {h.text}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start animate-in fade-in">
                <div className="bg-card border border-border rounded-lg rounded-bl-none px-4 py-3">
                  <div className="flex gap-2 items-center">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 rounded-full bg-muted-foreground/60 animate-bounce" />
                      <div
                        className="w-2 h-2 rounded-full bg-muted-foreground/60 animate-bounce"
                        style={{ animationDelay: '0.1s' }}
                      />
                      <div
                        className="w-2 h-2 rounded-full bg-muted-foreground/60 animate-bounce"
                        style={{ animationDelay: '0.2s' }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-border/50 p-4 bg-background/50 backdrop-blur-sm">
        {!fileHash && (
          <p className="text-xs text-muted-foreground text-center mb-3">
            Upload a PDF to start chatting
          </p>
        )}
        <div className="flex gap-2">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              fileHash ? 'Ask a question...' : 'Upload a PDF first'
            }
            disabled={!fileHash || loading}
            className="flex-1 min-h-10 px-3 py-2 rounded-lg border border-input bg-background text-sm placeholder:text-muted-foreground disabled:opacity-50 disabled:cursor-not-allowed resize-none focus:outline-none focus:ring-2 focus:ring-primary/20"
            rows="1"
          />
          <Button
            onClick={handleSend}
            disabled={!fileHash || loading || !inputValue.trim()}
            size="sm"
            className="px-3 h-10 flex-shrink-0"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
