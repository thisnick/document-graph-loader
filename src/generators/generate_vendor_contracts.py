import json
from pathlib import Path
from typing import Dict
import jinja2
from fpdf import FPDF
from datetime import datetime, timedelta
from decimal import Decimal
import os
from dotenv import load_dotenv
import openai
from typing import Dict, List, Optional

load_dotenv()

class VendorContractGenerator:
  def __init__(self, template_dir="templates"):
    self.template_loader = jinja2.FileSystemLoader(template_dir)
    self.template_env = jinja2.Environment(loader=self.template_loader)

    # Load vendor data
    with open("seed_data/vendor_profiles.json", "r") as f:
      self.vendors = json.load(f)["vendors"]

    with open("seed_data/recurring_operating_expenses.json", "r") as f:
      self.expense_data = json.load(f)["recurringOperationalExpenses"]

    # Initialize OpenAI
    self.openai_client = openai.OpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )

  def _load_company_profile(self):
    """Load ServiceTech company profile"""
    with open("seed_data/company.txt", "r") as f:
      return f.read()

  def _generate_contract_prompt(self, vendor: Dict, vendor_type: str) -> str:
    """Generate prompt for contract generation based on vendor type and details"""
    base_prompt = f"""Generate a detailed, professional contract section for {vendor['name']}, a {vendor_type} vendor.

Company Details:
- Legal Name: {vendor['company']['legalName']}
- Industry: {vendor['company']['industry']}
- Service Type: {vendor['type']}

Services Overview:"""

    # Add service-specific details based on vendor type
    if vendor_type == "facilities":
      base_prompt += f"""
This is a facilities contract covering:
- Primary Service: {vendor['services'].get('primary', '')}
- Additional Services: {', '.join(vendor['services'].get('additional', []))}
- Coverage Areas: {', '.join(vendor['services'].get('coverage', []))}

Include specific terms for:
- Property management responsibilities
- Maintenance obligations
- Security and access requirements
- Facility operating hours
- Emergency response procedures"""

    elif vendor_type == "technology":
      base_prompt += f"""
This is a technology services contract covering:
Software Subscriptions:
{self._format_software_subscriptions(vendor)}

Include specific terms for:
- Software licensing terms
- Data security requirements
- System uptime guarantees
- Support response times
- User access management
- Data backup and recovery"""

    elif vendor_type == "fleet":
      base_prompt += f"""
This is a fleet management contract covering:
- Primary Service: {vendor['services'].get('primary', '')}
- Additional Services: {', '.join(vendor['services'].get('additional', []))}

Include specific terms for:
- Vehicle maintenance schedules
- Fuel management procedures
- Insurance requirements
- Vehicle replacement terms
- Driver responsibilities
- Accident reporting procedures"""

    # Add contract value information
    for contract_name, contract_details in vendor['contracts'].items():
      if 'value' in contract_details:
        base_prompt += f"\n\nContract Value for {contract_name}:"
        if isinstance(contract_details['value'], dict):
          for key, value in contract_details['value'].items():
            base_prompt += f"\n- {key}: {value}"

    base_prompt += """

Generate the following contract sections:
1. Scope of Services
2. Payment Terms
3. Service Level Agreement
4. Term and Termination
5. Compliance Requirements
6. Special Provisions

Each section should be detailed and specific to this vendor's industry and services."""

    return base_prompt

  def _format_software_subscriptions(self, vendor: Dict) -> str:
    """Format software subscription details for prompt"""
    if 'software_subscriptions' not in vendor.get('services', {}):
      return ""

    result = []
    for product, details in vendor['services']['software_subscriptions'].items():
      result.append(f"- {details['product']}: {details.get('users', 'Unlimited')} users")
    return "\n".join(result)

  def _generate_contract_section(self, prompt: str) -> str:
    """Generate contract section using OpenAI"""
    try:
      response = self.openai_client.chat.completions.create(
        model="gpt-4",  # or your preferred model
        messages=[
          {"role": "system", "content": "You are a legal contract writer specializing in business contracts. Write in a clear, professional style using standard legal terminology."},
          {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=2000
      )
      return response.choices[0].message.content
    except Exception as e:
      print(f"Error generating contract section: {str(e)}")
      return ""

  def generate_contract_content(self, vendor_type: str, vendor_id: str) -> Dict:
    """Generate contract content for a specific vendor using LLM"""
    vendor = self.vendors[vendor_type][vendor_id]
    prompt = self._generate_contract_prompt(vendor, vendor_type)

    contract_text = self._generate_contract_section(prompt)

    # Parse the generated text into sections
    sections = self._parse_contract_sections(contract_text)

    return {
      "vendor": vendor,
      "sections": sections,
      "date": datetime.now()
    }

  def _parse_contract_sections(self, contract_text: str) -> Dict[str, str]:
    """Parse the generated contract text into sections"""
    sections = {
      "scope_of_services": "",
      "payment_terms": "",
      "service_levels": "",
      "term_and_termination": "",
      "compliance": "",
      "special_provisions": ""
    }

    current_section = None
    current_text = []

    for line in contract_text.split('\n'):
      if any(section in line.lower() for section in [
        "scope of services",
        "payment terms",
        "service level",
        "term and termination",
        "compliance",
        "special provisions"
      ]):
        if current_section:
          sections[current_section] = '\n'.join(current_text).strip()
        current_section = self._identify_section(line)
        current_text = []
      elif current_section:
        current_text.append(line)

    if current_section:
      sections[current_section] = '\n'.join(current_text).strip()

    return sections

  def _identify_section(self, line: str) -> Optional[str]:
    """Identify which section a header line belongs to"""
    line = line.lower()
    if "scope of services" in line:
      return "scope_of_services"
    elif "payment terms" in line:
      return "payment_terms"
    elif "service level" in line:
      return "service_levels"
    elif "term and termination" in line:
      return "term_and_termination"
    elif "compliance" in line:
      return "compliance"
    elif "special provisions" in line:
      return "special_provisions"
    return None

  def create_contract_pdf(self, content: Dict, output_path: str):
    """Create PDF contract"""
    pdf = FPDF()
    pdf.add_page()

    # Add header
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "MASTER SERVICES AGREEMENT", ln=True, align="C")
    pdf.ln(10)

    # Add contract date and parties
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"This Agreement is made on {content['date'].strftime('%B %d, %Y')}", ln=True)
    pdf.cell(0, 10, "between", ln=True)
    pdf.ln(5)

    # Party details
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "ServiceTech Solutions (\"Client\")", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 5, "2500 Innovation Drive", ln=True)
    pdf.cell(0, 5, "Suite 400", ln=True)
    pdf.cell(0, 5, "San Jose, CA 95134", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"{content['vendor']['name']} (\"Vendor\")", ln=True)
    pdf.set_font("Arial", "", 10)
    address = content['vendor']['company']['headquarters'].split(", ")
    for line in address:
      pdf.cell(0, 5, line, ln=True)
    pdf.ln(10)

    # Contract sections
    sections = [
      ("SCOPE OF SERVICES", content['sections']['scope_of_services']),
      ("PAYMENT TERMS", content['sections']['payment_terms']),
      ("SERVICE LEVEL AGREEMENT", content['sections']['service_levels']),
      ("TERM AND TERMINATION", content['sections']['term_and_termination']),
      ("COMPLIANCE AND STANDARDS", content['sections']['compliance']),
      ("SPECIAL PROVISIONS", content['sections']['special_provisions'])
    ]

    for title, text in sections:
      pdf.set_font("Arial", "B", 12)
      pdf.cell(0, 10, title, ln=True)
      pdf.set_font("Arial", "", 10)
      pdf.multi_cell(0, 5, text)
      pdf.ln(10)

    # Signature block
    pdf.ln(20)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(95, 10, "ServiceTech Solutions", ln=False)
    pdf.cell(95, 10, content['vendor']['name'], ln=True)

    pdf.ln(15)
    pdf.set_font("Arial", "", 10)
    pdf.cell(95, 10, "________________________", ln=False)
    pdf.cell(95, 10, "________________________", ln=True)
    pdf.cell(95, 10, "Authorized Signature", ln=False)
    pdf.cell(95, 10, "Authorized Signature", ln=True)
    pdf.cell(95, 10, "Date: _________________", ln=False)
    pdf.cell(95, 10, "Date: _________________", ln=True)

    pdf.output(output_path)

  def generate_vendor_contracts(self):
    """Generate contracts for all vendors"""
    output_dir = Path("company_documents/contracts/vendor")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate contracts for each vendor type and vendor
    for vendor_type, vendors in self.vendors.items():
      for vendor_id in vendors:
        try:
          print(f"\nGenerating contract for {vendors[vendor_id]['name']}")

          # Generate contract content
          content = self.generate_contract_content(vendor_type, vendor_id)

          # Create PDF
          output_path = output_dir / f"{vendor_id}_contract_{datetime.now().strftime('%Y%m%d')}.pdf"
          self.create_contract_pdf(content, str(output_path))

          print(f"✓ Successfully generated contract: {output_path}")

        except Exception as e:
          print(f"✗ Error generating contract for {vendor_id}: {str(e)}")

def generate_vendor_contracts():
  generator = VendorContractGenerator()

  try:
    generator.generate_vendor_contracts()
    print("\n✓ Successfully generated all vendor contracts")
  except Exception as e:
    print(f"\n✗ Error generating vendor contracts: {str(e)}")

if __name__ == "__main__":
  generate_vendor_contracts()
