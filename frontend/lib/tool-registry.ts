// Single source of truth, on the frontend, about the editing tools:
// readable name, which media each tool applies to and pipeline position rules.
//
// It mirrors what the `projects` service enforces in projects/utils/video.js
// (VIDEO_TOOLS, VIDEO_ONLY_TOOLS, PER_VIDEO_TOOLS and validateFrameExtraction).
// When a tool is added or its rules change, update both sides.
import type { ToolNames } from "@/lib/tool-types";

/** Which kind of media a tool can be applied to. */
export type ToolMedia = "image" | "video" | "both";

/** Every real tool ("scale" and "project" in ToolNames are not toolbar tools). */
export type RegisteredTool = Exclude<ToolNames, "scale" | "project">;

export interface ToolInfo {
  procedure: RegisteredTool;
  /** Readable name, for lists and messages. */
  label: string;
  /** Media the tool applies to: only images, only videos, or both. */
  media: ToolMedia;
  /** Defined for one specific video (params.imgId), e.g. trim and speed. */
  perVideo: boolean;
  /** Project-wide video effect: applied to every video, whichever item is selected. */
  allVideos?: boolean;
  /** Must be the last step of the pipeline (and can appear only once). */
  mustBeLast: boolean;
}

// The order is the order of the toolbar.
export const TOOL_REGISTRY: Record<RegisteredTool, ToolInfo> = {
  brightness: { procedure: "brightness", label: "Brightness", media: "both", perVideo: false, mustBeLast: false },
  contrast: { procedure: "contrast", label: "Contrast", media: "both", perVideo: false, mustBeLast: false },
  saturation: { procedure: "saturation", label: "Saturation", media: "both", perVideo: false, mustBeLast: false },
  binarization: { procedure: "binarization", label: "Black & White", media: "both", perVideo: false, mustBeLast: false },
  rotate: { procedure: "rotate", label: "Rotate", media: "both", perVideo: false, mustBeLast: false },
  cut: { procedure: "cut", label: "Crop", media: "both", perVideo: false, mustBeLast: false },
  resize: { procedure: "resize", label: "Resize", media: "both", perVideo: false, mustBeLast: false },
  border: { procedure: "border", label: "Border", media: "both", perVideo: false, mustBeLast: false },

  // Video only
  trim: { procedure: "trim", label: "Trim", media: "video", perVideo: true, mustBeLast: false },
  speed: { procedure: "speed", label: "Speed", media: "video", perVideo: true, mustBeLast: false },
  subtitles: { procedure: "subtitles", label: "Automatic subtitles", media: "video", perVideo: false, allVideos: true, mustBeLast: false },
  extract_frames: { procedure: "extract_frames", label: "Extract frames", media: "video", perVideo: false, allVideos: true, mustBeLast: true },

  // Image only (the video worker does not support them)
  watermark: { procedure: "watermark", label: "Watermark", media: "image", perVideo: false, mustBeLast: false },
  bg_remove_ai: { procedure: "bg_remove_ai", label: "AI Background Removal", media: "image", perVideo: false, mustBeLast: false },
  cut_ai: { procedure: "cut_ai", label: "AI Crop", media: "image", perVideo: false, mustBeLast: false },
  obj_ai: { procedure: "obj_ai", label: "AI Object Detection", media: "image", perVideo: false, mustBeLast: false },
  people_ai: { procedure: "people_ai", label: "AI People Detection", media: "image", perVideo: false, mustBeLast: false },
  text_ai: { procedure: "text_ai", label: "AI Text Detection", media: "image", perVideo: false, mustBeLast: false },
  expand_ai: { procedure: "expand_ai", label: "AI Expand", media: "image", perVideo: false, mustBeLast: false },
  upgrade_ai: { procedure: "upgrade_ai", label: "AI Upgrade", media: "image", perVideo: false, mustBeLast: false },
};

/** All the tools, in toolbar order. */
export const TOOL_LIST: ToolInfo[] = Object.values(TOOL_REGISTRY);

/** Looks a tool up by its procedure name. Unknown procedures return undefined. */
export function getToolInfo(procedure: string): ToolInfo | undefined {
  return Object.prototype.hasOwnProperty.call(TOOL_REGISTRY, procedure)
    ? TOOL_REGISTRY[procedure as RegisteredTool]
    : undefined;
}

/** Readable name of a tool; falls back to the procedure name if unknown. */
export function getToolLabel(procedure: string): string {
  return getToolInfo(procedure)?.label ?? procedure;
}

/** Whether the tool can be applied to this kind of media. Unknown tools are not restricted. */
export function appliesToMedia(procedure: string, kind: "image" | "video"): boolean {
  const info = getToolInfo(procedure);
  return !info || info.media === "both" || info.media === kind;
}

/** Short text for the Image / Video badge. Null for unknown tools. */
export function getMediaBadge(procedure: string): string | null {
  const info = getToolInfo(procedure);
  if (!info) return null;
  if (info.media === "image") return "Image";
  if (info.media === "video") return "Video";
  return "Image & video";
}

/** Line for tooltips saying which media the tool applies to. Null for unknown tools. */
export function getWorksOnText(procedure: string): string | null {
  const info = getToolInfo(procedure);
  if (!info) return null;
  if (info.allVideos) return "Applies to every video in the project.";
  const badge = getMediaBadge(procedure);
  return badge ? `Works on: ${badge}` : null;
}

export interface ProjectMediaContext {
  /** The project has at least one video. */
  hasVideos: boolean;
  /** Kind of the media item currently selected, if any. */
  selected?: "image" | "video" | null;
}

/**
 * Why a tool cannot be used right now, or null if it can.
 * Same rules as the backend: image-only tools are rejected when the project has
 * videos, video-only tools when it has none, and trim/speed need a selected video.
 */
export function getUnavailableReason(
  procedure: string,
  context: ProjectMediaContext,
): string | null {
  const info = getToolInfo(procedure);
  if (!info) return null;

  if (info.media === "image" && context.hasVideos) {
    return "Image only. Not available while the project contains videos.";
  }
  if (info.media === "video" && !context.hasVideos) {
    return "Video only. Add a video to this project to use it.";
  }
  if (info.perVideo && context.hasVideos && context.selected !== "video") {
    return "Select a video to use this tool. It applies to that video only.";
  }
  return null;
}
