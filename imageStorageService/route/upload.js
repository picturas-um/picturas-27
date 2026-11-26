const express = require("express");
const multer = require("multer");
const fs = require("fs");
const os = require("os");
const crypto = require("crypto");

const uploadImage = require("../services/uploadImage");
const allowedStages = require("../utils/stages");

const router = express.Router();

// Store uploads in temporary disk files instead of RAM.
const upload = multer({
  storage: multer.diskStorage({
    destination: os.tmpdir(),
    filename: (req, file, cb) => {
      cb(null, `${Date.now()}-${crypto.randomUUID()}`);
    },
  }),
});

router.post(
  "/:userId/:projectId/:stage",

  // Reject invalid stages before accepting a file.
  (req, res, next) => {
    if (!allowedStages.includes(req.params.stage)) {
      return res.status(400).json({
        error: "O estágio deve ser src, preview, preview_cache ou out.",
      });
    }
    next();
  },

  upload.single("file"),

  async (req, res) => {
    const { userId, projectId, stage } = req.params;

    if (!req.file) {
      return res.status(400).json({
        error: "No file uploaded",
      });
    }

    try {
      const result = await uploadImage(
        userId,
        projectId,
        req.file,
        stage
      );

      return res.status(201).json({
        message: "Imagem enviada com sucesso!",
        data: result,
      });
    } catch (error) {
      return res.status(500).json({
        error: error.message,
      });
    } finally {
      await fs.promises.unlink(req.file.path).catch((err) => {
        console.error(
          "[IMAGE-STORAGE] Temporary file cleanup failed:",
          err
        );
      });
    }
  }
);

module.exports = router;
