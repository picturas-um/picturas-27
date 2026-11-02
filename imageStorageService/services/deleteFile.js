const s3 = require("./s3Client");
const { BUCKET, objectKey } = require("./storage");

async function deleteFile(userId, projectId, stage, fileName) {
  const key = `${projectId}/${stage}/${fileName}`;

  try {
    const params = {
      Bucket: BUCKET,
      Key: objectKey(userId, projectId, stage, fileName),
    };

    await s3.deleteObject(params).promise();
    console.log(`Arquivo '${params.Key}' deletado do bucket '${BUCKET}'.`);
    return { message: "Arquivo deletado com sucesso!", key };
  } catch (error) {
    console.error("Erro ao deletar o arquivo:", error.message);
    throw error;
  }
}

module.exports = deleteFile;
