import json
from pathlib import Path
import jinja2
from fpdf import FPDF
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import random
from typing import Dict, List
import os
from dotenv import load_dotenv

load_dotenv()

class VendorInvoiceGenerator:
  def __init__(self, template_dir="templates"):
    self.template_loader = jinja2.FileSystemLoader(template_dir)
    self.template_env = jinja2.Environment(loader=self.template_loader)

    # Load vendor profiles and operational expenses data
    with open("seed_data/vendor_profiles.json", "r") as f:
      self.vendors = json.load(f)["vendors"]

    with open("seed_data/recurring_operating_expenses.json", "r") as f:
      self.expense_data = json.load(f)["recurringOperationalExpenses"]

  def generate_rent_invoice(self, date: datetime, location: str) -> Dict:
    """Generate rent invoice for a specific location"""
    vendor = self.vendors["facilities"]["CitySpace_Commercial"]

    if location == "main":
      base_amount = float(vendor["contracts"]["main_office"]["value"]["monthly"])
    else:
      base_amount = float(vendor["contracts"]["regional_offices"][location]["monthly"])

    # Convert to Decimal after ensuring we have a float
    base_decimal = Decimal(str(base_amount))

    # Calculate additional charges based on lease terms
    cam_charges = base_decimal * Decimal('0.1')  # Common Area Maintenance
    property_tax = base_decimal * Decimal('0.05')  # Property Tax

    # Calculate annual increase if applicable
    start_date = datetime(2023, 1, 1)  # Example start date
    years_elapsed = (date - start_date).days / 365
    if years_elapsed >= 1:
      # Apply the greater of 3% or CPI (using 3% as default)
      increase_rate = Decimal('0.03') * int(years_elapsed)
      base_decimal += base_decimal * increase_rate

    total_amount = base_decimal + cam_charges + property_tax

    return {
      "description": f"Monthly Rent - {location.title()} Office",
      "amount": total_amount,
      "details": [
        {"item": "Base Rent", "amount": base_decimal},
        {"item": "CAM Charges", "amount": cam_charges},
        {"item": "Property Tax", "amount": property_tax}
      ],
      "vendor": vendor
    }

  def generate_utility_invoice(self, date: datetime) -> Dict:
    """Generate utility invoice with seasonal variations"""
    vendor = self.vendors["facilities"]["Metro_Utilities"]
    base_utilities = vendor["contracts"]["utilities"]["value"]["monthly_average"]
    breakdown = vendor["contracts"]["utilities"]["value"]["breakdown"]

    # Add seasonal variation
    season_factor = 1.0
    if date.month in [6, 7, 8]:  # Summer
      season_factor = 1.3
    elif date.month in [12, 1, 2]:  # Winter
      season_factor = 1.2

    # Apply peak demand pricing if applicable
    peak_factor = Decimal('1.0')
    if 9 <= date.hour <= 17:  # Peak hours
      peak_factor = Decimal('1.15')

    return {
      "description": "Monthly Utilities",
      "amount": Decimal(str(base_utilities * season_factor * float(peak_factor))),
      "details": [
        {"item": "Electricity",
         "amount": Decimal(str(breakdown["electricity"] * season_factor * float(peak_factor)))},
        {"item": "Water",
         "amount": Decimal(str(breakdown["water"]))},
        {"item": "Internet & Phones",
         "amount": Decimal(str(breakdown["internet_phones"]))}
      ],
      "vendor": vendor
    }

  def generate_software_invoice(self, date: datetime) -> Dict:
    """Generate software subscription invoice"""
    vendor = self.vendors["technology"]["TechCare_Solutions"]
    subscriptions = vendor["services"]["software_subscriptions"]

    total_amount = Decimal('0')
    details = []

    for system, info in subscriptions.items():
      amount = Decimal(str(info["monthly"]))
      total_amount += amount
      details.append({
        "item": f"{info['product']} Subscription",
        "amount": amount
      })

    # Add managed services if included
    managed_services = vendor["services"]["managed_services"]
    managed_amount = Decimal(str(managed_services["monthly"]))
    total_amount += managed_amount
    details.append({
      "item": "Managed IT Services",
      "amount": managed_amount
    })

    return {
      "description": "Monthly Technology Services",
      "amount": total_amount,
      "details": details,
      "vendor": vendor
    }

  def generate_fleet_invoice(self, date: datetime) -> Dict:
    """Generate fleet-related invoice with variations"""
    vendor = self.vendors["fleet"]["FleetMaster_Leasing"]
    fleet_lease = vendor["contracts"]["fleet_lease"]
    fuel_program = vendor["contracts"]["fuel_program"]

    # Calculate lease amount
    base_lease = Decimal(str(fleet_lease["value"]["monthly_total"]))

    # Calculate fuel costs with market variations
    fuel_base = Decimal(str(fuel_program["value"]["monthly_total"]))
    fuel_variation = Decimal(str(random.uniform(0.9, 1.1)))
    fuel_cost = fuel_base * fuel_variation

    # Add maintenance costs if any vehicles exceeded mileage
    maintenance_cost = Decimal('0')
    if random.random() < 0.3:  # 30% chance of maintenance needed
      maintenance_cost = base_lease * Decimal('0.05')

    total_amount = base_lease + fuel_cost + maintenance_cost

    return {
      "description": "Monthly Fleet Services",
      "amount": total_amount,
      "details": [
        {"item": "Vehicle Leases", "amount": base_lease},
        {"item": "Fuel Charges", "amount": fuel_cost},
        {"item": "Maintenance", "amount": maintenance_cost}
      ],
      "vendor": vendor
    }

  def create_invoice_pdf(self,
                       invoice_data: Dict,
                       invoice_number: str,
                       invoice_date: datetime,
                       output_path: str):
    """Create PDF invoice"""
    pdf = FPDF()
    pdf.add_page()

    vendor = invoice_data["vendor"]

    # Vendor header
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, vendor["name"], ln=True, align="L")
    pdf.set_font("Arial", "", 10)
    address = vendor["company"]["headquarters"]
    for line in address.split(", "):
      pdf.cell(0, 5, line, ln=True)
    pdf.ln(5)

    # Invoice details
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "INVOICE", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 5, f"Invoice Number: {invoice_number}", ln=True)
    pdf.cell(0, 5, f"Date: {invoice_date.strftime('%B %d, %Y')}", ln=True)
    pdf.cell(0, 5, f"Vendor ID: {vendor['id']}", ln=True)

    # Get payment terms from the appropriate contract
    payment_terms = "Net 30"  # Default
    if "terms" in vendor.get("contracts", {}):
      contract = next(iter(vendor["contracts"].values()))
      if "payment_terms" in contract.get("terms", {}):
        payment_terms = contract["terms"]["payment_terms"]

    pdf.cell(0, 5, f"Terms: {payment_terms}", ln=True)
    pdf.ln(10)

    # Bill To
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Bill To:", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 5, "ServiceTech Solutions", ln=True)
    pdf.cell(0, 5, "2500 Innovation Drive", ln=True)
    pdf.cell(0, 5, "Suite 400", ln=True)
    pdf.cell(0, 5, "San Jose, CA 95134", ln=True)
    pdf.ln(10)

    # Items
    pdf.set_font("Arial", "B", 10)
    col_width = 95
    pdf.cell(col_width, 10, "Description", 1)
    pdf.cell(col_width, 10, "Amount", 1, ln=True)

    pdf.set_font("Arial", "", 10)
    for detail in invoice_data["details"]:
      pdf.cell(col_width, 10, detail["item"], 1)
      pdf.cell(col_width, 10, f"${detail['amount']:,.2f}", 1, ln=True)

    # Total
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(col_width, 10, "Total Due:", 0)
    pdf.cell(col_width, 10, f"${invoice_data['amount']:,.2f}", 0, ln=True)

    # Payment terms and additional information
    pdf.ln(10)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 5, f"Please pay within {payment_terms}", ln=True)
    pdf.cell(0, 5, "Make checks payable to " + vendor["company"]["legalName"], ln=True)

    # Add any special terms or notes if present
    if "special_conditions" in vendor.get("contracts", {}).get("terms", {}):
      pdf.ln(5)
      pdf.set_font("Arial", "I", 9)
      pdf.cell(0, 5, "Note: " + vendor["contracts"]["terms"]["special_conditions"], ln=True)

    pdf.output(output_path)

  def generate_monthly_invoices(self, start_date: datetime, end_date: datetime) -> None:
    """Generate all vendor invoices for a period"""
    current_date = start_date

    while current_date <= end_date:
      print(f"\nGenerating vendor invoices for {current_date.strftime('%B %Y')}")

      # Create directory structure
      output_dir = Path(f"company_documents/invoices/incoming/{current_date.year}/{current_date.strftime('%m')}")
      output_dir.mkdir(parents=True, exist_ok=True)

      # Generate rent invoices for all locations
      for location in ["main", "northeast", "southeast", "midwest", "west"]:
        invoice_data = self.generate_rent_invoice(current_date, location)
        invoice_number = f"RENT-{location.upper()}-{current_date.strftime('%Y%m')}"
        output_path = output_dir / f"{invoice_number}.pdf"

        self.create_invoice_pdf(
          invoice_data, invoice_number, current_date, str(output_path)
        )

      # Generate utility invoices
      invoice_data = self.generate_utility_invoice(current_date)
      invoice_number = f"UTIL-{current_date.strftime('%Y%m')}"
      output_path = output_dir / f"{invoice_number}.pdf"

      self.create_invoice_pdf(
        invoice_data, invoice_number, current_date, str(output_path)
      )

      # Generate software invoices
      invoice_data = self.generate_software_invoice(current_date)
      invoice_number = f"TECH-{current_date.strftime('%Y%m')}"
      output_path = output_dir / f"{invoice_number}.pdf"

      self.create_invoice_pdf(
        invoice_data, invoice_number, current_date, str(output_path)
      )

      # Generate fleet invoices
      invoice_data = self.generate_fleet_invoice(current_date)
      invoice_number = f"FLEET-{current_date.strftime('%Y%m')}"
      output_path = output_dir / f"{invoice_number}.pdf"

      self.create_invoice_pdf(
        invoice_data, invoice_number, current_date, str(output_path)
      )

      current_date += relativedelta(months=1)

def generate_vendor_invoices():
  generator = VendorInvoiceGenerator()

  # Generate invoices from start of 2023 through 2024
  start_date = datetime(2023, 1, 1)
  end_date = datetime(2024, 12, 31)

  try:
    generator.generate_monthly_invoices(start_date, end_date)
    print("\n✓ Successfully generated all vendor invoices")
  except Exception as e:
    print(f"\n✗ Error generating vendor invoices: {str(e)}")

if __name__ == "__main__":
  generate_vendor_invoices()
