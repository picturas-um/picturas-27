import { LoaderCircle, Sparkle, type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRouter, useSearchParams } from "next/navigation";
import { useSession } from "@/providers/session-provider";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "../ui/dropdown-menu";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  useCurrentImage,
  usePreview,
  useProjectInfo,
  useUnsavedChanges,
  useCanEditProject,
} from "@/providers/project-provider";
import {
  useAddProjectTool,
  useDeleteProjectTool,
  usePreviewProjectResult,
  useUpdateProjectTool,
} from "@/lib/mutations/projects";
import { isVideo, ProjectTool, ProjectToolResponse } from "@/lib/projects";
import {
  getToolInfo,
  getUnavailableReason,
  getWorksOnText,
} from "@/lib/tool-registry";
import { useGetSocket } from "@/lib/queries/projects";
import { Tooltip, TooltipTrigger, TooltipContent } from "../ui/tooltip";
import { getErrorMessage } from "@/lib/error-messages";
import { useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/hooks/use-toast";

interface ToolbarButtonProps {
  open?: boolean;
  setOpen?: (open: boolean) => void;
  icon: LucideIcon;
  label: string;
  disabled?: boolean;
  previewDisabled?: boolean;
  saveDisabled?: boolean;
  isDefault?: boolean;
  isPremium?: boolean;
  tool: Omit<ProjectTool, "position">;
  children?: React.ReactNode;
  noParams?: boolean;
  onDefault?: () => void;
  // How to find this tool in the pipeline (default: by procedure).
  // Trim uses it to match the trim of the selected video only.
  matchTool?: (t: ProjectToolResponse) => boolean;
}

export function ToolbarButton({
  
  open = false,
  setOpen = () => {},
  icon: Icon,
  label,
  disabled = false,
  previewDisabled = false,
  saveDisabled = false,
  isDefault = false,
  isPremium = false,
  tool,
  children,
  noParams = false,
  onDefault = () => {},
  matchTool,
}: ToolbarButtonProps) {
  const isThisTool = (t: ProjectToolResponse) =>
    matchTool ? matchTool(t) : t.procedure === tool.procedure;

  const router = useRouter();
  const session = useSession();
  const project = useProjectInfo();
  const preview = usePreview();
  const { setHasUnsavedChanges } = useUnsavedChanges();
  const { toast } = useToast();
  const canEdit = useCanEditProject();

  const socket = useGetSocket(session.token);
  const searchParams = useSearchParams();
  const ownerParam = searchParams.get("owner") ?? session.user._id;
  const shareParam = searchParams.get("share") ?? undefined;

  const qc = useQueryClient();

  // memo para não recriar array a cada render (ajuda também)
  const projectKey = useMemo(
    () => ["project", session.user._id, project._id, session.token, ownerParam, shareParam],
    [session.user._id, project._id, session.token, ownerParam, shareParam],
  );

  const handleProjectConflict = (error: any) => {
    const status = error?.response?.status;

    if (status === 409) {
      toast({
        title: "Conflito de edição",
        description:
          "O projeto foi alterado por outro utilizador. Atualizámos para a versão mais recente.",
        variant: "destructive",
      });

      qc.invalidateQueries({ queryKey: projectKey, refetchType: "all" });
      return true;
    }

    return false;
  };

  const variant =
    project.tools.find(isThisTool) !== undefined
      ? "default"
      : "outline";

  const currentImage = useCurrentImage();

  // Why this tool cannot be used in this project right now (null = it can).
  // The rules live in lib/tool-registry.ts and mirror the backend ones.
  const hasVideos = project.imgs.some((i) => isVideo(i));
  const unavailableReason = getUnavailableReason(tool.procedure, {
    hasVideos,
    selected: currentImage ? (isVideo(currentImage) ? "video" : "image") : null,
  });

  const addTool = useAddProjectTool(
    session.user._id,
    project._id,
    session.token,
    ownerParam,
    shareParam,
  );

  const updateTool = useUpdateProjectTool(
    session.user._id,
    project._id,
    session.token,
    ownerParam,
    shareParam,
  );

  const deleteTool = useDeleteProjectTool(
    session.user._id,
    project._id,
    session.token,
    ownerParam,
    shareParam,
  );

  const previewEdits = usePreviewProjectResult(
    session.user._id,
    project._id,
    session.token,
    ownerParam,
    shareParam,
  );

  const [prevTool, setPrevTool] = useState<ProjectToolResponse | undefined>(undefined);
  const [waiting, setWaiting] = useState(false);
  const previewTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const clearPreviewTimer = () => {
    if (previewTimer.current !== null) clearTimeout(previewTimer.current);
    previewTimer.current = null;
  };

  useEffect(() => () => clearPreviewTimer(), []);

  function handleDeleteTool() {
    if (!canEdit) return;
    if (!prevTool) return;

    deleteTool.mutate(
      { toolId: prevTool._id, projectVersion: project.version },
      {
        onError: (error) => {
          if (handleProjectConflict(error)) return;
          const { title, description } = getErrorMessage("project-update", error);
          toast({ title, description, variant: "destructive" });
        },
      },
    );
  }

  function handlePreview() {

    if (!canEdit) return;
    clearPreviewTimer();
    // Start waiting before sending: a cached preview can arrive before HTTP success.
    setWaiting(true);
    preview.setWaiting(tool.procedure);
    const hasSubtitles = tool.procedure === "subtitles" ||
      project.tools.some((item) => item.procedure === "subtitles");
    const hasExtraction = tool.procedure === "extract_frames" ||
      project.tools.some((item) => item.procedure === "extract_frames");
    const timeoutMs = hasSubtitles || hasExtraction ? 10 * 60 * 1000 : 10000 * (project.tools.length + 1);
    previewTimer.current = setTimeout(() => {
      previewTimer.current = null;
      setWaiting(false);
      preview.setWaiting("");
      toast({
        title: "Preview timed out",
        description: hasSubtitles
          ? "Subtitles are taking longer than expected. The worker may still be downloading the speech model or processing another video. Try again later."
          : hasExtraction
            ? "Frame extraction may process the complete edited video. The worker may still be busy. Try again later."
            : "The preview took too long to load.",
        variant: "destructive",
      });
    }, timeoutMs);
    previewEdits.mutate(
      { imageId: currentImage?._id ?? "", projectVersion: project.version },
      {
        onError: (error) => {
          clearPreviewTimer();
          setWaiting(false);
          preview.setWaiting("");
          if (handleProjectConflict(error)) return;
          const { title, description } = getErrorMessage("project-process", error);
          toast({ title, description, variant: "destructive" });
        },
      },
    );
  }

  function handleAddTool(runPreview?: boolean) {
    
    if (!canEdit) return;
    const afterSuccess = () => {
      setHasUnsavedChanges(false); // acabou de guardar
      if (runPreview) handlePreview();
    };

    if (prevTool) {
      updateTool.mutate(
        { toolId: prevTool._id, toolParams: tool.params, projectVersion: project.version },
        {
          onSuccess: afterSuccess,
          onError: (error) => {
            if (handleProjectConflict(error)) return;
            const { title, description } = getErrorMessage("project-update", error);
            toast({ title, description, variant: "destructive" });
          },
        },
      );
    } else {
      addTool.mutate(
        { tool: { ...tool, position: project.tools.length }, projectVersion: project.version },
        {
          onSuccess: afterSuccess,
          onError: (error) => {
            if (handleProjectConflict(error)) return;
            const { title, description } = getErrorMessage("project-update", error);
            toast({ title, description, variant: "destructive" });
          },
        },
      );
    }

    setOpen(false);
  }

  function handleClick() {

     if (!canEdit) {
      toast({
        title: "Read-only",
        description: "Este projeto foi partilhado com permissão de leitura.",
        variant: "destructive",
      });
      return;
    }

    if (isPremium && session.user.type === "anonymous") {
      router.push("/login");
      return;
    }

    if (noParams) {
      if (prevTool) handleDeleteTool();
      else handleAddTool(true);
    }
  }

  useEffect(() => {
    const s = socket.data;
    if (!s) return;

    const onPreviewReady = () => {
      clearPreviewTimer();
      setWaiting(false);
      preview.setWaiting("");
    };

    s.on("preview-ready", onPreviewReady);
    s.on("preview-error", onPreviewReady);

    return () => {
      s.off("preview-ready", onPreviewReady);
      s.off("preview-error", onPreviewReady);
    };
  }, [socket.data, preview]);

  useEffect(() => {
    setPrevTool(project.tools.find(isThisTool));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.tools, tool.procedure, matchTool]);

  const locked = !canEdit;

  const uiDisabled =
    disabled ||
    locked ||
    unavailableReason !== null ||
    (preview.waiting !== tool.procedure && preview.waiting !== "");

  // Small corner label for tools that only work on one kind of media.
  // Tools that work on both get no label (the tooltip says so).
  const mediaInfo = getToolInfo(tool.procedure);
  const cornerBadge =
    mediaInfo && mediaInfo.media !== "both"
      ? mediaInfo.media === "image"
        ? "IMG"
        : "VID"
      : null;
  const worksOnText = getWorksOnText(tool.procedure);

  const lockReason = "Read-only (não podes editar)";

  const TButton = () => (
    <Tooltip>
      {/* The span (not the button) receives the hover, so the tooltip also
          works when the button is disabled. */}
      <TooltipTrigger asChild>
        <span
          className="inline-block rounded-md"
          tabIndex={unavailableReason ? 0 : undefined}
        >
          <Button
            variant={variant}
            className={`size-8 relative ${
              isPremium && variant === "default" ? "bg-indigo-500 hover:bg-indigo-400" : ""
            }`}
            disabled={uiDisabled}
            onClick={handleClick}
          >
            {waiting ? (
              <LoaderCircle className="animate-spin" />
            ) : (
              <>
                {isPremium ? (
                  <div
                    className={
                      isPremium && variant === "default" ? "text-white" : "text-indigo-500"
                    }
                  >
                    <Icon className="h-3.5 w-3.5" />
                    <Sparkle className="h-3 w-3 absolute -top-1 -right-1" />
                    <span className="sr-only">{label}</span>
                  </div>
                ) : (
                  <>
                    <Icon className="h-3.5 w-3.5" />
                    <span className="sr-only">{label}</span>
                  </>
                )}
              </>
            )}
            {cornerBadge && (
              <span
                aria-hidden="true"
                className="pointer-events-none absolute -bottom-1 -right-1 rounded border bg-background px-0.5 text-[8px] font-semibold leading-3 text-muted-foreground"
              >
                {cornerBadge}
              </span>
            )}
          </Button>
        </span>
      </TooltipTrigger>
      <TooltipContent className="ml-2 max-w-52 bg-indigo-500" side="right">
        <div className="font-medium">{label}</div>
        {unavailableReason ? (
          <div className="pt-0.5">{unavailableReason}</div>
        ) : (
          worksOnText && <div className="pt-0.5 opacity-90">{worksOnText}</div>
        )}
      </TooltipContent>
    </Tooltip>
  );

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      {!locked && !((isPremium && session.user.type === "anonymous") || noParams) ? (
        <DropdownMenuTrigger asChild disabled={uiDisabled}>
          <div>
            <TButton />
          </div>
        </DropdownMenuTrigger>
      ) : (
        <div>
          <TButton />
        </div>
      )}


      {!locked && (
        <DropdownMenuContent
          className="w-[--radix-dropdown-menu-trigger-width] min-w-64 rounded-lg"
          side="right"
          align="end"
          sideOffset={4}
        >

        <DropdownMenuLabel className="text-sm p-1">{label}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <div className="p-1">{children}</div>
        <DropdownMenuSeparator />

        <div className="flex w-full gap-1 items-center">
          <Button
            variant="outline"
            className="h-6 text-xs"
            onClick={() => {
              handleDeleteTool();
              onDefault();
            }}
            disabled={isDefault}
          >
            Default
          </Button>

          <Button
            variant="outline"
            onClick={() => handleAddTool(true)}
            className="h-6 text-xs"
            disabled={isDefault || previewDisabled || saveDisabled}
          >
            Preview
          </Button>

          <Button
            onClick={() => handleAddTool(false)}
            disabled={isDefault || saveDisabled}
            className="h-6 text-xs w-full"
          >
            Save
          </Button>
        </div>
      </DropdownMenuContent>
    )}
    </DropdownMenu>
  );
}
