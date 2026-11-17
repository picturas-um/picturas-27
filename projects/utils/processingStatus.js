function createProcessingState({ token, runnerId, totalSteps, videoIds }) {
  return {
    token,
    status: "processing",
    runnerId: String(runnerId),
    totalSteps,
    completedMessages: [],
    videoProgress: Object.fromEntries(videoIds.map(id => [String(id), 0])),
    startedAt: new Date(),
    updatedAt: new Date(),
    error: null,
  };
}

function processingStatus(project, canCancel = false) {
  const run = project.processingState;
  if (!run || run.token == null) return { status: "idle", token: null, progress: 0, canCancel: false, projectVersion: project.version };
  const steps = (run.completedMessages || []).length +
    Object.values(run.videoProgress || {}).reduce((sum, percent) => sum + percent / 100, 0);
  const progress = run.status === "completed" ? 100 :
    Math.min(99, Math.max(0, Math.round(steps * 100 / Math.max(1, run.totalSteps))));
  return {
    token: run.token,
    status: run.status,
    progress,
    canCancel: canCancel && run.status === "processing",
    projectVersion: project.version,
    startedAt: run.startedAt,
    updatedAt: run.updatedAt,
    error: run.error || null,
  };
}

function createStatusHandler(Project, getCallerId) {
  return async (req, res) => {
    try {
      const project = req.sharedProject || await Project.getOne(req.params.user, req.params.project);
      if (!project) return res.status(404).jsonp("Project not found");
      const owner = String(getCallerId(req)) === String(project.user_id);
      if (!owner && !req.sharedPermission) return res.status(403).jsonp("Not allowed");
      res.set("Cache-Control", "no-store");
      return res.json(processingStatus(project, owner || req.sharedPermission === "edit"));
    } catch (error) {
      return res.status(500).jsonp("Unable to read processing status");
    }
  };
}

module.exports = { createProcessingState, processingStatus, createStatusHandler };
