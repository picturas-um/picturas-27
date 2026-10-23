
"use client";

import dynamic from "next/dynamic";

const TrimVideo = dynamic(
  () => import("@/components/video-tools/trim-video"),
  { ssr: false }
);

export default function TrimVideoPage() {
  return <TrimVideo />;
}
