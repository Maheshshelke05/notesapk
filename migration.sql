-- Add new columns to users table
ALTER TABLE users 
ADD COLUMN notes_uploaded_today INT DEFAULT 0,
ADD COLUMN notes_upload_reset_date DATETIME DEFAULT CURRENT_TIMESTAMP;

-- Add file_hash column to notes table
ALTER TABLE notes 
ADD COLUMN file_hash VARCHAR(64),
ADD INDEX idx_file_hash (file_hash);

-- Update existing notes with NULL hash (they won't be checked for duplicates)
UPDATE notes SET file_hash = NULL WHERE file_hash IS NULL;
