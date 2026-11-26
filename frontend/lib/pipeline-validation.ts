// Checks a pipeline the same way the backend does when it is run, so the UI can
// point out the invalid steps before the user presses Preview/Apply.
//
// Mirrors projects/utils/video.js (unsupportedVideoTools, validateFrameExtraction)
// and the "only video effects" check in projects/routes/projects.js.
import { getToolInfo, getToolLabel } from "@/lib/tool-registry";

export interface PipelineStep {
  _id: string;
  procedure: string;
  position?: number;
}

export interface StepIssue {
  /** Very short text: it has to fit in the narrow tools bar. */
  short: string;
  /** Full explanation, for tooltips and messages. */
  detail: string;
}

export interface PipelineValidation {
  /** First problem of each invalid step, by step id. */
  stepIssues: Record<string, StepIssue>;
  /** Every distinct problem, in plain words. Empty when the pipeline is valid. */
  problems: string[];
  /** True when the backend would accept the pipeline. */
  isValid: boolean;
}

export function validatePipeline(
  steps: PipelineStep[],
  context: { hasVideos: boolean },
): PipelineValidation {
  const ordered = [...steps].sort((a, b) => (a.position ?? 0) - (b.position ?? 0));
  const stepIssues: Record<string, StepIssue> = {};
  const problems: string[] = [];

  const flag = (step: PipelineStep, issue: StepIssue) => {
    if (!stepIssues[step._id]) stepIssues[step._id] = issue;
    if (!problems.includes(issue.detail)) problems.push(issue.detail);
  };

  // 1. Steps that must be the last one (extract frames): only one, and at the end
  const lastOnly = new Set(
    ordered.filter((s) => getToolInfo(s.procedure)?.mustBeLast).map((s) => s.procedure),
  );
  lastOnly.forEach((procedure) => {
    const label = getToolLabel(procedure);
    const group = ordered.filter((s) => s.procedure === procedure);
    if (group.length > 1) {
      group.slice(1).forEach((s) =>
        flag(s, {
          short: "Only one allowed",
          detail: `Only one "${label}" step is allowed in a pipeline.`,
        }),
      );
    } else if (ordered[ordered.length - 1] !== group[0]) {
      flag(group[0], {
        short: "Must be last",
        detail: `"${label}" must be the last step of the pipeline.`,
      });
    }
  });

  // 2. Image-only tools cannot run in a project that has videos
  if (context.hasVideos) {
    ordered.forEach((s) => {
      if (getToolInfo(s.procedure)?.media === "image") {
        flag(s, {
          short: "Not for videos",
          detail: `"${getToolLabel(s.procedure)}" works on images only, so it cannot be applied while the project has videos. Remove it from the pipeline, or remove the videos.`,
        });
      }
    });
  }

  // 3. Without videos, a pipeline made only of video effects has nothing to run on
  if (
    !context.hasVideos &&
    ordered.length > 0 &&
    ordered.every((s) => getToolInfo(s.procedure)?.media === "video")
  ) {
    ordered.forEach((s) =>
      flag(s, {
        short: "Needs a video",
        detail: `"${getToolLabel(s.procedure)}" works on videos only and this project has no videos. Add a video, or remove it from the pipeline.`,
      }),
    );
  }

  return { stepIssues, problems, isValid: problems.length === 0 };
}
