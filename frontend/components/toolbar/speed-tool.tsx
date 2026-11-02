// Playback speed tool (0.25x to 5x), video only.
// Like trim, a speed change belongs to the video it was defined on.
import { ToolbarButton } from "./toolbar-button";
import { Gauge } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import {
  useCurrentImage,
  useProjectInfo,
  useUnsavedChanges,
} from "@/providers/project-provider";
import { SpeedToolParams } from "@/lib/tool-types";
import { isVideo, ProjectToolResponse } from "@/lib/projects";
import { Slider } from "../ui/slider";

const MIN_SPEED = 0.25;
const MAX_SPEED = 5;
const DEFAULT_SPEED = 1;

export default function SpeedTool({ disabled }: { disabled: boolean }) {
  const project = useProjectInfo();
  const currentImage = useCurrentImage();
  const { setHasUnsavedChanges } = useUnsavedChanges();

  const videoId = currentImage?._id ?? "";
  const duration = currentImage?.video?.duration ?? 0;

  const [factor, setFactor] = useState<number>(DEFAULT_SPEED);
  const [open, setOpen] = useState<boolean>(false);

  // the speed change of the selected video, if any
  const matchTool = useCallback(
    (t: ProjectToolResponse) =>
      t.procedure === "speed" && (t.params as SpeedToolParams).imgId === videoId,
    [videoId],
  );

  useEffect(() => {
    const speedTool = project.tools.find(matchTool);
    setFactor(speedTool ? (speedTool.params as SpeedToolParams).factor : DEFAULT_SPEED);
  }, [project.tools, open, matchTool]);

  // only shown while a video is selected
  if (!currentImage || !isVideo(currentImage)) return null;

  return (
    <ToolbarButton
      open={open}
      setOpen={setOpen}
      tool={{
        procedure: "speed",
        params: { factor, imgId: videoId },
      }}
      matchTool={matchTool}
      onDefault={() => {
        setFactor(DEFAULT_SPEED);
        setHasUnsavedChanges(false);
      }}
      isDefault={factor === DEFAULT_SPEED}
      disabled={disabled}
      icon={Gauge}
      label="Speed (this video)"
    >
      <Slider
        min={MIN_SPEED}
        max={MAX_SPEED}
        step={0.25}
        value={[factor]}
        onValueChange={(v) => {
          setFactor(v[0]);
          setHasUnsavedChanges(true);
        }}
        className="w-full"
      />
      <div className="flex w-full justify-between items-center text-xs text-gray-500 pt-1">
        <span>{MIN_SPEED}x</span>
        <span className="font-semibold">{factor}x</span>
        <span>{MAX_SPEED}x</span>
      </div>
      {duration > 0 && (
        <span className="text-xs text-gray-500">
          {duration.toFixed(1)} s becomes {(duration / factor).toFixed(1)} s. Applies to this
          video only.
        </span>
      )}
    </ToolbarButton>
  );
}
