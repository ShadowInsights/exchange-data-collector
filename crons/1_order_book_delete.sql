-- Creates schema with tables for cron jobs
CREATE EXTENSION PG_CRON;

-- Cron job to delete order_books every day at 1:00 pm
SELECT CRON.SCHEDULE('0 21 */1 * *','DELETE FROM public.order_books');