/**
 * API client utilities for PDF AI Assistant backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL

/**
 * Upload a PDF file to the backend
 * @param {File} file - The PDF file to upload
 * @returns {Promise<{file_hash: string, message: string, chunks: number}>}
 */
export async function uploadPDF(file) {
  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await fetch(`${API_BASE_URL}/upload-pdf`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.message || `Upload failed with status ${response.status}`)
    }

    return await response.json()
  } catch (error) {
    console.error('Upload error:', error)
    throw error
  }
}

/**
 * Ask a question about the uploaded PDF
 * @param {string} sessionId - Unique session identifier
 * @param {string} fileHash - Hash of the uploaded PDF
 * @param {string} query - The question to ask
 * @returns {Promise<{answer: string, highlights: string[], images: Array}>}
 */
export async function askQuestion(sessionId, fileHash, query) {
  try {
    const response = await fetch(`${API_BASE_URL}/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        file_hash: fileHash,
        query,
      }),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.message || `Request failed with status ${response.status}`)
    }

    return await response.json()
  } catch (error) {
    console.error('Ask error:', error)
    throw error
  }
}

/**
 * Format file size for display
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted file size
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

/**
 * Get image URL with fallback
 * @param {string} imagePath - Path to the image
 * @returns {string} Full image URL
 */
export function getImageUrl(imagePath) {
  if (!imagePath) return null
  if (imagePath.startsWith('http')) return imagePath
  return `${API_BASE_URL}/${imagePath}`
}

// Returns true if backend still has the file, false otherwise
export async function checkFileExists(fileHash) {
  const res = await fetch(`${API_BASE_URL}/check-file/${fileHash}`)
  if (res.status === 404) return false
  if (!res.ok) throw new Error('File check failed')
  const data = await res.json()
  return data.exists ?? true
}