const express = require("express");
const {
  getPresignedUrlDocker,
  getPresignedUrlHost,
} = require("../services/getPresignedUrl");

const router = express.Router();

router.get("/docker/:userId/:projectId/:stage/:imageName", async (req, res) => {
  const { userId, projectId, stage, imageName } = req.params;

  const allowedStages = require("../utils/stages");

  if (!allowedStages.includes(stage)) {
    return res.status(400).json({
      error: "O estágio deve ser src, preview, preview_cache ou out.",
    });
  }


  try {
    const url = await getPresignedUrlDocker(
      userId,
      projectId,
      stage,
      imageName,
    );
    res.status(200).json({ url });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.get("/host/:userId/:projectId/:stage/:imageName", async (req, res) => {
  const { userId, projectId, stage, imageName } = req.params;

  const allowedStages = require("../utils/stages");

  if (!allowedStages.includes(stage)) {
    return res.status(400).json({
      error: "O estágio deve ser src, preview, preview_cache ou out.",
    });
  }


  try {
    const url = await getPresignedUrlHost(userId, projectId, stage, imageName);
    
    res.status(200).json({ url });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
