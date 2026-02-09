-- Add missing columns to notes table
ALTER TABLE notes ADD COLUMN IF NOT EXISTS views INT DEFAULT 0;
ALTER TABLE notes ADD COLUMN IF NOT EXISTS shares INT DEFAULT 0;
ALTER TABLE notes ADD COLUMN IF NOT EXISTS likes INT DEFAULT 0;
ALTER TABLE notes ADD COLUMN IF NOT EXISTS earnings FLOAT DEFAULT 0;

-- Update existing records
UPDATE notes SET views = 0 WHERE views IS NULL;
UPDATE notes SET shares = 0 WHERE shares IS NULL;
UPDATE notes SET likes = 0 WHERE likes IS NULL;
UPDATE notes SET earnings = 0 WHERE earnings IS NULL;
