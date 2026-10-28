"use client";

import { Camera, Loader2, Upload } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ProgressRing } from "@/components/ProgressRing";
import { RecognitionPanel } from "@/components/RecognitionPanel";
import { StoryModal } from "@/components/StoryModal";
import { useStoryAudio } from "@/components/useStoryAudio";
import { positionedCheckpoints, referenceSources } from "@/lib/checkpoints";
import { MAX_UPLOAD_BYTES } from "@/lib/scan-limits";
import { addLocalDiscovery, DISCOVERIES_EVENT, DISCOVERIES_STORAGE_KEY, discoveriesFromRaw } from "@/lib/discoveries";
import { formatDistance, haversineDistanceMeters, watchPosition } from "@/lib/geo";
import { useBrowserStorage } from "@/lib/use-browser-storage";
import type { Checkpoint, DiscoveryMethod, Site } from "@/types";

interface LensViewProps {
  site: Site;
}

interface NearbyCheckpoint extends Checkpoint {
  distance: number;
}

type LensMode = "camera" | "upload";

type ScanKind = "invalid" | "no_match" | "unavailable" | "error";

type Recognition =
  | { status: "match"; checkpoint: Checkpoint }
  | { status: "miss"; kind: ScanKind; message: string };

const MISS_HEADING: Record<ScanKind, string> = {
  invalid: "This photograph could not be used",
  no_match: "No reliable match found",
  unavailable: "Scanning is not available yet",
  error: "The scan did not finish",
};

function cameraFailureMessage(error: unknown): string {
  const name = error instanceof DOMException ? error.name : "";
  if (name === "NotAllowedError" || name === "PermissionDeniedError") {
    return "Camera access was blocked. You can choose a photograph from this phone instead.";
  }
  if (name === "NotFoundError" || name === "DevicesNotFoundError") {
    return "No camera was found. You can choose a photograph from this phone instead.";
  }
  if (name === "NotReadableError" || name === "TrackStartError") {
    return "The camera is busy in another app. You can choose a photograph instead.";
  }
  if (name === "SecurityError") {
    return "This browser will not open the camera on this page. You can choose a photograph instead.";
  }
  return "The camera is unavailable. You can choose a photograph from this phone instead.";
}

function scanKind(code: string | undefined, ok: boolean): ScanKind {
  if (code === "invalid_image") return "invalid";
  if (code === "unavailable") return "unavailable";
  if (code === "no_match") return "no_match";
  if (!ok || code === "error" || code === "not_found") return "error";
  return "no_match";
}

