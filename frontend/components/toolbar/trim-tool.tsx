// Trim tool (time cut), video only.
// Unlike the other effects, a trim belongs to the video it was defined on
// because its times only make sense for that video's duration.
import { ToolbarButton } from "./toolbar-button";
import { Scissors } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import {
  useCurrentImage,
  useProjectInfo,
  useUnsavedChanges,
} from "@/providers/project-provider";
import { TrimToolParams } from "@/lib/tool-types";
import { isVideo, ProjectToolResponse } from "@/lib/projects";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

export default function TrimTool({ disabled }: { disabled: boolean }) {
  const project = useProjectInfo();
  const currentImage = useCurrentImage();
  const { setHasUnsavedChanges } = useUnsavedChanges();

  const videoId = currentImage?._id ?? "";
  const maxDuration = currentImage?.video?.duration ?? 0;

  const round = (n: number) => Math.round(n * 10) / 10;
  const [start, setStart] = useState<number>(0);
  const [end, setEnd] = useState<number>(round(maxDuration));
  const [open, setOpen] = useState<boolean>(false);

  // the trim of the selected video, if any
  const matchTool = useCallback(
    (t: ProjectToolResponse) =>
      t.procedure === "trim" && (t.params as TrimToolParams).imgId === videoId,
    [videoId],
  );

  useEffect(() => {
    const trimTool = project.tools.find(matchTool);
    if (trimTool) {
      setStart((trimTool.params as TrimToolParams).start);
      setEnd((trimTool.params as TrimToolParams).end);
    } else {
      setStart(0);
      setEnd(round(maxDuration));
    }
  }, [project.tools, open, maxDuration, matchTool]);

  // End must be after start and within the video duration
  const error =
    start < 0
      ? "Start cannot be negative."
      : end <= start
        ? "End must be after start."
        : maxDuration > 0 && end > maxDuration + 0.05
          ? `End exceeds the video duration (${maxDuration.toFixed(1)} s).`
          : null;

  const isDefault = start === 0 && end === round(maxDuration);

  // only shown while a video is selected
  if (!currentImage || !isVideo(currentImage)) return null;

  return (
    <ToolbarButton
      open={open}
      setOpen={setOpen}
      tool={{
        procedure: "trim",
        params: { start, end, imgId: videoId },
      }}
      matchTool={matchTool}
      onDefault={() => {
        setStart(0);
        setEnd(round(maxDuration));
        setHasUnsavedChanges(false);
      }}
      isDefault={isDefault || error !== null}
      disabled={disabled}
      icon={Scissors}
      label="Trim (this video)"
    >
      <div className="flex flex-col gap-2">
        <div className="flex gap-2">
          <div className="flex flex-col gap-1 w-full">
            <Label className="text-xs">Start (s)</Label>
            <Input
              type="number"
              min={0}
              step={0.1}
              value={start}
              onChange={(e) => {
                setStart(Number(e.target.value));
                setHasUnsavedChanges(true);
              }}
              className="h-7 text-xs"
            />
          </div>
          <div className="flex flex-col gap-1 w-full">
            <Label className="text-xs">End (s)</Label>
            <Input
              type="number"
              min={0}
              max={maxDuration || undefined}
              step={0.1}
              value={end}
              onChange={(e) => {
                setEnd(Number(e.target.value));
                setHasUnsavedChanges(true);
              }}
              className="h-7 text-xs"
            />
          </div>
        </div>
        <span className={`text-xs ${error ? "text-red-400" : "text-gray-500"}`}>
          {error ??
            `Keeps ${(end - start).toFixed(1)} s of ${maxDuration.toFixed(1)} s. Applies to this video only.`}
        </span>
      </div>
    </ToolbarButton>
  );
}
