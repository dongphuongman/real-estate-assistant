"use client";

import { useState } from "react";
import { FileUp, Loader2, MessageSquareText } from "lucide-react";
import { ragQa, uploadRagDocuments } from "@/lib/api";
import type { RagQaResponse, RagUploadResponse } from "@/lib/types";

export default function KnowledgePage() {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadResult, setUploadResult] = useState<RagUploadResponse | null>(null);

  const [question, setQuestion] = useState<string>("");
  const [topK, setTopK] = useState<string>("5");
  const [provider, setProvider] = useState<string>("");
  const [model, setModel] = useState<string>("");
  const [asking, setAsking] = useState(false);
  const [qaError, setQaError] = useState<string | null>(null);
  const [qaResult, setQaResult] = useState<RagQaResponse | null>(null);

  const parseTopK = (): number => {
    const raw = topK.trim();
    if (!raw) return 5;
    const n = Number(raw);
    if (!Number.isFinite(n)) return 5;
    const asInt = Math.floor(n);
    if (asInt < 1) return 1;
    if (asInt > 50) return 50;
    return asInt;
  };

  const onUpload = async () => {
    setUploadError(null);
    setUploadResult(null);
    if (!files.length) {
      setUploadError("Select at least one file to upload.");
      return;
    }
    setUploading(true);
    try {
      const res = await uploadRagDocuments(files);
      setUploadResult(res);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setUploadError(msg || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const onAsk = async () => {
    setQaError(null);
    setQaResult(null);
    const q = question.trim();
    if (!q) {
      setQaError("Enter a question.");
      return;
    }
    setAsking(true);
    try {
      const res = await ragQa({
        question: q,
        top_k: parseTopK(),
        provider: provider.trim() || undefined,
        model: model.trim() || undefined,
      });
      setQaResult(res);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setQaError(msg || "QA failed");
    } finally {
      setAsking(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-10">
      <h1 className="text-3xl font-bold mb-2">Knowledge</h1>
      <p className="text-muted-foreground mb-8">
        Upload documents to your local knowledge base and ask questions with citations.
      </p>

      <section className="border rounded-lg p-6 mb-8">
        <div className="flex items-center gap-2 mb-4">
          <FileUp className="w-5 h-5" />
          <h2 className="text-xl font-semibold">Upload</h2>
        </div>

        <input
          className="border p-2 w-full"
          type="file"
          multiple
          accept=".txt,.md,.pdf,.docx"
          onChange={(e) => {
            const list = e.target.files ? Array.from(e.target.files) : [];
            setFiles(list);
          }}
          aria-label="Knowledge files"
        />

        {files.length ? (
          <ul className="text-sm text-muted-foreground mt-2 list-disc pl-5">
            {files.map((f) => (
              <li key={`${f.name}-${f.size}`}>{f.name}</li>
            ))}
          </ul>
        ) : null}

        <div className="mt-4 flex items-center gap-3">
          <button
            className="bg-black text-white px-3 py-2 rounded disabled:opacity-50"
            disabled={uploading}
            onClick={onUpload}
          >
            {uploading ? (
              <span className="inline-flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Uploading...
              </span>
            ) : (
              "Upload"
            )}
          </button>
          <button
            className="border px-3 py-2 rounded disabled:opacity-50"
            disabled={uploading || !files.length}
            onClick={() => {
              setFiles([]);
              setUploadError(null);
              setUploadResult(null);
            }}
          >
            Clear
          </button>
        </div>

        {uploadError && <p className="text-red-600 mt-3">{uploadError}</p>}
        {uploadResult ? (
          <div className="mt-4">
            <p className="font-medium">{uploadResult.message}</p>
            <p className="text-sm text-muted-foreground">Chunks indexed: {uploadResult.chunks_indexed}</p>
            {uploadResult.errors.length ? (
              <ul className="mt-2 text-sm text-red-600 list-disc pl-5">
                {uploadResult.errors.map((err, idx) => (
                  <li key={idx}>{err}</li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
      </section>

      <section className="border rounded-lg p-6">
        <div className="flex items-center gap-2 mb-4">
          <MessageSquareText className="w-5 h-5" />
          <h2 className="text-xl font-semibold">Ask</h2>
        </div>

        <textarea
          className="border p-2 w-full"
          placeholder="Ask a question about your uploaded documents..."
          rows={4}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          aria-label="Knowledge question"
        />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3">
          <input
            className="border p-2 w-full"
            type="number"
            min={1}
            max={50}
            value={topK}
            onChange={(e) => setTopK(e.target.value)}
            aria-label="Top K"
            placeholder="Top K (1-50)"
          />
          <input
            className="border p-2 w-full"
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            aria-label="Provider override"
            placeholder="Provider (optional)"
          />
          <input
            className="border p-2 w-full"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            aria-label="Model override"
            placeholder="Model (optional)"
          />
        </div>

        <div className="mt-4 flex items-center gap-3">
          <button
            className="bg-black text-white px-3 py-2 rounded disabled:opacity-50"
            disabled={asking}
            onClick={onAsk}
          >
            {asking ? (
              <span className="inline-flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Asking...
              </span>
            ) : (
              "Ask"
            )}
          </button>
          <button
            className="border px-3 py-2 rounded disabled:opacity-50"
            disabled={asking || (!question.trim() && !qaResult && !qaError)}
            onClick={() => {
              setQuestion("");
              setQaError(null);
              setQaResult(null);
            }}
          >
            Clear
          </button>
        </div>

        {qaError && <p className="text-red-600 mt-3">{qaError}</p>}

        {qaResult ? (
          <div className="mt-4">
            <div className="border rounded p-4 bg-muted/30">
              <p className="text-sm text-muted-foreground mb-2">
                llm_used={String(qaResult.llm_used)} provider={qaResult.provider ?? "null"} model={qaResult.model ?? "null"}
              </p>
              <p className="whitespace-pre-wrap">{qaResult.answer}</p>
            </div>

            <h3 className="font-semibold mt-4">Citations</h3>
            {qaResult.citations.length ? (
              <ul className="text-sm text-muted-foreground mt-2 list-disc pl-5">
                {qaResult.citations.map((c, idx) => (
                  <li key={`${c.source}-${c.chunk_index}-${idx}`}>
                    {c.source} (chunk {c.chunk_index})
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground mt-2">No citations returned.</p>
            )}
          </div>
        ) : null}
      </section>
    </div>
  );
}