export function LensView({ site }: LensViewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadPreviewRef = useRef<string | null>(null);
  const announcedRef = useRef<Set<string>>(new Set());
  const streamRef = useRef<MediaStream | null>(null);

  const [lensMode, setLensMode] = useState<LensMode>("camera");
  const [cameraAttempt, setCameraAttempt] = useState(0);
  const lensModeRef = useRef<LensMode>("camera");
  const [uploadPreview, setUploadPreview] = useState<string | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [position, setPosition] = useState<{ latitude: number; longitude: number } | null>(null);
  const discoveriesRaw = useBrowserStorage(DISCOVERIES_STORAGE_KEY, DISCOVERIES_EVENT);
  const [activePopup, setActivePopup] = useState<Checkpoint | null>(null);
  const [storyCheckpoint, setStoryCheckpoint] = useState<Checkpoint | null>(null);
  const [scanning, setScanning] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [recognition, setRecognition] = useState<Recognition | null>(null);

  useEffect(() => {
    lensModeRef.current = lensMode;
  }, [lensMode]);

  const spokenText =
    recognition?.status === "match"
      ? `${recognition.checkpoint.name}. ${recognition.checkpoint.story}`
      : "";
  const audio = useStoryAudio(spokenText);
  const discoveredIds = useMemo(() => {
    const entries = discoveriesFromRaw(discoveriesRaw)[site.slug] ?? [];
    return new Set(entries.map((item) => item.checkpointId));
  }, [discoveriesRaw, site.slug]);
  const nearby = useMemo(() => {
    if (!position) return [] as NearbyCheckpoint[];
    return positionedCheckpoints(site.checkpoints)
      .map((checkpoint) => ({
        ...checkpoint,
        distance: haversineDistanceMeters(
          position.latitude,
          position.longitude,
          checkpoint.latitude,
          checkpoint.longitude,
        ),
      }))
      .filter((checkpoint) => checkpoint.distance <= Math.max(checkpoint.radiusMeters * 3, 120))
      .sort((a, b) => a.distance - b.distance);
  }, [position, site.checkpoints]);

  const markDiscovered = useCallback(
    (checkpoint: Checkpoint, method: DiscoveryMethod) => {
      addLocalDiscovery(site.slug, checkpoint.id, method);
    },
    [site.slug],
  );

  useEffect(() => {
    return watchPosition(
      (pos) => {
        setGeoError(null);
        const nextPosition = { latitude: pos.latitude, longitude: pos.longitude };
        setPosition(nextPosition);
        const closestInRange = positionedCheckpoints(site.checkpoints)
          .map((checkpoint) => ({
            checkpoint,
            distance: haversineDistanceMeters(
              nextPosition.latitude,
              nextPosition.longitude,
              checkpoint.latitude,
              checkpoint.longitude,
            ),
          }))
          .filter((item) => item.distance <= item.checkpoint.radiusMeters)
          .sort((a, b) => a.distance - b.distance)[0];

        if (closestInRange && !announcedRef.current.has(closestInRange.checkpoint.id)) {
          announcedRef.current.add(closestInRange.checkpoint.id);
          setActivePopup(closestInRange.checkpoint);
          markDiscovered(closestInRange.checkpoint, "gps");
        }
      },
      (message) => setGeoError(message),
    );
  }, [markDiscovered, site.checkpoints]);

  useEffect(() => {
    let cancelled = false;

    function stopCamera() {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      if (videoRef.current) videoRef.current.srcObject = null;
      setCameraReady(false);
    }

    async function startCamera() {
      if (!navigator.mediaDevices?.getUserMedia) {
        setCameraError("This browser cannot open a camera. Choose a photograph instead.");
        setLensMode("upload");
        setCameraReady(false);
        return;
      }

      try {
        let stream: MediaStream;
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            audio: false,
            video: { facingMode: { ideal: "environment" } },
          });
        } catch (error) {
          const name = error instanceof DOMException ? error.name : "";
          if (cancelled || name === "NotAllowedError" || name === "SecurityError") throw error;
          stream = await navigator.mediaDevices.getUserMedia({ audio: false, video: true });
        }
        if (cancelled || document.visibilityState === "hidden") {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        stopCamera();
        streamRef.current = stream;
        const video = videoRef.current;
        if (video) {
          video.srcObject = stream;
          await video.play();
        }
        setCameraReady(true);
        setCameraError(null);
      } catch (error) {
        if (cancelled) return;
        stopCamera();
        setCameraError(cameraFailureMessage(error));
        setLensMode("upload");
      }
    }

    function onVisibility() {
      if (document.visibilityState === "hidden") {
        stopCamera();
        return;
      }
      if (lensModeRef.current === "camera") void startCamera();
    }

    void startCamera();
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("pagehide", stopCamera);

    return () => {
      cancelled = true;
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("pagehide", stopCamera);
      stopCamera();
    };
  }, [cameraAttempt]);

  useEffect(() => {
    const stream = streamRef.current;
    if (!stream) return;
    const showCamera = lensMode === "camera";
    stream.getTracks().forEach((track) => {
      track.enabled = showCamera;
    });
    if (showCamera && videoRef.current && videoRef.current.srcObject !== stream) {
      videoRef.current.srcObject = stream;
      void videoRef.current.play();
    }
  }, [lensMode]);

  useEffect(() => {
    return () => {
      if (uploadPreviewRef.current) URL.revokeObjectURL(uploadPreviewRef.current);
    };
  }, []);

  async function submitScan(blob: Blob) {
    setScanning(true);
    setRecognition(null);
    audio.stop();

    const formData = new FormData();
    formData.append("image", blob, "scan.jpg");
    formData.append("siteSlug", site.slug);

    try {
      const response = await fetch("/api/match", { method: "POST", body: formData });
      let result: { match?: Checkpoint; message?: string; code?: string } = {};
      try {
        result = (await response.json()) as { match?: Checkpoint; message?: string; code?: string };
      } catch {
        setRecognition({
          status: "miss",
          kind: "error",
          message: "The scan could not be read. Try the photograph again.",
        });
        return;
      }

      const claimedId = result.code === "no_match" ? undefined : result.match?.id;
      const known = claimedId
        ? site.checkpoints.find((checkpoint) => checkpoint.id === claimedId)
        : undefined;

      if (response.ok && known && result.code !== "no_match") {
        setRecognition({ status: "match", checkpoint: known });
        markDiscovered(known, "photo_match");
      } else {
        const kind = scanKind(result.code, response.ok);
        setRecognition({
          status: "miss",
          kind,
          message:
            result.message ??
            (kind === "error"
              ? "The photograph could not be compared. Try again."
              : "No reliable match found. Try a clearer photograph of one place, or choose it from the list."),
        });
      }
    } catch {
      setRecognition({
        status: "miss",
        kind: "error",
        message: "The photograph could not be compared. Check your connection and try again.",
      });
    } finally {
      setScanning(false);
    }
  }

  async function handleCameraScan() {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) return;
    context.drawImage(video, 0, 0);
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.85),
    );
    if (!blob) {
      setRecognition({ status: "miss", kind: "invalid", message: "Could not capture the frame. Try again." });
      return;
    }
    await submitScan(blob);
  }

  async function handleUploadedScan() {
    if (uploadedFile) {
      await submitScan(uploadedFile);
      return;
    }
    if (!uploadPreview || !canvasRef.current) {
      setRecognition({ status: "miss", kind: "invalid", message: "Upload a photograph first, then scan it." });
      return;
    }

    const image = new window.Image();
    image.src = uploadPreview;
    try {
      await new Promise<void>((resolve, reject) => {
        image.onload = () => resolve();
        image.onerror = () => reject(new Error("Failed to load image"));
      });
    } catch {
      setRecognition({ status: "miss", kind: "invalid", message: "Could not read the uploaded photograph." });
      return;
    }

    const canvas = canvasRef.current;
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    const context = canvas.getContext("2d");
    if (!context) return;
    context.drawImage(image, 0, 0);
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.85),
    );
    if (!blob) {
      setRecognition({ status: "miss", kind: "invalid", message: "Could not read the uploaded photograph." });
      return;
    }
    await submitScan(blob);
  }

  function handleScan() {
    if (lensMode === "camera" && cameraReady) void handleCameraScan();
    else void handleUploadedScan();
  }

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.size === 0) {
      setRecognition({ status: "miss", kind: "invalid", message: "The uploaded file is empty." });
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setRecognition({
        status: "miss",
        kind: "invalid",
        message: "That photograph is too large. Use an image under 8 MB.",
      });
      return;
    }
    if (!file.type.startsWith("image/")) {
      setRecognition({
        status: "miss",
        kind: "invalid",
        message: "That file is not a photograph. Use a JPG, PNG, or WebP image.",
      });
      return;
    }
    if (uploadPreviewRef.current) URL.revokeObjectURL(uploadPreviewRef.current);
    const previewUrl = URL.createObjectURL(file);
    uploadPreviewRef.current = previewUrl;
    setUploadPreview(previewUrl);
    setUploadedFile(file);
    setLensMode("upload");
    setCameraError(null);
    setRecognition(null);
    event.target.value = "";
  }

  function scanAgain() {
    audio.stop();
    setRecognition(null);
  }

  const discoveredCount = discoveredIds.size;
  const total = site.checkpoints.length;
  const complete = discoveredCount === total && total > 0;
  const canScan = lensMode === "camera" ? cameraReady : Boolean(uploadPreview || uploadedFile);
  const scannableCount = site.checkpoints.filter((checkpoint) => referenceSources(checkpoint).length > 0).length;
  const showCameraLoader = lensMode === "camera" && !cameraReady && !cameraError;
  const matchedCheckpoint = recognition?.status === "match" ? recognition.checkpoint : null;
  const locationLabel = position
    ? "Location on"
    : geoError
      ? "Location off"
      : "Finding location…";

  return (
    <div className="dark-ui flex min-h-dvh flex-col bg-[#0c100e] text-ivory pt-[env(safe-area-inset-top)]">
      <header className="flex items-start justify-between gap-3 px-4 py-3">
        <div className="min-w-0">
          <p className="text-[11px] uppercase tracking-[0.18em] text-gold">Scanner</p>
          <p className="font-display text-2xl leading-tight">{site.name}</p>
          <p className="text-xs text-[#d9d3c7]">{locationLabel}</p>
        </div>
        <div className="flex items-center gap-3">
          <ProgressRing discovered={discoveredCount} total={total} size={68} tone="dark" />
          <Link
            href={`/explore/${site.slug}`}
            className="inline-flex min-h-11 items-center px-2 text-sm text-ivory"
          >
            Close
          </Link>
        </div>
      </header>

      <div className="relative min-h-[46vh] flex-1 bg-black">
        {lensMode === "camera" ? (
          <video
            ref={videoRef}
            playsInline
            muted
            className="absolute inset-0 h-full w-full object-cover"
            aria-label="Live camera preview"
          />
        ) : uploadPreview ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={uploadPreview}
            alt="Photograph selected for scanning"
            className="absolute inset-0 h-full w-full object-cover"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center px-6 text-center">
            <div className="max-w-xs">
              <p className="text-base text-[#d9d3c7]">
                {cameraError ?? `Choose a photograph of one place at ${site.name}, then scan it.`}
              </p>
              <p className="mt-3 text-sm text-[#d9d3c7]">
                A scan compares the picture with stored reference photographs. A new angle may not match.
              </p>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="mt-5 inline-flex min-h-12 w-full items-center justify-center border border-white/30 px-4 text-sm"
              >
                Choose a photograph
              </button>
            </div>
          </div>
        )}
        <div className="pointer-events-none absolute inset-6 border border-white/20" aria-hidden="true">
          <span className="absolute left-0 top-0 h-7 w-7 border-l-2 border-t-2 border-gold" />
          <span className="absolute right-0 top-0 h-7 w-7 border-r-2 border-t-2 border-gold" />
          <span className="absolute bottom-0 left-0 h-7 w-7 border-b-2 border-l-2 border-gold" />
          <span className="absolute bottom-0 right-0 h-7 w-7 border-b-2 border-r-2 border-gold" />
        </div>
        {showCameraLoader && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-[#0c100e] text-center">
            <Camera className="h-8 w-8" aria-hidden="true" />
            <p>Starting the camera…</p>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex min-h-11 items-center border border-white/30 px-4 text-sm"
            >
              Upload a photograph instead
            </button>
          </div>
        )}
      </div>

      <canvas ref={canvasRef} className="hidden" />
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        aria-label="Choose a photograph"
        onChange={handleFileChange}
      />

      {nearby.length > 0 && (
        <div className="border-t border-white/10 px-4 py-3">
          <p className="text-[11px] uppercase tracking-[0.16em] text-gold">Nearby</p>
          <ul className="mt-2 flex max-w-full gap-2 overflow-x-auto overscroll-x-contain pb-1">
            {nearby.map((checkpoint) => {
              const found = discoveredIds.has(checkpoint.id);
              return (
                <li key={checkpoint.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setStoryCheckpoint(checkpoint);
                      markDiscovered(checkpoint, found ? "manual" : "gps");
                    }}
                    className="inline-flex min-h-11 shrink-0 flex-col items-start justify-center border border-white/20 px-3 text-left"
                  >
                    <span className="text-sm">{checkpoint.name}</span>
                    <span className="text-[11px] text-[#d9d3c7]">
                      {formatDistance(checkpoint.distance)}
                      {found ? " · Found" : ""}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {activePopup && !storyCheckpoint && !recognition && (
        <section className="border-t border-white/10 px-4 py-4" aria-live="polite">
          <p className="text-[11px] uppercase tracking-[0.16em] text-gold">You are near</p>
          <h2 className="mt-1 font-display text-3xl">{activePopup.name}</h2>
          <p className="mt-2 text-sm text-[#d9d3c7]">{activePopup.shortDescription}</p>
          <div className="mt-4 flex gap-3">
            <button
              type="button"
              onClick={() => setStoryCheckpoint(activePopup)}
              className="inline-flex min-h-11 flex-1 items-center justify-center bg-ivory text-sm font-medium text-primary"
            >
              Read the story
            </button>
            <button
              type="button"
              onClick={() => setActivePopup(null)}
              className="inline-flex min-h-11 items-center justify-center border border-white/25 px-4 text-sm"
            >
              Dismiss
            </button>
          </div>
        </section>
      )}

      {recognition && (
        <RecognitionPanel
          checkpoint={matchedCheckpoint}
          message={recognition.status === "miss" ? recognition.message : null}
          heading={recognition.status === "miss" ? MISS_HEADING[recognition.kind] : undefined}
          saved={matchedCheckpoint ? discoveredIds.has(matchedCheckpoint.id) : false}
          speaking={audio.speaking}
          audioNote={
            audio.unsupported
              ? "Listening is not available in this browser. You can still read the story."
              : null
          }
          onListen={audio.toggle}
          onOpenStory={() => {
            if (matchedCheckpoint) setStoryCheckpoint(matchedCheckpoint);
          }}
          onSave={() => {
            if (matchedCheckpoint) markDiscovered(matchedCheckpoint, "photo_match");
          }}
          onScanAgain={scanAgain}
          checkpointsHref={`/explore/${site.slug}/checkpoints`}
        />
      )}

      {complete && !recognition && (
        <p className="border-t border-white/10 px-4 py-3 text-sm text-[#d9d3c7]">
          You have found all {total} places at {site.name}.
        </p>
      )}

      <div className="space-y-3 border-t border-white/10 px-4 py-4 pb-[max(1.5rem,env(safe-area-inset-bottom))]">
        {(cameraError || geoError) && (
          <p className="text-sm text-[#d9d3c7]" role="status">
            {cameraError ?? geoError}
          </p>
        )}
        {scannableCount < total && (
          <p className="text-sm text-[#d9d3c7]">
            {scannableCount === 0
              ? "No reference photographs are on record here yet. Open the place list to read each one."
              : `Photographs can match ${scannableCount} of ${total} places. The others are read from the list.`}
          </p>
        )}
        <p className="text-sm text-[#d9d3c7]" role="status">
          {scanning
            ? `Comparing this photograph with the reference images for ${site.name}.`
            : recognition?.status === "match"
              ? "The photograph was compared with this destination."
              : recognition?.status === "miss"
                ? "You can scan again without leaving this page."
                : lensMode === "upload" && (uploadPreview || uploadedFile)
                  ? "Photograph ready. It stays on this phone until you scan it."
                  : "Fill the frame with one place, then capture. A match needs a photograph close to a stored reference. JPG, PNG, and WebP can be chosen if the camera is unavailable."}
        </p>
        <div className="flex flex-wrap gap-2">
          {cameraReady && (
            <button
              type="button"
              onClick={() => {
                setLensMode("camera");
                setRecognition(null);
                if (!streamRef.current) setCameraAttempt((attempt) => attempt + 1);
              }}
              aria-pressed={lensMode === "camera"}
              className={`inline-flex min-h-11 items-center gap-2 px-4 text-sm ${
                lensMode === "camera" ? "bg-ivory text-primary" : "border border-white/25"
              }`}
            >
              <Camera className="h-4 w-4" aria-hidden="true" />
              Camera
            </button>
          )}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            aria-pressed={lensMode === "upload"}
            className={`inline-flex min-h-11 flex-1 items-center justify-center gap-2 px-4 text-sm ${
              lensMode === "upload" ? "bg-ivory text-primary" : "border border-white/25"
            }`}
          >
            <Upload className="h-4 w-4" aria-hidden="true" />
            Upload photograph
          </button>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleScan}
            disabled={!canScan || scanning}
            aria-busy={scanning}
            className="inline-flex min-h-12 flex-1 items-center justify-center gap-2 bg-[#c4b083] px-4 text-sm font-medium text-[#1c1915] disabled:opacity-50"
          >
            {scanning ? <Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" aria-hidden="true" /> : null}
            {scanning ? "Comparing photograph…" : "Scan landmark"}
          </button>
          <Link
            href={`/explore/${site.slug}/checkpoints`}
            className="inline-flex min-h-12 items-center justify-center border border-white/25 px-4 text-sm"
          >
            Places
          </Link>
        </div>
      </div>

      {storyCheckpoint && (
        <StoryModal checkpoint={storyCheckpoint} onClose={() => setStoryCheckpoint(null)} />
      )}
    </div>
  );
}
