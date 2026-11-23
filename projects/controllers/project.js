var Project = require("../models/project");
const ProjectModel = require("../models/project");

// DELETE condicional por versão
module.exports.deleteIfVersion = async (user_id, project_id, expectedVersion) => {
  const res = await Project.deleteOne({
    user_id: user_id,
    _id: project_id,
    version: expectedVersion,
  });

  return res.deletedCount === 1;
};

// Adicionar share link (atómico + versão)
module.exports.addShareLinkIfVersion = async (
  user_id,
  project_id,
  newLink,
  expectedVersion
) => {
  return await Project.findOneAndUpdate(
    { user_id: user_id, _id: project_id, version: expectedVersion },
    { $push: { sharedLinks: newLink }, $inc: { version: 1 } },
    { new: true }
  ).exec();
};

// Revogar share link (atómico + versão)
module.exports.revokeShareLinkIfVersion = async (
  user_id,
  project_id,
  shareId,
  expectedVersion
) => {
  return await Project.findOneAndUpdate(
    {
      user_id: user_id,
      _id: project_id,
      version: expectedVersion,
      "sharedLinks.id": shareId,
    },
    { $set: { "sharedLinks.$.revoked": true }, $inc: { version: 1 } },
    { new: true }
  ).exec();
};

module.exports.getAll = async (user_id) => {
  return await Project.find({ user_id: user_id }).sort({ _id: 1 }).exec();
};

module.exports.getOne = async (user_id, project_id) => {
  return await Project.findOne({ user_id: user_id, _id: project_id }).exec();
};

module.exports.create = async (project) => {
  return await Project.create(project);
};

module.exports.update = (user_id, project_id, project) => {
  return Project.updateOne({ user_id: user_id, _id: project_id }, project);
};

module.exports.delete = (user_id, project_id) => {
  return Project.deleteOne({ user_id: user_id, _id: project_id });
};

// Devolve o projeto que contém este shareId
module.exports.getOneByShareId = (shareId) =>
  Project.findOne({ "sharedLinks.id": shareId }).exec();

module.exports.updateIfVersion = async (user_id, project_id, project, expectedVersion, options = {}) => {
  const raw = project.toObject ? project.toObject() : project;

  // remove campos que não se quer "setar"
  const { _id, user_id: _uid, version, __v, sharedLinks, processingState, ...rest } = raw;

  // Ordinary project edits must not overwrite progress written by a worker.
  if (options.processingState) rest.processingState = options.processingState;
  const filter = { user_id, _id: project_id, version: expectedVersion };
  if (options.activeToken !== undefined) filter.activeToken = options.activeToken;
  if (options.requireProcessing) filter["processingState.status"] = "processing";

  return await Project.findOneAndUpdate(
    filter,
    { $set: rest, $inc: { version: 1 } },
    { new: true } // devolve documento já com versão incrementada
  ).exec();
};

module.exports.updateRaw = async (user_id, project_id, update) => {
  return await ProjectModel.updateOne(
    { user_id, _id: project_id },
    update
  ).exec();
};


// Commit only if cancellation/new processing has not changed the active run.
module.exports.commitRunIfActive = async (user_id, project_id, token, tools, tracked = false) => {
  const filter = { user_id, _id: project_id, activeToken: token };
  if (tracked) {
    filter["processingState.token"] = token;
    filter["processingState.status"] = "processing";
  }
  const fields = { committedToken: token, resultsToken: token, committedTools: tools };
  if (tracked) {
    fields["processingState.status"] = "completed";
    fields["processingState.updatedAt"] = new Date();
  }
  return Project.findOneAndUpdate(
    filter,
    { $set: fields },
    { new: true }
  ).exec();
};

module.exports.recordProcessingProgress = (user_id, project_id, token, { messageId, videoId, percent } = {}) => {
  const update = { $set: { "processingState.updatedAt": new Date() } };
  if (messageId) update.$addToSet = { "processingState.completedMessages": messageId };
  if (videoId && Number.isFinite(percent)) {
    update.$max = { [`processingState.videoProgress.${videoId}`]: Math.max(0, Math.min(100, percent)) };
  }
  return Project.updateOne({ user_id, _id: project_id, activeToken: token,
    "processingState.token": token, "processingState.status": "processing" }, update).exec();
};

module.exports.failProcessing = (user_id, project_id, token, error) =>
  Project.updateOne({ user_id, _id: project_id, activeToken: token,
    "processingState.token": token, "processingState.status": "processing" }, {
    $set: { "processingState.status": "failed", "processingState.error": error,
      "processingState.updatedAt": new Date() },
  }).exec();
