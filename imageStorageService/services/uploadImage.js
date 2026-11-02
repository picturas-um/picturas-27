const s3 = require("./s3Client");
const { BUCKET, objectKey, ensureBucket } = require("./storage");
const { v4: uuidv4 } = require("uuid");

async function uploadImage(userId, projectId, file, stage) {
  await ensureBucket();

  // imageKey is what callers store and send back (<projectId>/<stage>/<file>);
  // the user prefix is added only for the object's key in the shared bucket.
  const fileName = `${uuidv4()}.${file.mimetype.split("/")[1]}`;
  const imageKey = `${projectId}/${stage}/${fileName}`;
  const params = {
    Bucket: BUCKET,
    Key: objectKey(userId, projectId, stage, fileName),
    Body: file.buffer,
    ContentType: file.mimetype,
  };

  try {
    const data = await s3.upload(params).promise();
    return { imageKey, location: data.Location };
  } catch (error) {
    console.error("Erro ao enviar imagem:", error.message);
    throw error;
  }
}

module.exports = uploadImage;
