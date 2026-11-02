const s3 = require("./s3Client");
const { BUCKET, objectKey } = require("./storage");

async function copyFile(userId, projectId, fromStage, toStage, fileName) {
  const sourceKey = `${projectId}/${fromStage}/${fileName}`;
  const destKey   = `${projectId}/${toStage}/${fileName}`;

  try {
    await s3.copyObject({
      Bucket: BUCKET,
      CopySource: `/${BUCKET}/${objectKey(userId, projectId, fromStage, fileName)}`,
      Key: objectKey(userId, projectId, toStage, fileName),
    }).promise();

    return { from: sourceKey, to: destKey };
  } catch (error) {
    console.error("Erro ao copiar ficheiro:", error.message);
    throw error;
  }
}

module.exports = copyFile;
