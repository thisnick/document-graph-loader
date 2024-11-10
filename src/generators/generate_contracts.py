import json
from pathlib import Path
import jinja2
from fpdf import FPDF
from datetime import datetime
import openai
from dotenv import load_dotenv  # Add this import
import os  # Add this import

# Load environment variables at the start
load_dotenv()


class ContractGenerator:
  def __init__(self, template_dir="templates"):
    self.llm = openai.OpenAI()  # or anthropic.Client()
    self.template_loader = jinja2.FileSystemLoader(template_dir)
    self.template_env = jinja2.Environment(loader=self.template_loader)

  def load_client_data(self, client_id):
    # Load and combine relevant data for the client
    data = {
      "client": self._load_client_portfolio(client_id),
      "crm": self._load_crm_profile(client_id),
      "pricing": self._load_pricing_structure(),
    }
    return data

  def _load_client_portfolio(self, client_id):
    with open("seed_data/client_portfolio.json", "r") as f:
      portfolio = json.load(f)
      return next(
        (
          client
          for client in portfolio["clients"]
          if client["id"] == client_id
        ),
        None,
      )

  def _load_crm_profile(self, client_id):
    with open("seed_data/customer_crm_profiles.json", "r") as f:
      profiles = json.load(f)
      return next(
        (
          profile
          for profile in profiles["clientRelationships"]
          if profile["clientId"] == client_id
        ),
        None,
      )

  def _load_pricing_structure(self):
    with open("seed_data/revenue_and_pricing_structure.json", "r") as f:
      return json.load(f)

  def generate_contract_content(self, client_data):
    print(f"Generating contracts for: {client_data['client']['company']['name']}")

    # Gather all contract sections
    company_profile = self._load_company_profile()
    context_sections = self._gather_context_sections(client_data)

    # Build the prompt
    prompt = self._build_contract_prompt(client_data, company_profile, context_sections)

    # Get response from LLM
    return self._get_llm_response(prompt)

  def _load_company_profile(self):
    with open("seed_data/company.txt", "r") as f:
        return f.read()

  def _gather_context_sections(self, client_data):
    return {
        'client_info': self._extract_client_info(client_data),
        'relationship': self._get_relationship_context(client_data),
        'address': self._format_address_info(client_data),
        'contacts': self._format_key_contacts(client_data),
        'financial': self._format_financial_details(client_data),
        'sla': self._format_sla_details(client_data),
        'pricing': self._format_pricing_details(client_data),
        'timeline': self._format_timeline_details(client_data),
        'communication': self._format_communication_details(client_data)
    }

  def _extract_client_info(self, client_data):
    return {
        'challenges': client_data["client"]["businessProfile"]["mainChallenges"],
        'culture': client_data["client"]["businessProfile"]["culture"],
        'characteristics': client_data["client"]["businessProfile"]["uniqueCharacteristics"],
        'service_reqs': client_data["client"]["serviceRequirements"]
    }

  def _get_relationship_context(self, client_data):
    if "salesHistory" not in client_data["crm"]:
        return ""

    sales_history = client_data["crm"]["salesHistory"]
    return f"""
    Relationship Context:
    - Initial Contact: {sales_history['initialContactDate']}
    - Sales Cycle Duration: {sales_history['salesCycleDuration']}
    - Decision Process: {[stage['notes'] for stage in sales_history['decisionMakingProcess']]}
    - Key Winning Factors: {sales_history['decisionMakingProcess'][-1]['notes']}
    """

  def _format_address_info(self, client_data):
    return f"""
    Client Addresses:
    Headquarters: {client_data['client']['company']['address']['headquarters']}
    Additional Locations: {', '.join(client_data['client']['company']['address'].get('warehouses', []) or
                                   client_data['client']['company']['address'].get('serviceLocations', []) or
                                   client_data['client']['company']['address'].get('facilities', []) or
                                   client_data['client']['company']['address'].get('locations', []))}
    """

  def _format_key_contacts(self, client_data):
    return f"""
    Key Contacts:
    {chr(10).join([f"- {contact['name']} ({contact['role']}): {contact['preferences']}"
                   for contact in client_data['client']['keyContacts']])}
    """

  def _format_financial_details(self, client_data):
    return f"""
    Financial Details:
    - Contract Value: {client_data['client']['company']['contractValue']}
    - Payment Terms: {client_data['client']['businessProfile']['paymentTerms']}
    - Cash Flow Situation: {client_data['client']['businessProfile']['cashFlowSituation']}
    """

  def _format_sla_details(self, client_data):
    return f"""
    Service Level Requirements:
    - Response Time Performance: {client_data['crm']['issues']['slaPerformance']['responseTime']}
    - Resolution Time Performance: {client_data['crm']['issues']['slaPerformance']['resolutionTime']}
    - Customer Satisfaction Target: {client_data['crm']['issues']['slaPerformance']['customerSatisfaction']}
    - Average Resolution Time: {client_data['crm']['issues']['summary']['averageResolutionTime']}
    """

  def _format_pricing_details(self, client_data):
    return f"""
    Pricing Structure:
    - Contract Value: {client_data['crm']['contractDetails']['final']['actualValue']}
    - Revenue Streams:
        * Regular Services: {client_data['crm']['financialMetrics']['revenueStreams']['regularServices']['amount']}
        * Emergency Services: {client_data['crm']['financialMetrics']['revenueStreams']['emergencyServices']['amount']}
        * Special Projects: {client_data['crm']['financialMetrics']['revenueStreams']['specialProjects']['amount']}
    - Cost Breakdown:
        * Labor: {client_data['crm']['financialMetrics']['costBreakdown']['labor']['amount']} ({client_data['crm']['financialMetrics']['costBreakdown']['labor']['percentage']})
        * Materials: {client_data['crm']['financialMetrics']['costBreakdown']['materials']['amount']} ({client_data['crm']['financialMetrics']['costBreakdown']['materials']['percentage']})
        * Overhead: {client_data['crm']['financialMetrics']['costBreakdown']['overhead']['amount']} ({client_data['crm']['financialMetrics']['costBreakdown']['overhead']['percentage']})
    """

  def _format_timeline_details(self, client_data):
    return f"""
    Key Dates and Timeline:
    - Contract Start Date: {client_data['crm']['relationshipStatus']['customerSince']}
    - Last Review Date: {client_data['crm']['relationshipStatus']['lastReviewDate']}
    - Regular Review Schedule: {client_data['crm']['interactions']['summary']['interactionFrequency']}
    - Next Scheduled Review: {client_data['crm']['interactions']['summary']['nextScheduledMeeting']}
    """

  def _format_communication_details(self, client_data):
    return f"""
    Communication Requirements:
    - Preferred Channels: {', '.join(client_data['crm']['interactions']['summary']['preferredChannels'])}
    - Key Meeting Types: {', '.join(client_data['crm']['interactions']['keyInteractionTypes'])}
    - Required Reports: Weekly status reports, Monthly performance metrics, Quarterly business reviews
    """

  def _build_contract_prompt(self, client_data, company_profile, sections):
    return f"""
    You are tasked with generating a detailed service contract between ServiceTech Solutions and
    {client_data['client']['company']['name']}. Use this comprehensive context to create a
    contract that addresses all specific needs and concerns.

    CONTEXT ABOUT SERVICE PROVIDER:
    {company_profile}

    CLIENT CONTEXT:
    Company: {client_data['client']['company']['name']}
    Industry: {client_data['client']['company']['industry']}
    Annual Revenue: {client_data['client']['company']['annualRevenue']}
    Locations: {client_data['client']['company']['locations']}
    Year Founded: {client_data['client']['company']['yearFounded']}
    Business Model: {client_data['client']['businessProfile']['model']}
    Company Culture: {client_data['client']['businessProfile']['culture']}
    Key Challenges: {client_data['client']['businessProfile']['mainChallenges']}
    Unique Characteristics: {client_data['client']['businessProfile']['uniqueCharacteristics']}

    {sections['address']}

    {sections['contacts']}

    {sections['financial']}

    SERVICE REQUIREMENTS:
    Primary Services: {client_data['client']['serviceRequirements']['primaryServices']}
    Response Time Required: {client_data['client']['serviceRequirements']['responseTimeRequired']}
    Special Requirements: {client_data['client']['serviceRequirements']['specialRequirements']}

    CONTRACT SPECIFICS:
    Initial Terms: {client_data['crm']['contractDetails']['initial']['keyTerms']}
    Final Special Terms: {client_data['crm']['contractDetails']['final']['specialTerms']}
    Contract Duration: {client_data['crm']['contractDetails']['final']['actualTerm']}
    Contract Value: {client_data['crm']['contractDetails']['final']['actualValue']}

    RELATIONSHIP CONTEXT:
    {sections['relationship']}

    ADDITIONAL OPERATIONAL DETAILS:
    {sections['sla']}

    PRICING STRUCTURE:
    {sections['pricing']}

    TIMELINE AND REVIEWS:
    {sections['timeline']}

    COMMUNICATION REQUIREMENTS:
    {sections['communication']}

    Generate a comprehensive service contract that includes:

    1. Parties and Recitals
      - Include full legal descriptions of both parties
      - Specify the business context and purpose of the agreement
      - Reference any relevant prior agreements or relationships

    2. Definitions
      - Define all technical terms specific to this industry and service type
      - Include client-specific terminology based on their business model
      - Define service levels, response times, and performance metrics

    3. Detailed Scope of Services
      - Break down each service type with specific inclusions and exclusions
      - Address any unique requirements based on client's industry
      - Include specific service locations and coverage areas
      - Detail resource commitments (personnel, equipment, etc.)

    4. Service Level Agreements
      - Response time commitments
      - Performance metrics and measurement methods
      - Reporting requirements and frequencies
      - Quality assurance standards
      - Issue resolution procedures

    5. Term and Termination
      - Contract duration
      - Renewal terms
      - Termination conditions and notice periods
      - Transition assistance provisions

    6. Pricing and Payment Terms
      - Fee structure
      - Payment schedule
      - Rate adjustments
      - Additional services pricing
      - Volume discounts if applicable
      - Late payment terms

    7. Personnel and Resources
      - Key personnel requirements
      - Certification requirements
      - Security clearance requirements if needed
      - Subcontractor usage and approval process

    8. Compliance and Standards
      - Industry-specific regulatory requirements
      - Safety standards
      - Environmental compliance if relevant
      - Data security requirements

    9. Insurance and Liability
      - Insurance requirements specific to the industry
      - Liability limitations
      - Indemnification terms
      - Force majeure provisions

    10. Additional Terms Based on Client Profile
      - Add any terms that address the client's specific challenges
      - Include provisions for their unique characteristics
      - Address any industry-specific risks or requirements


    11. Service Level Agreements (Detailed)
      - Response time target: {client_data['crm']['issues']['slaPerformance']['responseTime']}
      - Resolution time target: {client_data['crm']['issues']['slaPerformance']['resolutionTime']}
      - Customer satisfaction requirements
      - Performance measurement and reporting
      - Penalty clauses for missed SLAs
      - Escalation procedures

    12. Financial Terms
      - Detailed pricing structure for each service type
      - Payment schedules aligned with {client_data['crm']['financials']['paymentHistory']['averageDaysToPayment']} day payment terms
      - Rate cards for additional services
      - Annual price adjustment mechanisms
      - Invoice dispute resolution process

    13. Communication and Reporting
      - Required regular meetings and reviews
      - Reporting schedule and formats
      - Key stakeholder roles and responsibilities
      - Emergency communication procedures
      - Documentation requirements

    Format the response in clear sections with proper legal language. The contract should
    be detailed and comprehensive while remaining clear and unambiguous. Add any additional
    sections or terms you think are necessary based on the client's industry, size, and
    specific requirements.

    This contract should be the final contract. It should not contain any placeholders.
    """

  def _get_llm_response(self, prompt):
    response = self.llm.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """You are an expert legal document generator with
                deep knowledge of service contracts, especially in technical and facility
                management industries. Create comprehensive, legally sound contract language that
                protects both parties while facilitating effective service delivery.""",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=4000,
    )
    return response.choices[0].message.content

  def create_pdf(self, contract_content, output_path):
    pdf = FPDF()
    pdf.add_page()

    # Add company logo/header
    pdf.set_font("Arial", 'B', size=16)
    pdf.cell(200, 10, txt="SERVICE AGREEMENT", ln=1, align="C")

    # Process markdown content
    for line in contract_content.split("\n"):
        # Handle special characters by replacing them
        line = (line.replace('"', '"')
                   .replace('"', '"')
                   .replace(''', "'")
                   .replace(''', "'")
                   .replace('—', '-'))
        # Handle headers
        if line.strip().startswith('#'):
            level = len(line.split()[0])  # Count the number of #
            size = 20 - (level * 2)  # Decrease size for each header level
            pdf.set_font("Arial", 'B', size=size)
            pdf.cell(0, 10, txt=line.lstrip('#').strip(), ln=1)

        # Handle bold text (between ** **)
        elif '**' in line:
            parts = line.split('**')
            for i, part in enumerate(parts):
                if i % 2 == 0:  # Regular text
                    pdf.set_font("Arial", size=12)
                    pdf.write(10, part)
                else:  # Bold text
                    pdf.set_font("Arial", 'B', size=12)
                    pdf.write(10, part)
            pdf.ln()

        # Regular text
        else:
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, txt=line)

    pdf.output(output_path)


