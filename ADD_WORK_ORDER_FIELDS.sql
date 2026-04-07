-- Add Work Order fields to contracts table
-- Run this SQL in your PostgreSQL database

-- Add WO type and number
ALTER TABLE contracts 
ADD COLUMN IF NOT EXISTS wo_type VARCHAR(20) NOT NULL DEFAULT 'outgoing' 
CHECK (wo_type IN ('incoming', 'outgoing'));

ALTER TABLE contracts 
ADD COLUMN IF NOT EXISTS wo_number VARCHAR(100) UNIQUE;

-- INCOMING WO Fields (Client → M2N)
ALTER TABLE contracts 
ADD COLUMN IF NOT EXISTS client_id INTEGER REFERENCES companies(id);

ALTER TABLE contracts 
ADD COLUMN IF NOT EXISTS client_po_number VARCHAR(100);

ALTER TABLE contracts 
ADD COLUMN IF NOT EXISTS client_payment_terms VARCHAR(255);

-- OUTGOING WO Fields (M2N → Subcontractor)
ALTER TABLE contracts 
ADD COLUMN IF NOT EXISTS contractor_category VARCHAR(50);
-- Values: 'civil', 'electrical', 'plumbing', 'hvac', 'fire_fighting', etc.

ALTER TABLE contracts 
ADD COLUMN IF NOT EXISTS work_scope_summary TEXT;

-- Financial Fields
ALTER TABLE contracts 
ADD COLUMN IF NOT EXISTS advance_percentage DECIMAL(5,2) NOT NULL DEFAULT 0;

ALTER TABLE contracts 
ADD COLUMN IF NOT EXISTS security_deposit DECIMAL(18,2) NOT NULL DEFAULT 0;

ALTER TABLE contracts 
ADD COLUMN IF NOT EXISTS billing_cycle VARCHAR(50) NOT NULL DEFAULT 'monthly' 
CHECK (billing_cycle IN ('milestone', 'fortnightly', 'monthly'));

-- Approval Workflow
ALTER TABLE contracts 
ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20) NOT NULL DEFAULT 'draft' 
CHECK (approval_status IN ('draft', 'pending', 'approved', 'rejected'));

ALTER TABLE contracts 
ADD COLUMN IF NOT EXISTS approved_by INTEGER REFERENCES users(id);

ALTER TABLE contracts 
ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP WITH TIME ZONE;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_contracts_wo_type ON contracts(wo_type);
CREATE INDEX IF NOT EXISTS idx_contracts_wo_number ON contracts(wo_number);
CREATE INDEX IF NOT EXISTS idx_contracts_client_id ON contracts(client_id);
CREATE INDEX IF NOT EXISTS idx_contracts_approval_status ON contracts(approval_status);

-- Add comment for documentation
COMMENT ON COLUMN contracts.wo_type IS 'incoming: Client → M2N, outgoing: M2N → Subcontractor';
COMMENT ON COLUMN contracts.contractor_category IS 'civil, electrical, plumbing, hvac, fire_fighting, etc.';
