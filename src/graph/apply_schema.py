from neo4j import GraphDatabase
import os
import logging
from typing import Optional
from dotenv import load_dotenv  # Add this import
import os  # Add this import

# Load environment variables at the start
load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchemaManager:
    def __init__(self, uri: str, username: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def close(self):
        self.driver.close()

    def read_schema_file(self, file_path: str) -> Optional[str]:
        """Read the schema file and return its contents."""
        try:
            with open(file_path, 'r') as file:
                return file.read()
        except FileNotFoundError:
            logger.error(f"Schema file not found at: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error reading schema file: {str(e)}")
            return None

    def apply_schema(self, cypher_script: str):
        """Execute the schema changes in the database."""
        with self.driver.session() as session:
            try:
                # Split the script into individual statements
                statements = [stmt.strip() for stmt in cypher_script.split(';') if stmt.strip()]

                for statement in statements:
                    if statement:  # Skip empty statements
                        logger.info(f"Executing: {statement[:100]}...")  # Log first 100 chars
                        session.run(statement)

                logger.info("Schema changes applied successfully")

            except Exception as e:
                logger.error(f"Error applying schema changes: {str(e)}")
                raise

def apply_schema():
    # Get database connection details from environment variables
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD")

    if not password:
        raise ValueError("NEO4J_PASSWORD environment variable must be set")

    # Get the schema file path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(current_dir, "schema.cypher")

    # Initialize the schema manager
    schema_manager = SchemaManager(uri, username, password)

    try:
        # Read the schema file
        schema_content = schema_manager.read_schema_file(schema_path)
        if not schema_content:
            raise ValueError("Failed to read schema file")

        # Apply the schema changes
        schema_manager.apply_schema(schema_content)

    except Exception as e:
        logger.error(f"Failed to apply schema: {str(e)}")
        raise

    finally:
        schema_manager.close()

if __name__ == "__main__":
    apply_schema()
