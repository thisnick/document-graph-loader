from pydantic import BaseModel, Field
from typing import List, Dict, Any
from enum import Enum

class EntityType(Enum):
  ORGANIZATION = "Organization"
  INVOICE = "Invoice"
  PAYMENT_TERM = "PaymentTerm"
  DOCUMENT = "Document"
  CONTRACT = "Contract"
  SERVICE_ITEM = "ServiceItem"
  EMPLOYEE = "Employee"
  DEPARTMENT = "Department"
  COST_CENTER = "CostCenter"
  PAYROLL = "Payroll"
  PAYROLL_ITEM = "PayrollItem"

class RelationshipType(Enum):
  BILLED_TO = "BILLED_TO"
  BILLED_BY = "BILLED_BY"
  CONTAINS_ITEM = "CONTAINS_ITEM"
  HAS_PAYMENT_TERM = "HAS_PAYMENT_TERM"
  MENTIONED_IN = "MENTIONED_IN"
  PARTY_TO = "PARTY_TO"
  HAS_SERVICE = "HAS_SERVICE"
  ISSUES_PAYROLL = "ISSUES_PAYROLL"
  RECEIVES_PAYROLL = "RECEIVES_PAYROLL"
  HAS_PAYROLL_ITEM = "HAS_PAYROLL_ITEM"
  BELONGS_TO = "BELONGS_TO"
  IS_INSTANCE_OF = "IS_INSTANCE_OF"
  HAS_EMPLOYEE = "HAS_EMPLOYEE"

class EntityRef(BaseModel):
  """Reference to an entity in the document"""
  type: EntityType = Field(..., description="The type of entity being referenced (e.g., 'Organization', 'Invoice')")
  id: str = Field(..., description="Unique identifier for the referenced entity. For example: 'organization_1'")

class Relationship(BaseModel):
  """Represents a relationship between two entities"""
  from_: EntityRef = Field(
    alias='from',
    description="The source entity of the relationship. For example: {'type': 'Organization', 'id': 'organization_1'}"
  )
  to: EntityRef = Field(..., description="The target entity of the relationship. For example: {'type': 'Invoice', 'id': 'invoice_1'}")
  type: RelationshipType = Field(..., description="The type of relationship (e.g., 'BILLED_TO', 'CONTAINS_ITEM')")
  properties: Dict[str, Any] = Field(
    ...,
    description="Additional properties specific to this relationship (e.g., amount, date)"
  )

  model_config = {
    'populate_by_name': True
  }

class Entity(BaseModel):
  """Represents an entity extracted from the document"""
  type: EntityType = Field(..., description="The type of the entity (e.g., 'Organization', 'Invoice')")
  properties: Dict[str, Any] = Field(
    ...,
    description="Properties specific to this entity type (e.g., name, amount, date)"
  )

class DocumentExtraction(BaseModel):
  """Complete extraction result from a document"""
  entities: List[Entity] = Field(..., description="List of entities found in the document")
  relationships: List[Relationship] = Field(..., description="List of relationships between entities")
