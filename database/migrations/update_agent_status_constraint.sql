-- Migration: Add WAITING and COORDINATING states to agent status constraint
-- Date: 2025-07-19
-- Purpose: Support recursive task decomposition coordination patterns

-- Drop the existing constraint
ALTER TABLE agents DROP CONSTRAINT IF EXISTS check_agents_status;

-- Add the new constraint with additional states for recursive coordination
ALTER TABLE agents ADD CONSTRAINT check_agents_status 
    CHECK (status IN ('spawned', 'active', 'waiting', 'coordinating', 'completed', 'failed', 'terminated'));

-- Verify the constraint was applied correctly
SELECT conname, consrc 
FROM pg_constraint 
WHERE conname = 'check_agents_status';

-- Show current agent status values (for verification)
SELECT DISTINCT status, COUNT(*) 
FROM agents 
GROUP BY status 
ORDER BY status;