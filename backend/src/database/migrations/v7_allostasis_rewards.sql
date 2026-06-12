-- v7_allostasis_rewards.sql
-- Add category and last_purchased_at fields to the rewards table

ALTER TABLE rewards ADD COLUMN category VARCHAR(50) NOT NULL DEFAULT 'regular';
ALTER TABLE rewards ADD COLUMN last_purchased_at DATETIME;
