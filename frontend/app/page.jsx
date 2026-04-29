'use client'

import { useState, useRef, useEffect } from 'react'
import { v4 as uuidv4 } from 'uuid'
import DocumentPanel from '@/components/DocumentPanel'
import ChatPanel from '@/components/ChatPanel'
import ViewerPanel from '@/components/ViewerPanel'
import { Toaster } from '@/components/ui/toaster'

export default function Home() {
  const [fileHash, setFileHash] = useState(null)
  const [sessionId] = useState(() => uuidv4())
  const [messages, setMessages] = useState([])
  const [images, setImages] = useState([])
  const [loading, setLoading] = useState(false)
  const [fileName, setFileName] = useState(null)
  const [processingStatus, setProcessingStatus] = useState('')
  const panelsRef = useRef(null)

  const handleUpload = async (file) => {
    setFileName(file.name)
    setProcessingStatus('Uploading and processing PDF...')
    setMessages([])
    setImages([])

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('http://localhost:8000/upload-pdf', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) throw new Error('Upload failed')

      const data = await response.json()
      setFileHash(data.file_hash)
      setProcessingStatus(`Processed: ${data.chunks || 0} chunks`)
    } catch (error) {
      console.error('Upload error:', error)
      setProcessingStatus('Upload failed. Try again.')
    }
  }

  const handleSendMessage = async (query) => {
    if (!fileHash || !query.trim()) return

    const userMessage = { role: 'user', content: query, id: Date.now() }
    setMessages((prev) => [...prev, userMessage])
    setLoading(true)

    try {
      const response = await fetch('http://localhost:8000/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          file_hash: fileHash,
          query,
        }),
      })

      if (!response.ok) throw new Error('Request failed')

      const data = await response.json()

      const assistantMessage = {
        role: 'assistant',
        content: data.answer,
        highlights: data.highlights || [],
        id: Date.now() + 1,
      }

      setMessages((prev) => [...prev, assistantMessage])

      if (data.images && Array.isArray(data.images)) {
        const processedImages = data.images.map((img) => ({
          page: img.page,
          types: img.types || [],
          image_path: `http://localhost:8000/${img.image_path}`,
        }))
        setImages(processedImages)
      }
    } catch (error) {
      console.error('Ask error:', error)
      const errorMessage = {
        role: 'assistant',
        content: 'Error processing your question. Please try again.',
        id: Date.now() + 1,
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-screen w-full flex flex-col bg-background text-foreground overflow-hidden">
      {/* Header */}
      <div className="border-b border-border h-14 flex items-center px-6 gap-3 bg-background/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
          <span className="text-white text-xs font-bold">AI</span>
        </div>
        <h1 className="text-sm font-semibold">PDF AI Assistant</h1>
        <span className="text-xs text-muted-foreground ml-auto">
          {fileHash ? '✓ Ready' : '○ Upload PDF'}
        </span>
      </div>

      {/* Main Content - 3 Panel Layout */}
      <div
        ref={panelsRef}
        className="flex-1 flex overflow-hidden"
      >
        {/* LEFT: Document Panel */}
        <DocumentPanel
          fileHash={fileHash}
          fileName={fileName}
          processingStatus={processingStatus}
          onUpload={handleUpload}
        />

        {/* CENTER: Chat Panel */}
        <ChatPanel
          messages={messages}
          loading={loading}
          fileHash={fileHash}
          onSendMessage={handleSendMessage}
        />

        {/* RIGHT: Viewer Panel */}
        <ViewerPanel images={images} />
      </div>

      <Toaster />
    </div>
  )
}
