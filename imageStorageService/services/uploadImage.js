const fs = require("fs");
const s3 = require("./s3Client");
const { BUCKET, objectKey, ensureBucket } = require("./storage");
const { v4: uuidv4 } = require("uuid");

async function uploadImage(userId, projectId, file, stage) {
  await ensureBucket();

  // Preserve the existing object naming and storage structure.
  const fileName = `${uuidv4()}.${file.mimetype.split("/")[1]}`;
  const imageKey = `${projectId}/${stage}/${fileName}`;

  const fileStream = fs.createReadStream(file.path);

  const params = {
    Bucket: BUCKET,
    Key: objectKey(userId, projectId, stage, fileName),
    Body: fileStream,
    ContentType: file.mimetype,
  };

  try {
    const data = await s3.upload(params).promise();

    return {
      imageKey,
      location: data.Location,
    };
  } catch (error) {
    console.error("Erro ao enviar imagem:", error.message);
    throw error;
  } finally {
    fileStream.destroy();
  }
}

module.exports = uploadImage;
