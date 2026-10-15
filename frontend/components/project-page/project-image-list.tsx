"use client";

import { useState, useEffect } from "react";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
  type CarouselApi,
} from "@/components/ui/carousel";
import { useGetSocket } from "@/lib/queries/projects";
import { useCanEditProject, useCurrentImage, useProjectInfo, useVideoTrim } from "@/providers/project-provider";
import { useRouter, useSearchParams } from "next/navigation";
import { useSession } from "@/providers/session-provider";
import {
  Dialog,
  DialogHeader,
  DialogTitle,
  DialogContent,
  DialogFooter,
} from "../ui/dialog";
import Image from "next/image";
import { useToast } from "@/hooks/use-toast";
import * as ProjectTypes from "@/lib/projects";
import { ProjectImage } from "./project-image";
import { VideoTrimPanel } from "@/components/toolbar/video-trim-tool";
import { useQueryClient } from "@tanstack/react-query";
import ProjectText from "./project-text";
import { getAiErrorMessage, getErrorMessage } from "@/lib/error-messages";
import { usePreview } from "@/providers/project-provider";
import AppDropzone from "@/components/app-dropzone";
import { useAddProjectImages } from "@/lib/mutations/projects";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

export function ProjectImageList({
  setCurrentImageId,
  results,
}: {
  setCurrentImageId: (img: ProjectTypes.ProjectImage) => void;
  results: {
    imgs: ProjectTypes.ProjectImage[];
    texts: ProjectTypes.ProjectImageText[];
  };
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const view = searchParams.get("view") ?? "grid";
  const mode = searchParams.get("mode") ?? "edit";
  const owner = searchParams.get("owner");
  const share = searchParams.get("share");  

  const [api, setApi] = useState<CarouselApi>();
  const [current, setCurrent] = useState(0);
  const [count, setCount] = useState(0);
  const [jumpTo, setJumpTo] = useState<number | null>(null);
  const [previewOpen, setPreviewOpen] = useState<boolean>(false);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [previewText, setPreviewText] = useState<string[] | null>(null);
  const [mediaFilter, setMediaFilter] = useState("all");

  const project = useProjectInfo();
  const currentImage = useCurrentImage();
  const canEdit = useCanEditProject();
  const { videoTrimOpen } = useVideoTrim();
  const session = useSession();
  const { toast } = useToast();
  const preview = usePreview();
  const addProjectMedia = useAddProjectImages(
    session.user._id,
    project._id,
    session.token,
    owner ?? undefined,
    share ?? undefined,
  );

  const qc = useQueryClient();
  const socket = useGetSocket(session.token);

  const showVideoTrim = Boolean(
    view === "carousel" &&
      mode === "edit" &&
      videoTrimOpen &&
      currentImage?.url &&
      /\.(mp4|webm)$/i.test(currentImage.name || currentImage.url),
  );


useEffect(() => {
  let active = true;

  if (active && socket.data) {
    socket.data.on("preview-error", (msg: string) => {
      if (!active) return;

      try {
        const msg_content = JSON.parse(msg) as {
          error_code?: number;
          error_msg?: string;
        };

        const error_code = msg_content.error_code;
        const error_msg = msg_content.error_msg;

        console.error("preview-error", error_code, error_msg);

        const { title, description } = getAiErrorMessage(
          error_code,
          error_msg,
        );

        toast({
          title,
          description,
          variant: "destructive",
        });
      } catch (e) {

        const { title, description } = getAiErrorMessage();
        toast({
          title,
          description,
          variant: "destructive",
        });
      } finally {
          // preview falhou → limpa o estado de preview “em curso”
          preview.setWaiting("");
      }
    });

      socket.data.on("preview-ready", (msg: string) => {
        if (active) {
          const msg_content = JSON.parse(msg) as {
            imageUrl: string;
            textResults: string[];
          };
          const url = msg_content.imageUrl;
          const textResults = msg_content.textResults;
          setPreviewImage(url);
          setPreviewText(textResults);
          setPreviewOpen(true);
        }
      });
    }

    return () => {
      active = false;
      if (socket.data) {
        socket.data.off("preview-error");
        socket.data.off("preview-ready");
      }
    };
  }, [socket.data, toast]);

  useEffect(() => {
    if (view === "grid") {
      setApi(undefined);
      setJumpTo(null);
    }
  }, [view]);

  useEffect(() => {
    if (!api) {
      return;
    }

    setCount(api.scrollSnapList().length);
    setCurrent(api.selectedScrollSnap() + 1);
    if (project.imgs) setCurrentImageId(project.imgs[api.selectedScrollSnap()]);

    const handleSelect = () => {
      setCurrent(api.selectedScrollSnap() + 1);
      if (project.imgs)
        setCurrentImageId(project.imgs[api.selectedScrollSnap()]);
    };

    api.on("select", () => {
      setCurrent(api.selectedScrollSnap() + 1);
      if (project.imgs)
        setCurrentImageId(project.imgs[api.selectedScrollSnap()]);
    });

    if (jumpTo !== null && jumpTo !== api.selectedScrollSnap()) {
      api.scrollTo(jumpTo, true);
      setJumpTo(null);
    }

    return () => {
      api.off("select", handleSelect);
    };
  }, [api, jumpTo, project.imgs, setCurrentImageId]);

  const isVideo = (image: ProjectTypes.ProjectImage) =>
    image.mediaMetadata?.format === "mp4" ||
    image.mediaMetadata?.format === "webm" ||
    /\.(mp4|webm|mov|m4v)$/i.test(image.name || image.url);
  const videoImages = project.imgs.filter(isVideo);
  const photoImages = project.imgs.filter((image) => !isVideo(image));
  const gridImages =
    mode === "results"
      ? results.imgs
      : mediaFilter === "videos"
        ? videoImages
        : mediaFilter === "images"
          ? photoImages
          : project.imgs;
  const carouselImages = mode === "results" ? results.imgs : project.imgs;

  const handleGridDrop = (files: File[]) => {
    if (!canEdit || files.length === 0) return;
    addProjectMedia.mutate(
      { images: files, projectVersion: project.version },
      {
        onSuccess: (result) => {
          const uploadedNames = result.succeeded.map((file) => file.name).join(", ") || "none";
          const failureDetails = result.failed
            .map(({ file, message }) => `${file.name}: ${message}`)
            .join("; ");
          toast({
            title: result.failed.length > 0
              ? `${result.succeeded.length} uploaded; ${result.failed.length} failed`
              : "Media added successfully.",
            description: result.failed.length > 0
              ? `Uploaded: ${uploadedNames}. Failed: ${failureDetails}`
              : uploadedNames,
            variant: result.failed.length > 0 ? "destructive" : undefined,
          });
        },
        onError: (error) => {
          const { title, description } = getErrorMessage("project-upload", error);
          toast({ title, description, variant: "destructive" });
        },
      },
    );
  };

  const gridContent = (
    <div className="size-full flex flex-col items-center">
      {(mode === "edit" && project.imgs.length > 0) ||
      (mode === "results" && (results.imgs.length > 0 || results.texts.length > 0)) ? (
        <>
          {mode !== "results" && (
            <div className="relative pt-4 pb-2 text-gray-500 text-sm after:h-2 after:bg-gradient-to-b after:from-background after:to-background/10 after:w-full after:absolute after:bottom-0 after:translate-y-2 after:z-50 w-full text-center flex flex-col">
              Select an image or video from the grid to view it. Drop media here to add it to the project.
            </div>
          )}
          {mode === "edit" && project.imgs.length > 0 && (
            <Tabs value={mediaFilter} onValueChange={setMediaFilter} className="w-full px-2 pt-3">
              <TabsList>
                <TabsTrigger value="all">All ({project.imgs.length})</TabsTrigger>
                <TabsTrigger value="images">Images ({photoImages.length})</TabsTrigger>
                <TabsTrigger value="videos">Videos ({videoImages.length})</TabsTrigger>
              </TabsList>
            </Tabs>
          )}
          {gridImages.length > 0 || (mode === "results" && results.texts.length > 0) ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-2 p-2 overflow-scroll overflow-x-hidden h-fit w-full">
              {gridImages.map((image) => (
                <button
                  key={image._id}
                  className="aspect-square"
                  onClick={() => {
                    setCurrentImageId(image);
                    setJumpTo(carouselImages.findIndex((item) => item._id === image._id));

                    const params = new URLSearchParams();
                    params.set("mode", mode);
                    params.set("view", "carousel");
                    if (owner) params.set("owner", owner);
                    if (share) params.set("share", share);

                    router.push(`?${params.toString()}`);
                    qc.invalidateQueries({ queryKey: ["socket"], refetchType: "all" });
                  }}
                >
                  <ProjectImage image={image} />
                </button>
              ))}
              {mode === "results" &&
                results.texts.map((text, index) => (
                  <button
                    key={text._id + index}
                    className="aspect-square"
                    onClick={() => {
                      setJumpTo(results.imgs.length + index);

                      const params = new URLSearchParams();
                      params.set("mode", mode);
                      params.set("view", "carousel");
                      if (owner) params.set("owner", owner);
                      if (share) params.set("share", share);

                      router.push(`?${params.toString()}`);
                      qc.invalidateQueries({ queryKey: ["socket"], refetchType: "all" });
                    }}
                  >
                    <ProjectText text={text.text} />
                  </button>
                ))}
            </div>
          ) : (
            <div className="flex flex-1 items-center justify-center p-8 text-gray-500">
              {mediaFilter === "videos" ? "No videos in this project yet." : "No images in this project yet."}
            </div>
          )}
        </>
      ) : (
        <div className="flex flex-col items-center justify-center h-full p-8 text-center">
          <p className="text-gray-500 text-xl">
            {mode === "results"
              ? "No results found. Apply your changes and try again."
              : "Add images or videos to this project to get started."}
          </p>
          {mode === "edit" && canEdit && (
            <p className="mt-2 text-sm text-muted-foreground">Drop an image or MP4/WebM video anywhere in this area, or choose Add Media.</p>
          )}
        </div>
      )}
    </div>
  );

  return (
    <Dialog
      open={previewOpen}
      onOpenChange={() => {
        setPreviewOpen(false);
        setPreviewImage(null);
      }}
    >
      <div className={showVideoTrim ? "h-full min-h-0 w-full overflow-y-auto flex flex-col" : "size-full"}>
        {view === "grid" || project.imgs.length <= 0 ? (
          mode === "edit" && canEdit ? (
            <AppDropzone
              onDrop={handleGridDrop}
              noClick
              dropzoneClassName={project.imgs.length === 0 ? "min-h-[55vh]" : ""}
            >
              {gridContent}
            </AppDropzone>
          ) : (
            gridContent
          )
        ) : (
          // Carousel view
          <>
            <div className={showVideoTrim ? "w-full shrink-0 px-2 sm:px-10 py-2" : "size-full px-2 sm:px-16 py-2"}>
              <Carousel setApi={setApi}>
                <CarouselContent
                  className="aspect-auto h-[calc(100vh-99px-0.5rem-36px)] xl:h-[calc(100vh-55px-0.5rem-36px)]"
                  style={showVideoTrim ? { height: "min(52vh, 560px)" } : undefined}
                >
                  {mode === "edit" &&
                    project.imgs.length > 0 &&
                    project.imgs.map((image) => (
                      <CarouselItem key={image._id}>
                        <ProjectImage image={image} animation={false} />
                      </CarouselItem>
                    ))}
                  {mode === "results" &&
                    results.imgs.length > 0 &&
                    results.imgs.map((image) => (
                      <CarouselItem key={image._id}>
                        <ProjectImage image={image} animation={false} />
                      </CarouselItem>
                    ))}
                  {mode === "results" &&
                    results.texts.length > 0 &&
                    results.texts.map((text) => (
                      <CarouselItem key={text.name}>
                        <ProjectText text={text.text} />
                      </CarouselItem>
                    ))}
                </CarouselContent>
                <CarouselPrevious className="hidden sm:flex" />
                <CarouselNext className="hidden sm:flex" />
              </Carousel>
              <div className="py-2 text-center text-sm text-muted-foreground">
                {current} / {count}
              </div>
            </div>
            {showVideoTrim && <VideoTrimPanel disabled={!canEdit} />}
          </>
        )}
      </div>
      <DialogContent className="max-w-[80%] mt-4 overflow-y-scroll overflow-x-hidden">
        <DialogHeader>
          <DialogTitle>Image Preview</DialogTitle>
        </DialogHeader>
        <div className="flex justify-center items-center">
          {previewImage && (
            <Image
              src={previewImage}
              width={500}
              height={500}
              className={`object-contain rounded-md w-full ${previewText ? "max-h-[60vh]" : "max-h-[80vh]"}`}
              alt="Preview"
              unoptimized
            />
          )}
        </div>
        {previewText && previewText.length > 0 && (
          <DialogFooter>
            <div className="flex flex-col gap-2 w-full h-96">
              {previewText.map((text, index) => (
                <iframe
                  src={text}
                  key={index}
                  className="text-sm text-center font-medium size-full"
                />
              ))}
            </div>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
