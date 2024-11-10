from typing import TypedDict
from swarm import Agent
from src.graph.extraction_schema import DocumentExtraction

class AgentContextVariables(TypedDict):
  document_path: str
  document_processed_at: str

OUTPUT_FORMAT = f"""
Output your findings as a list of triplets in the following schema:
{DocumentExtraction.model_json_schema()}

Foe example:
{{
  "entities": [
    {{
      "type": "Organization",
      "properties": {{
        "id": "organization_1",
        "name": "ServiceTech Solutions"
      }}
    }},
    {{
      "type": "Contract",
      "properties": {{
        "id": "contract_1",
        "description": "Master Services Agreement between ServiceTech Solutions and CitySpace Commercial Properties for various property management services.",
        "startDate": "2024-11-04",
        "type": "Service Agreement",
        "status": "Active"
      }}
    }}
  ],
  "relationships": [
    {{
      "from_": {{
        "type": "Organization",
        "id": "organization_1"
      }},
      "to": {{
        "type": "Employee",
        "id": "employee_1"
      }},
      "type": "PARTY_TO",
      "properties": {{
        "startDate": "2024-11-04",
        "role": "CLIENT"
      }}
    }},
    ...
  ]
}}

Output the JSON string only, nothing else.
"""

def invoice_parsing_agent_instructions(context_variables: AgentContextVariables):
  return f"""You analyze invoices to extract entities and their relationships according to the following schema:

ENTITIES TYPES:
- Organization (id*, name*)
- ServiceItem (id*, description*)
- Invoice (id*, description*, invoiceDate*, amount*)
- PaymentTerm (id*, description*, daysToPayment) // NET 30, EOM, etc.
- Document (id*, path*, processedAt*, description*, documentType*=invoice)

RELATIONSHIP TYPES:
1. Invoice Flow:
- (Invoice) BILLED_TO (Organization) (invoiceDate*, amount*)
- (Invoice) BILLED_BY (Organization) (invoiceDate*, amount*)
- (Invoice) CONTAINS_ITEM (ServiceItem) (quantity*, unit*, amount*)
- (Invoice) HAS_PAYMENT_TERM (PaymentTerm) (assignedDate*)

2. Document Flow:
- (Invoice) MENTIONED_IN (Document) (confidence*=1.0)

{OUTPUT_FORMAT}

Here are additional contexts:
- Document Path: {context_variables['document_path']}
- Document Processed At: {context_variables['document_processed_at']}

Ensure all required properties (marked with *) are included for each entity and relationship."""

def contract_parsing_agent_instructions(context_variables: AgentContextVariables):
  return f"""You analyze contracts to extract entities and their relationships according to the following schema:

ENTITIES TYPES:
- Organization (id*, name*)
- Contract (id*, description*, startDate*, type*, status*)
- ServiceItem (id*, description*)
- Document (id*, path*, processedAt*, description*, documentType*=contract)

RELATIONSHIP TYPES:
1. Contract Flow:
- (Organization) PARTY_TO (Contract) (startDate*, role*=[CLIENT/VENDOR])
- (Contract) HAS_SERVICE (ServiceItem) (unitPrice)

2. Document Flow:
- (Contract) MENTIONED_IN (Document) (confidence*=1.0)

{OUTPUT_FORMAT}

Here are additional contexts:
- Document Path: {context_variables['document_path']}
- Document Processed At: {context_variables['document_processed_at']}

Ensure all required properties (marked with *) are included for each entity and relationship."""

def paystub_parsing_agent_instructions(context_variables: AgentContextVariables):
  return f"""You analyze pay stubs to extract entities and their relationships according to the following schema:

ENTITIES TYPES:
- Organization (id*, name*, type*)
- Employee (id*, name*, role*)
- Department (id*, name*)
- Payroll (id*, description*, payPeriod*, netPay*)
- PayrollItem (id*, description*, amount*, type*)
- Document (id*, path*, processedAt*, description*, documentType*=paystub)

RELATIONSHIP TYPES:
1. Payroll Flow:
- (Organization) ISSUES_PAYROLL (Payroll) (issuedDate*)
- (Employee) RECEIVES_PAYROLL (Payroll) (receivedDate*)
- (Payroll) HAS_PAYROLL_ITEM (PayrollItem) (appliedDate*)

2. Organizational Structure:
- (Employee) BELONGS_TO (Department)
- (Organization) HAS_EMPLOYEE (Employee)

3. Document Flow:
- (Payroll) MENTIONED_IN (Document) (confidence*=1.0)

{OUTPUT_FORMAT}

Here are additional contexts:
- Document Path: {context_variables['document_path']}
- Document Processed At: {context_variables['document_processed_at']}

Ensure all required properties (marked with *) are included for each entity and relationship."""

invoice_parsing_agent = Agent(
  name="invoice_parsing_agent",
  model="gpt-4o-mini",
  instructions=invoice_parsing_agent_instructions
)

contract_parsing_agent = Agent(
  name="contract_parsing_agent",
  model="gpt-4o-mini",
  instructions=contract_parsing_agent_instructions
)

paystub_parsing_agent = Agent(
  name="paystub_parsing_agent",
  model="gpt-4o-mini",
  instructions=paystub_parsing_agent_instructions
)

def transfer_to_invoice_parsing_agent():
  """Transfer the document to the invoice parsing agent"""
  return invoice_parsing_agent

def transfer_to_contract_parsing_agent():
  """Transfer the document to the contract parsing agent"""
  return contract_parsing_agent

def transfer_to_paystub_parsing_agent():
  """Transfer the document to the pay stub parsing agent"""
  return paystub_parsing_agent

triage_agent = Agent(
  name="triage_agent",
  model="gpt-4o-mini",
  tool_choice="required",
  instructions="You will be given the content of a document, your job is determine which type of document it is and let the corresponding agent parse it.",
  functions=[
    transfer_to_invoice_parsing_agent,
    transfer_to_contract_parsing_agent,
    transfer_to_paystub_parsing_agent
  ]
)

def get_triage_agent():
  """Get the triage agent"""
  return triage_agent


__all__ = ["get_triage_agent"]
