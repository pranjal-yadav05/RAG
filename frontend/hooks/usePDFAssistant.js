/**
 * Custom hook for managing PDF Assistant state and logic
 */

import { useState, useCallback } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { uploadPDF, askQuestion } from '@/lib/api'

export function usePDFAssistant() {
  const [fileHash, setFileHash] = useState(null)
  const [sessionId] = useState(() => uuidv4())
  const [messages, setMessages] = useState([])
  const [images, setImages] = useState([])
  const [loading, setLoading] = useState(false)
  const [fileName, setFileName] = useState(null)
  const [processingStatus, setProcessingStatus] = useState('')
  const [error, setError] = useState(null)

  const handleUpload = useCallback(async (file) => {
    setFileName(file.name)
    setProcessingStatus('Uploading and processing PDF...')
    setMessages([])
    setImages([])
    setError(null)

    try {
      const data = await uploadPDF(file)
      setFileHash(data.file_hash)
      setProcessingStatus(`Processed: ${data.chunks || 0} chunks`)
    } catch (err) {
      setError(err.message)
      setProcessingStatus('Upload failed. Try again.')
      console.error('Upload error:', err)
    }
  }, [])

  const handleSendMessage = useCallback(
    async (query) => {
      if (!fileHash || !query.trim()) return

      const userMessage = {
        role: 'user',
        content: query,
        id: Date.now(),
      }
      setMessages((prev) => [...prev, userMessage])
      setLoading(true)
      setError(null)

      try {
        const data = await askQuestion(sessionId, fileHash, query)

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
            image_path: img.image_path.startsWith('http')
              ? img.image_path
              : `http://localhost:8000/${img.image_path}`,
          }))
          setImages(processedImages)
        }
      } catch (err) {
        setError(err.message)
        const errorMessage = {
          role: 'assistant',
          content: `Error: ${err.message}. Please try again.`,
          id: Date.now() + 1,
        }
        setMessages((prev) => [...prev, errorMessage])
        console.error('Ask error:', err)
      } finally {
        setLoading(false)
      }
    },
    [fileHash, sessionId]
  )

  const clearChat = useCallback(() => {
    setMessages([])
    setImages([])
    setError(null)
  }, [])

  const resetAll = useCallback(() => {
    setFileHash(null)
    setMessages([])
    setImages([])
    setLoading(false)
    setFileName(null)
    setProcessingStatus('')
    setError(null)
  }, [])

  return {
    fileHash,
    sessionId,
    messages,
    images,
    loading,
    fileName,
    processingStatus,
    error,
    handleUpload,
    handleSendMessage,
    clearChat,
    resetAll,
  }
}
