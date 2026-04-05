-- 004_remove_documents_remote_key.sql
-- Remove legacy remote-storage metadata from documents.

BEGIN;

ALTER TABLE documents
  DROP COLUMN IF EXISTS s3_key;

COMMIT;
