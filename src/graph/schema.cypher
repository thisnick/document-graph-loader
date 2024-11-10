// Drop existing constraints and indexes first to avoid conflicts
// Note: In production, be careful with this as it might affect existing data
CALL apoc.schema.assert({},{},true);

// Wait a moment for the drops to complete
CALL apoc.util.sleep(1000);

//===============================
// 1. Uniqueness Constraints
//===============================
CREATE CONSTRAINT IF NOT EXISTS FOR (e:Employee) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (d:Department) REQUIRE d.name IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (cc:CostCenter) REQUIRE cc.code IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.path IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (si:ServiceItem) REQUIRE si.id IS UNIQUE;

// Add Organization constraint instead
CREATE CONSTRAINT IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE;

// Add Payroll and PayrollItem uniqueness constraints
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Payroll) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (pi:PayrollItem) REQUIRE pi.id IS UNIQUE;

//===============================
// 2. Property Existence Constraints
//===============================
CREATE CONSTRAINT IF NOT EXISTS FOR (e:Employee) REQUIRE e.name IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR (e:Employee) REQUIRE e.role IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR (e:Employee) REQUIRE e.embedding IS NOT NULL;

CREATE CONSTRAINT IF NOT EXISTS FOR (d:Department) REQUIRE d.embedding IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR (cc:CostCenter) REQUIRE cc.embedding IS NOT NULL;

CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.processedAt IS NOT NULL;

CREATE CONSTRAINT IF NOT EXISTS FOR (li:ServiceItem) REQUIRE li.description IS NOT NULL;

CREATE CONSTRAINT IF NOT EXISTS FOR (si:ServiceItem) REQUIRE si.description IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR (si:ServiceItem) REQUIRE si.embedding IS NOT NULL;

CREATE CONSTRAINT IF NOT EXISTS FOR (pt:PaymentTerm) REQUIRE pt.description IS NOT NULL;

CREATE CONSTRAINT IF NOT EXISTS FOR (i:Invoice) REQUIRE i.invoiceDate IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR (i:Invoice) REQUIRE i.amount IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR (i:Invoice) REQUIRE i.description IS NOT NULL;

CREATE CONSTRAINT IF NOT EXISTS FOR (o:Organization) REQUIRE o.name IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR (o:Organization) REQUIRE o.embedding IS NOT NULL;

// Add Payroll property constraints
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Payroll) REQUIRE p.payPeriod IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Payroll) REQUIRE p.netPay IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Payroll) REQUIRE p.description IS NOT NULL;

// Add PayrollItem property constraints
CREATE CONSTRAINT IF NOT EXISTS FOR (pi:PayrollItem) REQUIRE pi.amount IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR (pi:PayrollItem) REQUIRE pi.description IS NOT NULL;

//===============================
// 3. Node Indexes
//===============================
CREATE INDEX IF NOT EXISTS FOR (e:Employee) ON (e.name);
CREATE INDEX IF NOT EXISTS FOR (i:Invoice) ON (i.date);
CREATE INDEX IF NOT EXISTS FOR (c:Contract) ON (c.startDate);

// Vector indexes for embeddings
CREATE VECTOR INDEX IF NOT EXISTS FOR (e:Employee) ON (e.embedding);
CREATE VECTOR INDEX IF NOT EXISTS FOR (d:Department) ON (d.embedding);
CREATE VECTOR INDEX IF NOT EXISTS FOR (cc:CostCenter) ON (cc.embedding);
CREATE VECTOR INDEX IF NOT EXISTS FOR (o:Organization) ON (o.embedding);

// Date index
CREATE INDEX IF NOT EXISTS FOR (d:Document) ON (d.processedAt);
CREATE INDEX IF NOT EXISTS FOR (pt:PaymentTerm) ON (pt.daysToPayment);

// Add Organization index
CREATE INDEX IF NOT EXISTS FOR (o:Organization) ON (o.name);

// Add Payroll indexes
CREATE INDEX IF NOT EXISTS FOR (p:Payroll) ON (p.payPeriod);

//===============================
// 4. Relationship Property Constraints
//===============================
// Client Related
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:SERVES]-() REQUIRE r.startDate IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:SERVES]-() REQUIRE r.contractId IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:ACCOUNT_MANAGER]-() REQUIRE r.startDate IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:ACCOUNT_MANAGER]-() REQUIRE r.territory IS NOT NULL;

// Vendor Related
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:SUPPLIES]-() REQUIRE r.startDate IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:SUPPLIES]-() REQUIRE r.contractId IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:PROVIDES_SERVICE]-() REQUIRE r.serviceType IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:PROVIDES_SERVICE]-() REQUIRE r.startDate IS NOT NULL;

// Invoice Related
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:BILLED_TO]-() REQUIRE r.invoiceDate IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:BILLED_TO]-() REQUIRE r.amount IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:BILLED_BY]-() REQUIRE r.invoiceDate IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:BILLED_BY]-() REQUIRE r.amount IS NOT NULL;

// Service Related
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:CERTIFIED_FOR]-() REQUIRE r.certificationDate IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:CERTIFIED_FOR]-() REQUIRE r.expiryDate IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:ASSIGNED_TO]-() REQUIRE r.startDate IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:ASSIGNED_TO]-() REQUIRE r.role IS NOT NULL;

// Document Related
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:MENTIONED_IN]-() REQUIRE r.confidence IS NOT NULL;

// Line Item Related
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:CONTAINS_ITEM]-() REQUIRE r.quantity IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:CONTAINS_ITEM]-() REQUIRE r.unit IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:CONTAINS_ITEM]-() REQUIRE r.amount IS NOT NULL;

// Add new Contract relationship constraints
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:PARTY_TO]-() REQUIRE r.role IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:PARTY_TO]-() REQUIRE r.startDate IS NOT NULL;

// Add Payroll relationship constraints
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:ISSUES_PAYROLL]-() REQUIRE r.issuedDate IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:RECEIVES_PAYROLL]-() REQUIRE r.receivedDate IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:HAS_PAYROLL_ITEM]-() REQUIRE r.appliedDate IS NOT NULL;

//===============================
// 5. Relationship Property Indexes
//===============================
CREATE INDEX IF NOT EXISTS FOR ()-[r:BILLED_TO]-() ON (r.invoiceDate);
CREATE INDEX IF NOT EXISTS FOR ()-[r:BILLED_BY]-() ON (r.invoiceDate);
CREATE INDEX IF NOT EXISTS FOR ()-[r:MENTIONED_IN]-() ON (r.confidence);

// Add new relationship indexes
CREATE INDEX IF NOT EXISTS FOR ()-[r:PARTY_TO]-() ON (r.role);
CREATE INDEX IF NOT EXISTS FOR ()-[r:HAS_SERVICE]-() ON (r.unitPrice);

// Add Payroll relationship indexes
CREATE INDEX IF NOT EXISTS FOR ()-[r:ISSUES_PAYROLL]-() ON (r.issuedDate);
CREATE INDEX IF NOT EXISTS FOR ()-[r:RECEIVES_PAYROLL]-() ON (r.receivedDate);
