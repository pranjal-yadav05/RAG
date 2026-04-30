"use client";

import { useState, useCallback } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

export function usePDFAssistant(token) {
  // files[]: { file_id, file_name, content_hash, created_at, sessions[] }
  const [files, setFiles] = useState([]);
  const [sessions, setSessions] = useState([]); // flat list for sidebar compat
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [activeFileId, setActiveFileId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fileName, setFileName] = useState(null);
  const [fileId, setFileId] = useState(null);       // replaces fileHash
  const [processingStatus, setProcessingStatus] = useState("");
  const [error, setError] = useState(null);
  const [sessionsLoading, setSessionsLoading] = useState(false);

  const authHeaders = useCallback(
    () => ({ Authorization: `Bearer ${token}` }),
    [token]
  );

  // ── Helpers ───────────────────────────────────────────────────────────────

  /** Build a full image URL from the relative image_url the API returns */
  const resolveImageUrl = (image_url) => {
    if (!image_url) return null;
    if (image_url.startsWith("http")) return image_url;
    return `${API_BASE_URL}${image_url}`;
  };

  /** Map a raw API message to local shape */
  const mapMessage = (m, idx, sessionId) => ({
    role: m.role,
    content: m.content,
    highlights: m.highlights || [],
    images: (m.images || []).map((img) => ({
      page: img.page,
      types: img.types || [],
      image_path: resolveImageUrl(img.image_url),
    })),
    id: m.id ?? `${sessionId}-${idx}`,
    created_at: m.created_at,
  });

  // ── Fetch all files (with their sessions nested) ──────────────────────────

  const fetchChatHistory = useCallback(async () => {
    if (!token) return;
    setSessionsLoading(true);
    try {
      // 1. Get all files
      const filesRes = await fetch(`${API_BASE_URL}/files`, {
        headers: authHeaders(),
      });
      if (!filesRes.ok) throw new Error("Failed to fetch files");
      const filesData = await filesRes.json();
      const fileList = Array.isArray(filesData) ? filesData : [];

      // 2. For each file, get its sessions (parallel)
      const filesWithSessions = await Promise.all(
        fileList.map(async (file) => {
          try {
            const sessRes = await fetch(
              `${API_BASE_URL}/files/${file.file_id}/sessions`,
              { headers: authHeaders() }
            );
            const sessData = sessRes.ok ? await sessRes.json() : [];
            return {
              ...file,
              sessions: Array.isArray(sessData) ? sessData : [],
            };
          } catch {
            return { ...file, sessions: [] };
          }
        })
      );

      setFiles(filesWithSessions);

      // Build flat sessions list (for sidebar / legacy consumers)
      // Attach file_name onto each session so the sidebar can display it
      const flat = filesWithSessions.flatMap((f) =>
        f.sessions.map((s) => ({ ...s, file_name: f.file_name }))
      );
      setSessions(flat);
    } catch (e) {
      console.error("fetchChatHistory error:", e);
    } finally {
      setSessionsLoading(false);
    }
  }, [token, authHeaders]);

  // Alias
  const fetchSessions = fetchChatHistory;

  // ── Load a session ────────────────────────────────────────────────────────

  const loadSession = useCallback(
    async (sessionId) => {
      if (!token) return;
      try {
        // FIXED: was /session/{id}, now /sessions/{id}
        const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
          headers: authHeaders(),
        });
        if (!res.ok) throw new Error("Failed to load session");
        const data = await res.json();

        setActiveSessionId(data.session_id);
        setActiveFileId(data.file_id || null);
        setImages([]);
        setError(null);

        // Resolve file_name from our files list or from the flat sessions list
        const matchedSession = sessions.find(
          (s) => s.session_id === data.session_id
        );
        const matchedFile = files.find((f) => f.file_id === data.file_id);
        const resolvedName =
          matchedSession?.file_name ||
          matchedFile?.file_name ||
          data.file_name ||
          null;

        setFileName(resolvedName);
        // Use file_id as the "ready" signal (replaces old fileHash)
        setFileId(data.file_id || null);

        const mapped = (data.messages || []).map((m, i) =>
          mapMessage(m, i, data.session_id)
        );
        setMessages(mapped);

        // Show images from the last assistant turn
        const lastAssistant = [...mapped]
          .reverse()
          .find((m) => m.role === "assistant");
        if (lastAssistant?.images?.length) {
          setImages(lastAssistant.images);
        }

        setProcessingStatus(data.file_id ? "Ready" : "");
      } catch (e) {
        console.error("Load session error:", e);
        setError(e.message);
      }
    },
    [token, authHeaders, sessions, files]
  );

  // ── Upload PDF → creates file + default session ───────────────────────────

  const handleUpload = useCallback(
    async (file) => {
      setFileName(file.name);
      setProcessingStatus("Uploading and processing PDF...");
      setMessages([]);
      setImages([]);
      setError(null);
      setActiveSessionId(null);
      setActiveFileId(null);
      setFileId(null);

      const formData = new FormData();
      formData.append("file", file);

      try {
        const res = await fetch(`${API_BASE_URL}/upload-pdf`, {
          method: "POST",
          headers: authHeaders(),
          body: formData,
        });
        if (!res.ok) throw new Error("Upload failed");
        const data = await res.json();

        // FIXED: API returns file_id (not file_hash) and session_id
        setActiveSessionId(data.session_id);
        setActiveFileId(data.file_id);
        setFileId(data.file_id);
        setProcessingStatus("Ready");

        // Refresh so sidebar shows the new file + session
        await fetchChatHistory();
      } catch (err) {
        setError(err.message);
        setProcessingStatus("Upload failed. Try again.");
        console.error("Upload error:", err);
      }
    },
    [authHeaders, fetchChatHistory]
  );

  // ── Ask ───────────────────────────────────────────────────────────────────

  const handleSendMessage = useCallback(
    async (query) => {
      if (!activeSessionId || !query.trim()) return;

      const userMessage = {
        role: "user",
        content: query,
        id: Date.now(),
        highlights: [],
        images: [],
      };
      setMessages((prev) => [...prev, userMessage]);
      setLoading(true);
      setError(null);

      try {
        // FIXED: was POST /ask with session_id in body
        //        now  POST /sessions/{session_id}/ask with { query }
        const res = await fetch(
          `${API_BASE_URL}/sessions/${activeSessionId}/ask`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...authHeaders(),
            },
            body: JSON.stringify({ query }),
          }
        );
        if (!res.ok) throw new Error("Request failed");
        const data = await res.json();

        // FIXED: images use image_url, not image_path
        const processedImages = (data.images || []).map((img) => ({
          page: img.page,
          types: img.types || [],
          image_path: resolveImageUrl(img.image_url),
        }));

        const assistantMessage = {
          role: "assistant",
          content: data.answer,
          highlights: data.highlights || [],
          images: processedImages,
          id: Date.now() + 1,
        };
        setMessages((prev) => [...prev, assistantMessage]);

        if (processedImages.length) {
          setImages(processedImages);
        }

        // Update sidebar preview without a full refetch
        setSessions((prev) =>
          prev.map((s) =>
            s.session_id === activeSessionId
              ? { ...s, updated_at: new Date().toISOString() }
              : s
          )
        );
      } catch (err) {
        setError(err.message);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `Error: ${err.message}. Please try again.`,
            id: Date.now() + 1,
            highlights: [],
            images: [],
          },
        ]);
        console.error("Ask error:", err);
      } finally {
        setLoading(false);
      }
    },
    [activeSessionId, authHeaders]
  );

  // ── Start a new session on an EXISTING file ───────────────────────────────

  const startNewSessionOnFile = useCallback(
    async (fId) => {
      if (!token || !fId) return;
      try {
        // FIXED: was just clearing local state; now actually creates a server session
        const res = await fetch(`${API_BASE_URL}/files/${fId}/sessions`, {
          method: "POST",
          headers: authHeaders(),
        });
        if (!res.ok) throw new Error("Failed to create session");
        const data = await res.json();

        setActiveSessionId(data.session_id);
        setActiveFileId(fId);
        setMessages([]);
        setImages([]);
        setError(null);
        setProcessingStatus("Ready");

        // Find file name from local state
        const matchedFile = files.find((f) => f.file_id === fId);
        setFileName(matchedFile?.file_name || null);
        setFileId(fId);

        // Refresh sidebar to include the new session
        await fetchChatHistory();
      } catch (err) {
        console.error("startNewSessionOnFile error:", err);
        setError(err.message);
      }
    },
    [token, authHeaders, files, fetchChatHistory]
  );

  // ── Delete a session ──────────────────────────────────────────────────────

  const deleteSession = useCallback(
    async (sessionId) => {
      if (!token) return;
      try {
        const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
          method: "DELETE",
          headers: authHeaders(),
        });
        if (!res.ok) throw new Error("Failed to delete session");

        // Remove from local state
        setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
        setFiles((prev) =>
          prev.map((f) => ({
            ...f,
            sessions: f.sessions.filter((s) => s.session_id !== sessionId),
          }))
        );

        // If this was the active session, clear it
        if (activeSessionId === sessionId) {
          setActiveSessionId(null);
          setActiveFileId(null);
          setMessages([]);
          setImages([]);
          setFileId(null);
          setFileName(null);
          setProcessingStatus("");
        }
      } catch (err) {
        console.error("deleteSession error:", err);
        setError(err.message);
      }
    },
    [token, authHeaders, activeSessionId]
  );

  // ── Delete a file (cascades to all sessions) ──────────────────────────────

  const deleteFile = useCallback(
    async (fId) => {
      if (!token) return;
      try {
        const res = await fetch(`${API_BASE_URL}/files/${fId}`, {
          method: "DELETE",
          headers: authHeaders(),
        });
        if (!res.ok) throw new Error("Failed to delete file");

        // Remove file and all its sessions from local state immediately
        const deletedFile = files.find((f) => f.file_id === fId);
        const deletedSessionIds = new Set(
          (deletedFile?.sessions || []).map((s) => s.session_id)
        );

        setFiles((prev) => prev.filter((f) => f.file_id !== fId));
        setSessions((prev) =>
          prev.filter((s) => !deletedSessionIds.has(s.session_id))
        );

        // If active session belonged to this file, clear everything
        if (activeFileId === fId) {
          setActiveSessionId(null);
          setActiveFileId(null);
          setMessages([]);
          setImages([]);
          setFileId(null);
          setFileName(null);
          setProcessingStatus("");
        }
      } catch (err) {
        console.error("deleteFile error:", err);
        setError(err.message);
      }
    },
    [token, authHeaders, files, activeFileId]
  );

  // ── Rename a session ──────────────────────────────────────────────────────

  const renameSession = useCallback(
    async (sessionId, title) => {
      if (!token) return;
      try {
        const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            ...authHeaders(),
          },
          body: JSON.stringify({ title }),
        });
        if (!res.ok) throw new Error("Failed to rename session");

        // Update local state
        setSessions((prev) =>
          prev.map((s) =>
            s.session_id === sessionId ? { ...s, title } : s
          )
        );
        setFiles((prev) =>
          prev.map((f) => ({
            ...f,
            sessions: f.sessions.map((s) =>
              s.session_id === sessionId ? { ...s, title } : s
            ),
          }))
        );
      } catch (err) {
        console.error("renameSession error:", err);
        setError(err.message);
      }
    },
    [token, authHeaders]
  );

  // ── Legacy: startNewSession (clears to upload state) ─────────────────────

  const startNewSession = useCallback(() => {
    setActiveSessionId(null);
    setActiveFileId(null);
    setMessages([]);
    setImages([]);
    setFileName(null);
    setFileId(null);
    setProcessingStatus("");
    setError(null);
  }, []);

  // ── Reset all ─────────────────────────────────────────────────────────────

  const resetAll = useCallback(() => {
    setActiveSessionId(null);
    setActiveFileId(null);
    setMessages([]);
    setImages([]);
    setLoading(false);
    setFileName(null);
    setFileId(null);
    setProcessingStatus("");
    setError(null);
    setSessions([]);
    setFiles([]);
  }, []);

  return {
    // data
    files,
    sessions,
    sessionsLoading,
    activeSessionId,
    activeFileId,
    fileId,          // replaces fileHash — truthy means a file is loaded & ready
    fileName,
    messages,
    images,
    loading,
    processingStatus,
    error,

    // actions
    fetchSessions,
    fetchChatHistory,
    loadSession,
    startNewSession,
    startNewSessionOnFile,
    deleteSession,
    deleteFile,
    renameSession,
    handleUpload,
    handleSendMessage,
    resetAll,

    // legacy compat
    fileHash: fileId,      // kept so existing consumers don't break immediately
    sessionId: activeSessionId,
  };
}