from datetime import datetime
import hashlib
import json
import mimetypes
import os
import string
import time
from pathlib import Path
from typing import Any, Dict, List, TypedDict

import numpy as np
from pydantic import ValidationError
import shortuuid
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from swarm import Swarm

from ..lib.llama_parse import (
  SUPPORTED_MIME_TYPES,
  LlamaParseClient,
  MarkdownJobResult
)
from .document_entity_extractor_agent import (
  get_triage_agent,
  AgentContextVariables
)
from .extraction_schema import DocumentExtraction, EntityType


# Add this type definition before the DocumentLoader class
class ParsedContent(TypedDict):
  file_name: str
  markdown: str

ENTITY_RESOLUTION_TYPES = [
  EntityType.ORGANIZATION,
  EntityType.EMPLOYEE,
  EntityType.DEPARTMENT,
  EntityType.COST_CENTER,
  EntityType.SERVICE_ITEM,
]

class DocumentLoader:
  def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str, llama_parse_api_key: str):
    """Initialize connections to Neo4j and LlamaParse"""
    self.neo4j_uri = neo4j_uri
    self.neo4j_user = neo4j_user
    self.neo4j_password = neo4j_password
    self.llama_parse_api_key = llama_parse_api_key
    self.llama_parse_client = LlamaParseClient(llama_parse_api_key)
    self.neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    # Print all variables
    print(f"Neo4j URI: {self.neo4j_uri}")
    print(f"Neo4j User: {self.neo4j_user}")
    print(f"Neo4j Password: {'*' * len(self.neo4j_password)}")  # Masked for security
    print(f"LlamaParse API Key: {'*' * len(self.llama_parse_api_key)}")  # Masked for security
    print(f"LlamaParse Client: {self.llama_parse_client}")
    print(f"Neo4j Driver: {self.neo4j_driver}")



  def process_directory(self, directory_path: str) -> None:
    """Iterate through all files in the directory and process each"""
    print(f"Processing directory: {directory_path}")
    for file_path in Path(directory_path).glob('**/*'):
      if not self.check_file_supported(file_path):
        print(f"Skipping unsupported file: {file_path}")
        continue
      parse_result = self.parse_document(str(file_path))
      parsed_content = {
        'file_name': str(file_path),
        'markdown': parse_result['markdown']
      }
      document_extraction = self.extract_triples(parsed_content)
      updated_extraction = self.generate_embedding(document_extraction)
      resolved_extraction = self.resolve_and_update_entities(updated_extraction)
      self.add_triples_to_graph(resolved_extraction, str(file_path))

  def check_file_supported(self, file_path: str) -> bool:
    """Check if the file is supported by LlamaParse"""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type and mime_type in SUPPORTED_MIME_TYPES

  def parse_document(self, file_path: str) -> MarkdownJobResult:
    """Send document content to LlamaParse and get structured content with caching

    Args:
      file_path: Path to the document file as a string

    Returns:
      Parsed document structure from LlamaParse
    """
    print(f"Parsing document: {file_path}")
    path = Path(file_path)
    content = path.read_bytes()

    # Generate hash of content for cache key
    content_hash = hashlib.md5(content).hexdigest()

    # Create cache file path
    cache_path = Path('.parsed') / f"{file_path}.{content_hash}.md"

    # Ensure cache directory exists
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if cached version exists
    if cache_path.exists():
      print(f"Loading cached version of {file_path}")
      with open(cache_path, 'r') as f:
        return json.loads(f.read())

    # If not cached, process normally
    print(f"Processing {file_path}")
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type or mime_type not in SUPPORTED_MIME_TYPES:
      raise ValueError(f"Unsupported file type: {file_path}")

    start_time = time.time()
    response = self.llama_parse_client.process_file(content, file_path, mime_type)
    end_time = time.time()
    print(f"Processed {file_path} in {end_time - start_time} seconds")

    # Cache the response
    with open(cache_path, 'w') as f:
      json.dump(response, f)

    return response

  def extract_triples(self, parsed_content: ParsedContent) -> DocumentExtraction:
    """Use LLM to extract subject-predicate-object triples from parsed content.

    Args:
      parsed_content: Dictionary containing the parsed document structure including:
        - file_name: Name of the source file
        - markdown: The markdown content of the file

    Returns:
      Parsed triples as a JSON string
    """
    # Generate hash of content for cache key
    content_hash = hashlib.md5(parsed_content['markdown'].encode()).hexdigest()

    # Create cache file path
    cache_path = Path('.extracted') / f"{parsed_content['file_name']}.{content_hash}.json"

    # Ensure cache directory exists
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if cached version exists
    if cache_path.exists():
      print(f"Loading cached triples for {parsed_content['file_name']}")
      with open(cache_path, 'r') as f:
        cached_data = json.loads(f.read())
        return DocumentExtraction.model_validate(cached_data)

    # If not cached, process normally
    print(f"Extracting triples from {parsed_content['file_name']}")

    context_variables = AgentContextVariables(
      document_path=parsed_content['file_name'],
      document_processed_at=datetime.now().isoformat()
    )

    swarm = Swarm()

    response = swarm.run(
      agent=get_triage_agent(),
      context_variables=context_variables,
      messages=[{
      'role': 'user',
      'content': f"Here is the content of the document: {parsed_content['markdown']}"
      }]
    )
    results = response.messages[-1]["content"]
    json_results = json.loads(results)

    # Parse directly into DocumentExtraction using Pydantic
    try:
      document_extraction = DocumentExtraction.model_validate(json_results)
    except ValidationError as e:
      print(f"Error validating extraction: {json_results}")
      raise e

    # Cache the response using native Pydantic JSON serialization
    with open(cache_path, 'w') as f:
      f.write(document_extraction.model_dump_json())

    return document_extraction

  def generate_embedding(self, extraction: DocumentExtraction) -> DocumentExtraction:
    """Set embedding property for each entity using SentenceTransformer with caching.

    Args:
        extraction: DocumentExtraction object containing entities to embed
    """
    # Generate hash of the extraction for cache key
    extraction_json = extraction.model_dump_json()
    content_hash = hashlib.md5(extraction_json.encode()).hexdigest()

    # Create cache file path
    cache_path = Path('.embeddings') / f"{content_hash}.json"

    # Ensure cache directory exists
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if cached version exists
    if cache_path.exists():
        print("Loading cached embeddings")
        with open(cache_path, 'r') as f:
            cached_data = json.loads(f.read())
            return DocumentExtraction.model_validate(cached_data)

    # If not cached, process normally
    print("Generating new embeddings")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    updated_extraction = extraction.model_copy()

    # Generate embeddings for each entity's name
    for entity in updated_extraction.entities:
      if entity.type in ENTITY_RESOLUTION_TYPES:
        text_to_embed = f"{entity.properties.get('name') or entity.properties.get('description')} : {entity.type}"
        embedding = model.encode(text_to_embed, convert_to_numpy=True)
        entity.properties['embedding'] = embedding.tolist()

    # Cache the updated extraction
    with open(cache_path, 'w') as f:
        f.write(updated_extraction.model_dump_json())

    return updated_extraction

  def resolve_and_update_entities(self, extraction: DocumentExtraction) -> DocumentExtraction:
    """Connect to neo4j, find entities based on embedding, and resolve entities based on cosine distance.

    For each entity in the extraction, this method:
    1. Finds similar entities in Neo4j using embedding similarity
    2. If a similar entity is found above threshold, updates the ID to match
    3. Updates all relationships referencing the old entity ID
    4. Returns updated DocumentExtraction with resolved entities

    Args:
      extraction: DocumentExtraction object containing entities to resolve

    Returns:
      Updated DocumentExtraction with resolved entity IDs
    """
    print("Resolving entities with Neo4j")
    updated_extraction = extraction.model_copy()
    id_mapping = {}  # Store old_id -> new_id mappings

    with self.neo4j_driver.session() as session:
      for entity in updated_extraction.entities:
        # Special case for Document entities - look up by path
        if entity.type == EntityType.DOCUMENT:
          query = """
          MATCH (e:Document {path: $path})
          RETURN e.id AS id
          """
          result = session.run(
            query,
            path=entity.properties.get('path')
          )
          match = result.single()
          original_id = entity.properties.get('id')
          if match:
            entity.properties['id'] = match['id']
            if original_id:
              id_mapping[f"{entity.type}_{original_id}"] = match['id']
            continue

        # Regular handling for entities without embedding
        if 'embedding' not in entity.properties:
          short_guid = shortuuid.uuid()
          original_id = entity.properties.get('id')
          entity.properties['id'] = short_guid
          if original_id:
            id_mapping[f"{entity.type}_{original_id}"] = short_guid
          continue

        # Store original ID before potential update
        original_id = entity.properties.get('id')
        typed_original_id = f"{entity.type}_{original_id}" if original_id else None

        # Query Neo4j for similar entities using vector similarity
        query = f"""
        MATCH (e:`{entity.type.value}`)
        WITH e, vector.similarity.cosine(e.embedding, $embedding) AS similarity
        WHERE similarity > 0.95
        RETURN e.id AS id, e.name AS name, similarity
        ORDER BY similarity DESC
        LIMIT 1
        """

        result = session.run(
          query,
          embedding=entity.properties['embedding']
        )

        match = result.single()
        if match:
          # Update entity ID to match existing entity, ensuring type prefix
          matched_id = match['id']
          entity.properties['id'] = matched_id
          if typed_original_id:
            id_mapping[typed_original_id] = matched_id
        else:
          # No match found, generate new type-prefixed ID
          new_id = shortuuid.uuid()
          entity.properties['id'] = new_id
          if typed_original_id:
            id_mapping[typed_original_id] = new_id

      # Update relationship entity references using the id_mapping
      for relationship in updated_extraction.relationships:
        from_typed_id = f"{relationship.from_.type}_{relationship.from_.id}"
        to_typed_id = f"{relationship.to.type}_{relationship.to.id}"

        if from_typed_id in id_mapping:
          relationship.from_.id = id_mapping[from_typed_id]
        if to_typed_id in id_mapping:
          relationship.to.id = id_mapping[to_typed_id]

    return updated_extraction

  def add_triples_to_graph(self, extraction: DocumentExtraction, file_path: str) -> None:
    """Add entities and relationships from DocumentExtraction to Neo4j.
    Skips processing if document was already processed.

    Args:
        extraction: DocumentExtraction object containing entities and relationships
    """
    with self.neo4j_driver.session() as session:
        # Check if document was already processed and create if not exists
        check_query = """
        MATCH (d:Document {path: $path})
        RETURN d.processedAt
        """
        result = session.run(check_query, path=file_path)
        if result.single():
            print(f"Document already processed: {file_path}")
            return

        # Create new document node if it doesn't exist
        create_doc_query = """
        MERGE (d:Document {path: $path})
        ON CREATE SET
            d.processedAt = datetime(),
            d.id = $id
        """
        session.run(
            create_doc_query,
            path=file_path,
            id=shortuuid.uuid()
        )

        # First, create or update all entities
        for entity in extraction.entities:
          try:
            # Create entity with properties, merging on ID if exists
            query = f"""
            MERGE (e:`{entity.type.value}` {{id: $id}})
            SET e += $properties
            """

            # Convert numpy arrays to lists if present
            properties = {k: v.tolist() if isinstance(v, np.ndarray) else v
                        for k, v in entity.properties.items()}

            print(f"Creating or updating entity: {entity.type.value} with ID: {entity.properties['id']}")

            session.run(
                query,
                id=entity.properties['id'],
              properties=properties or {}
            )
          except Exception as e:
            print(f"Error creating or updating entity: {entity.type.value} with ID: {entity.properties['id']}")
            raise e

        # Then create all relationships
        for rel in extraction.relationships:
          try:
            from_type = rel.from_.type.value
            to_type = rel.to.type.value
            rel_type = rel.type.value
            # Create relationship between entities, using the type as relationship type
            query = f"""
            MATCH (from:`{from_type}` {{id: $from_id}})
            MATCH (to:`{to_type}` {{id: $to_id}})
            MERGE (from)-[r:`{rel_type}`]->(to)
            SET r += $properties
            """

            print(f"Creating relationship: {rel_type} between {from_type} and {to_type}")
            # Clean relationship type to be Neo4j compatible
            session.run(
                query,
                from_id=rel.from_.id,
                to_id=rel.to.id,
                properties=rel.properties or {}
            )
          except Exception as e:
            print(f"Error creating relationship: {rel_type} between {from_type} and {to_type}")
            raise e

def test_load_contracts():
  import dotenv
  dotenv.load_dotenv()
  neo4j_uri = os.getenv('NEO4J_URI')
  neo4j_user = os.getenv('NEO4J_USERNAME')
  neo4j_password = os.getenv('NEO4J_PASSWORD')
  llama_parse_api_key = os.getenv('LLAMA_PARSE_API_KEY')
  loader = DocumentLoader(neo4j_uri, neo4j_user, neo4j_password, llama_parse_api_key)
  loader.process_directory('company_documents')

if __name__ == "__main__":
  test_load_contracts()
