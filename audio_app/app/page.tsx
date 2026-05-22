"use client";

import { type ChangeEvent, useEffect, useMemo, useRef, useState } from "react";

const backendUrl =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8000";

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Home() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [status, setStatus] = useState("Siap kirim audio ke backend.");
  const [error, setError] = useState<string | null>(null);
  const [responseUrl, setResponseUrl] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const selectedFileSummary = useMemo(() => {
    if (!selectedFile) return "Belum ada file audio yang dipilih.";
    return `${selectedFile.name} · ${formatFileSize(selectedFile.size)}`;
  }, [selectedFile]);

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      if (responseUrl) {
        URL.revokeObjectURL(responseUrl);
      }
    };
  }, [responseUrl]);

  const resetMessage = () => {
    setError(null);
    setStatus("Siap kirim audio ke backend.");
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    resetMessage();
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
  };

  const startRecording = async () => {
    try {
      resetMessage();

      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("Browser ini tidak mendukung perekaman audio.");
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : MediaRecorder.isTypeSupported("audio/mp4")
          ? "audio/mp4"
          : "";

      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      streamRef.current = stream;
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const mime = recorder.mimeType || "audio/webm";
        const blob = new Blob(chunksRef.current, { type: mime });
        const extension = mime.includes("mp4") ? "mp4" : "webm";
        const file = new File([blob], `voice-chat.${extension}`, {
          type: mime,
        });
        setSelectedFile(file);
        setStatus("Rekaman selesai. Audio siap dikirim.");
        setIsRecording(false);
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
      setStatus("Merekam audio dari mikrofon...");
    } catch (recordError) {
      const message =
        recordError instanceof Error
          ? recordError.message
          : "Gagal memulai perekaman.";
      setError(message);
      setIsRecording(false);
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current = null;
  };

  const uploadVoice = async () => {
    try {
      resetMessage();

      if (!selectedFile) {
        throw new Error("Pilih atau rekam audio dulu sebelum mengirim.");
      }

      setIsSubmitting(true);
      setStatus("Mengirim audio ke /voice-chat...");

      const formData = new FormData();
      formData.append("file", selectedFile, selectedFile.name);

      const response = await fetch(`${backendUrl}/voice-chat`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let detail = `Request gagal dengan status ${response.status}.`;

        try {
          const payload = (await response.json()) as { detail?: string };
          if (payload.detail) {
            detail = payload.detail;
          }
        } catch {
          const text = await response.text();
          if (text) {
            detail = text;
          }
        }

        throw new Error(detail);
      }

      const audioBlob = await response.blob();
      const nextUrl = URL.createObjectURL(audioBlob);

      setResponseUrl((currentUrl) => {
        if (currentUrl) {
          URL.revokeObjectURL(currentUrl);
        }
        return nextUrl;
      });
      setStatus("Balasan audio diterima dan siap diputar.");

      if (audioRef.current) {
        audioRef.current.src = nextUrl;
        await audioRef.current.play().catch(() => undefined);
      }
    } catch (uploadError) {
      const message =
        uploadError instanceof Error
          ? uploadError.message
          : "Gagal mengirim audio.";
      setError(message);
      setStatus("Pengiriman gagal.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen overflow-hidden bg-[#0b1020] text-white">
      <div
        className="absolute inset-0"
        style={{
          backgroundImage:
            "radial-gradient(circle at top, rgba(120, 119, 198, 0.24), transparent 34%), radial-gradient(circle at bottom right, rgba(56, 189, 248, 0.18), transparent 28%), linear-gradient(180deg, #0b1020 0%, #060912 100%)",
        }}
      />
      <div className="absolute -left-40 top-24 h-72 w-72 rounded-full bg-cyan-500/20 blur-3xl" />
      <div className="absolute -right-32 top-40 h-80 w-80 rounded-full bg-violet-500/20 blur-3xl" />

      <div className="relative mx-auto flex min-h-screen w-full max-w-6xl items-center px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid w-full gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <section className="rounded-4xl border border-white/10 bg-white/6 p-6 shadow-2xl shadow-black/30 backdrop-blur-xl sm:p-8">
            <div className="mb-8 flex flex-wrap items-center gap-3 text-xs uppercase tracking-[0.3em] text-cyan-200/80">
              <span className="rounded-full border border-cyan-300/30 bg-cyan-300/10 px-3 py-1">
                Voice Chat Demo
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
                Next.js + FastAPI
              </span>
            </div>

            <div className="space-y-4">
              <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                Kirim audio ke backend lalu putar jawaban TTS-nya langsung di
                halaman ini.
              </h1>
              <p className="max-w-2xl text-base leading-7 text-slate-300 sm:text-lg">
                Halaman ini memanggil endpoint{" "}
                <span className="font-medium text-cyan-200">
                  POST {backendUrl}/voice-chat
                </span>{" "}
              </p>
            </div>

            <div className="mt-8 grid gap-4 sm:grid-cols-3">
              {[
                [
                  "1",
                  "Pilih atau rekam audio",
                  "Gunakan file lokal atau microphone browser.",
                ],
                [
                  "2",
                  "Kirim ke backend",
                  "FormData dikirim ke endpoint `/voice-chat`.",
                ],
                [
                  "3",
                  "Putar balasan",
                  "Audio jawaban tampil di player bawaan.",
                ],
              ].map(([step, title, description]) => (
                <div
                  key={step}
                  className="rounded-2xl border border-white/10 bg-slate-950/40 p-4"
                >
                  <div className="mb-3 text-sm font-medium text-cyan-200">
                    Langkah {step}
                  </div>
                  <div className="text-lg font-semibold text-white">
                    {title}
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-400">
                    {description}
                  </p>
                </div>
              ))}
            </div>

            <div className="mt-8 space-y-4 rounded-3xl border border-white/10 bg-slate-950/40 p-5">
              <label className="block text-sm font-medium text-slate-200">
                Audio file
              </label>
              <input
                type="file"
                accept="audio/*"
                onChange={handleFileChange}
                className="block w-full rounded-2xl border border-dashed border-white/15 bg-white/5 px-4 py-4 text-sm text-slate-300 file:mr-4 file:rounded-xl file:border-0 file:bg-cyan-300 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-slate-950 hover:border-cyan-300/40 hover:bg-white/8"
              />
              <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-slate-300">
                {selectedFileSummary}
              </div>

              <div className="flex flex-col gap-3 sm:flex-row">
                {!isRecording ? (
                  <button
                    type="button"
                    onClick={startRecording}
                    className="inline-flex items-center justify-center rounded-2xl bg-cyan-300 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200"
                  >
                    Rekam dari mikrofon
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={stopRecording}
                    className="inline-flex items-center justify-center rounded-2xl bg-rose-400 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-rose-300"
                  >
                    Hentikan rekaman
                  </button>
                )}

                <button
                  type="button"
                  onClick={uploadVoice}
                  disabled={isSubmitting}
                  className="inline-flex items-center justify-center rounded-2xl border border-cyan-300/30 bg-white/10 px-5 py-3 text-sm font-semibold text-white transition hover:border-cyan-200 hover:bg-white/15 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isSubmitting ? "Mengirim..." : "Kirim ke voice-chat"}
                </button>
              </div>

              <div className="flex items-center gap-3 text-sm text-slate-300">
                <span
                  className={`h-2.5 w-2.5 rounded-full ${isRecording ? "bg-rose-400" : "bg-emerald-400"}`}
                />
                <span>{status}</span>
              </div>

              {error ? (
                <div className="rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
                  {error}
                </div>
              ) : null}
            </div>
          </section>

          <aside className="flex flex-col gap-6">
            <section className="rounded-4xl border border-white/10 bg-white/6 p-6 shadow-2xl shadow-black/30 backdrop-blur-xl sm:p-8">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
                    Response
                  </p>
                  <h2 className="mt-2 text-2xl font-semibold text-white">
                    Balasan audio
                  </h2>
                </div>
                <div className="h-12 w-12 rounded-2xl bg-linear-to-br from-cyan-300 via-sky-400 to-violet-400 shadow-lg shadow-cyan-500/20" />
              </div>

              <div className="mt-6 rounded-3xl border border-dashed border-white/15 bg-slate-950/40 p-4">
                {responseUrl ? (
                  <audio ref={audioRef} controls className="w-full rounded-xl">
                    <source src={responseUrl} type="audio/wav" />
                    Browser kamu tidak mendukung elemen audio.
                  </audio>
                ) : (
                  <div className="flex min-h-40 items-center justify-center rounded-[1.25rem] bg-white/5 px-6 text-center text-sm leading-6 text-slate-400">
                    Hasil dari endpoint akan muncul di sini sebagai audio
                    player.
                  </div>
                )}
              </div>

              <div className="mt-5 grid grid-cols-2 gap-3 text-sm text-slate-300">
                <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                  File: {selectedFile ? selectedFile.name : "-"}
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                  State:{" "}
                  {isRecording
                    ? "Recording"
                    : isSubmitting
                      ? "Sending"
                      : "Idle"}
                </div>
              </div>
            </section>
          </aside>
        </div>
      </div>
    </main>
  );
}
