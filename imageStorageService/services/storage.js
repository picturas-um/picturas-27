const s3 = require("./s3Client");

// All files live in one shared bucket, separated by key prefix:
//   users/<userId>/projects/<projectId>/<stage>/<fileName>
// A bucket per user does not scale on SeaweedFS: every bucket needs volumes of
// its own, so uploads started failing for new users after the first few.
const BUCKET = process.env.S3_BUCKET || "picturas";

function objectKey(userId, projectId, stage, fileName) {
  return `users/${userId}/projects/${projectId}/${stage}/${fileName}`;
}

// Create the bucket on first use. The promise is cached so concurrent uploads
// share one check; on failure it is cleared so the next request retries.
let bucketReady = null;

function ensureBucket() {
  if (!bucketReady) {
    bucketReady = (async () => {
      try {
        await s3.headBucket({ Bucket: BUCKET }).promise();
      } catch (error) {
        if (error.statusCode !== 404) throw error;
        try {
          await s3.createBucket({ Bucket: BUCKET }).promise();
          console.log(`Bucket '${BUCKET}' created.`);
        } catch (createError) {
          if (createError.code !== "BucketAlreadyOwnedByYou" && createError.code !== "BucketAlreadyExists") {
            throw createError;
          }
        }
      }
    })().catch((error) => {
      bucketReady = null;
      throw error;
    });
  }
  return bucketReady;
}

module.exports = { BUCKET, objectKey, ensureBucket };
