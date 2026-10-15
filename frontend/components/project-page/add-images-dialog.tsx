"use client";

import { useState } from "react";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import ImageSubmissionArea from "../image-submission-area";
import { LoaderCircle, Plus } from "lucide-react";
import { useAddProjectImages } from "@/lib/mutations/projects";
import { createBlobUrlFromFile } from "@/lib/utils";
import { useProjectInfo } from "@/providers/project-provider";
import { useSession } from "@/providers/session-provider";
import { useToast } from "@/hooks/use-toast";
import { getErrorMessage } from "@/lib/error-messages";

export function AddImagesDialog() {
  const [open, setOpen] = useState(false);
  const [images, setImages] = useState<string[]>([]);
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [fileErrors, setFileErrors] = useState<{ fileName: string; message: string }[]>([]);
  const { toast } = useToast();

  const { _id: pid, version} = useProjectInfo();
  const session = useSession();

  const addImages = useAddProjectImages(
    session.user._id,
    pid as string,
    session.token,
  );

  function onDrop(files: File[], source: "selection" | "sync" = "selection") {
    Promise.all(files.map((file) => createBlobUrlFromFile(file))).then(setImages);
    setImageFiles(files);
    if (source === "selection") setFileErrors([]);
  }

  function handleAdd() {
    addImages.mutate(
      {
        images: imageFiles,
        projectVersion: version,
      },
      {
        onSuccess: async (result) => {
          if (result.failed.length > 0) {
            setImageFiles(result.failed.map(({ file }) => file));
            setImages(await Promise.all(result.failed.map(({ file }) => createBlobUrlFromFile(file))));
            setFileErrors(result.failed.map(({ file, message }) => ({ fileName: file.name, message })));
            toast({
              title: `${result.succeeded.length} uploaded; ${result.failed.length} failed`,
              description: `Uploaded: ${result.succeeded.map((file) => file.name).join(", ") || "none"}. Failed files remain selected so you can retry them.`,
              variant: "destructive",
            });
            return;
          }

          toast({
            title: "Media added successfully.",
            description: result.succeeded.map((file) => file.name).join(", "),
          });
          setImages([]);
          setImageFiles([]);
          setFileErrors([]);
          setOpen(false);
        },
        onError: (error) => {
          const { title, description } = getErrorMessage("project-upload", error);
          toast({
            title,
            description,
            variant: "destructive",
          });
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="inline-flex" variant="outline">
          <Plus /> Add Media
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Add Media</DialogTitle>
          <DialogDescription>
            Add images or videos to your project.
          </DialogDescription>
        </DialogHeader>
        <ImageSubmissionArea onDrop={onDrop} receivedFiles={imageFiles} />
        {fileErrors.length > 0 && (
          <div className="max-h-28 overflow-y-auto rounded-md border border-destructive/40 p-2 text-sm" role="alert">
            <p className="mb-1 font-medium">Some files could not be uploaded:</p>
            <ul className="list-disc space-y-1 pl-5">
              {fileErrors.map(({ fileName, message }) => (
                <li key={`${fileName}:${message}`}>
                  <span className="font-medium">{fileName}:</span> {message}
                </li>
              ))}
            </ul>
          </div>
        )}
        <DialogFooter>
          <Button
            onClick={handleAdd}
            disabled={images.length === 0 || addImages.isPending}
            className="inline-flex items-center gap-1"
          >
            <span>{fileErrors.length > 0 ? `Retry failed (${imageFiles.length})` : "Add"}</span>
            {addImages.isPending && (
              <LoaderCircle className="size-[1em] animate-spin" />
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