def generate_contracts():
  # Initialize generator
  generator = ContractGenerator()

  # Load all CRM profiles
  with open("seed_data/customer_crm_profiles.json", "r") as f:
    crm_profiles = json.load(f)

  # Filter for active clients
  active_clients = [
    client for client in crm_profiles["clientRelationships"]
    if client["relationshipStatus"]["currentState"] == "ACTIVE_CLIENT"
  ]

  print(f"Generating contracts for {len(active_clients)} active clients...")

  # Process each active client
  for client in active_clients:
    client_id = client["clientId"]
    company_name = client["companyName"]
    print(f"\nProcessing {company_name} (ID: {client_id})")

    try:
      # Load relevant data
      client_data = generator.load_client_data(client_id)

      # Generate contract content
      contract_content = generator.generate_contract_content(client_data)

      # Create output directory if it doesn't exist
      Path("company_documents/contracts").mkdir(parents=True, exist_ok=True)

      # Create PDF
      output_path = (
        f"company_documents/contracts/customer/{client_id}_contract_{datetime.now().strftime('%Y%m%d')}.pdf"
      )
      generator.create_pdf(contract_content, output_path)
      print(f"✓ Successfully generated contract: {output_path}")

    except Exception as e:
      print(f"✗ Error processing {company_name}: {str(e)}")


if __name__ == "__main__":
  generate_contracts()
