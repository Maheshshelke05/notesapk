-- Check notifications in database
SELECT * FROM notifications ORDER BY created_at DESC LIMIT 10;

-- Check buy requests
SELECT * FROM book_buy_requests ORDER BY created_at DESC LIMIT 10;

-- Check books
SELECT id, title, user_id FROM books ORDER BY created_at DESC LIMIT 5;
