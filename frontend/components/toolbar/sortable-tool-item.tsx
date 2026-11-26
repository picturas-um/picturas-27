"use client";

import type { CSSProperties, ReactNode } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { X, GripVertical, Lock } from "lucide-react";
import { getToolInfo, getToolLabel, getWorksOnText } from "@/lib/tool-registry";
import type { StepIssue } from "@/lib/pipeline-validation";
import type { ProjectToolResponse } from "@/lib/projects";

interface ToolItemProps {
  tool: ProjectToolResponse;
  onRemove: (id: string) => void;
  // Why the backend would refuse this step, if it would (shown in red)
  issue?: StepIssue;
}

// One row of the "Applied" list. It is shared by the draggable rows and by the
// locked rows (steps that always stay at the end, like extract frames).
function ToolRow({
  tool,
  onRemove,
  issue,
  handle,
  locked = false,
  rowRef,
  style,
}: ToolItemProps & {
  handle: ReactNode;
  locked?: boolean;
  rowRef?: (node: HTMLElement | null) => void;
  style?: CSSProperties;
}) {
  const info = getToolInfo(tool.procedure);
  const label = getToolLabel(tool.procedure);
  const worksOn = getWorksOnText(tool.procedure);

  // Small label only for tools that work on one kind of media
  // (same as in the toolbar; the hover text explains the rest)
  const cornerBadge =
    info && info.media !== "both" ? (info.media === "image" ? "IMG" : "VID") : null;

  const title = [
    label,
    worksOn,
    locked ? "Always the last step of the pipeline." : null,
    issue ? issue.detail : null,
  ]
    .filter(Boolean)
    .join("\n");

  return (
    <div
      ref={rowRef}
      style={style}
      title={title}
      className={`flex w-full flex-col gap-0.5 rounded px-2 py-1 ${
        issue ? "border border-red-500/60 bg-red-500/10" : "bg-muted/50"
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex min-w-0 items-center gap-1">
          {handle}
          {cornerBadge && (
            <span className="rounded border bg-background px-0.5 text-[8px] font-semibold leading-3 text-muted-foreground">
              {cornerBadge}
            </span>
          )}
        </div>

        <X
          onClick={() => onRemove(tool._id)}
          className="w-3 h-3 cursor-pointer text-red-500 flex-shrink-0"
        />
      </div>

      <span className="break-words text-[11px] leading-tight">{label}</span>

      {issue && (
        <span className="text-[10px] font-medium leading-tight text-red-500">
          {issue.short}
        </span>
      )}
    </div>
  );
}

export function SortableToolItem({ tool, onRemove, issue }: ToolItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({
    id: tool._id,
  });

  return (
    <ToolRow
      tool={tool}
      onRemove={onRemove}
      issue={issue}
      rowRef={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
      }}
      handle={
        <GripVertical
          className="w-3 h-3 flex-shrink-0 cursor-grab"
          {...attributes}
          {...listeners}
        />
      }
    />
  );
}

// A step that always stays at the end of the pipeline (extract frames).
// It cannot be dragged, and nothing can be dropped after it.
export function LockedToolItem({ tool, onRemove, issue }: ToolItemProps) {
  return (
    <ToolRow
      tool={tool}
      onRemove={onRemove}
      issue={issue}
      locked
      handle={<Lock className="w-3 h-3 flex-shrink-0 text-muted-foreground" />}
    />
  );
}
