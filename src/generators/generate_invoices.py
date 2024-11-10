import json
from pathlib import Path
import jinja2
from fpdf import FPDF
from datetime import datetime, timedelta
import random
from decimal import Decimal
import calendar
from typing import Dict, List
import os
from dotenv import load_dotenv
from dateutil.relativedelta import relativedelta
import numpy as np

load_dotenv()


# Initialize commission calculator
from ..calculators import CommissionCalculator

class InvoiceGenerator:
    def __init__(self, template_dir="templates"):
        self.template_loader = jinja2.FileSystemLoader(template_dir)
        self.template_env = jinja2.Environment(loader=self.template_loader)

    def load_data(self, client_id: str) -> Dict:
        """Load all relevant data for invoice generation"""
        return {
            "client": self._load_client_portfolio(client_id),
            "crm": self._load_crm_profile(client_id),
            "pricing": self._load_pricing_structure(),
            "contract": self._load_contract_metadata(client_id)
        }

    def _load_client_portfolio(self, client_id: str) -> Dict:
        with open("seed_data/client_portfolio.json", "r") as f:
            portfolio = json.load(f)
            return next((client for client in portfolio["clients"]
                        if client["id"] == client_id), None)

    def _load_crm_profile(self, client_id: str) -> Dict:
        with open("seed_data/customer_crm_profiles.json", "r") as f:
            profiles = json.load(f)
            return next((profile for profile in profiles["clientRelationships"]
                        if profile["clientId"] == client_id), None)

    def _load_pricing_structure(self) -> Dict:
        with open("seed_data/revenue_and_pricing_structure.json", "r") as f:
            return json.load(f)

    def _load_contract_metadata(self, client_id: str) -> Dict:
        contract_path = f"company_documents/contracts/metadata.json"
        if os.path.exists(contract_path):
            with open(contract_path, "r") as f:
                contracts = json.load(f)
                return next((contract for contract in contracts["contracts"].values()
                           if contract["metadata"]["clientId"] == client_id), None)
        return None

    def generate_invoice_items(self, client_data: Dict, invoice_date: datetime, variation_factors: Dict = None) -> List[Dict]:
      """Generate realistic line items based on contract and service data"""
      items = []

      # Extract contract value and services
      contract_value_str = client_data["crm"]["contractDetails"]["final"]["actualValue"]
      contract_value = Decimal(contract_value_str.replace("$", "").replace(",", "").replace("/year", ""))
      monthly_base = contract_value / 12

      # Get primary services from client data
      services = client_data["client"]["serviceRequirements"]["primaryServices"]
      service_count = len(services)

      # Generate regular contract service items
      for service in services:
          # Base service amount with some built-in variation
          service_amount = (monthly_base / service_count) * Decimal(random.uniform(0.95, 1.05))

          # Apply variation factors if provided
          if variation_factors:
              total_factor = (
                  variation_factors["seasonal"] *
                  variation_factors["random"] *
                  variation_factors["industry"] *
                  variation_factors["events"] *
                  variation_factors["size"] *
                  variation_factors["growth"]
              )
              service_amount = service_amount * Decimal(str(total_factor))

          items.append({
              "description": f"Monthly {service}",
              "quantity": 1,
              "unit": "month",
              "rate": service_amount,
              "amount": service_amount,
              "service_period": f"{invoice_date.strftime('%B %Y')}"
          })

      # Add emergency services (20% chance)
      if random.random() < 0.2:
          emergency_rate = Decimal("225.00")  # Base emergency rate
          hours = random.randint(2, 6)

          if variation_factors:
              emergency_rate *= Decimal(str(variation_factors["random"]))

          items.append({
              "description": "Emergency Service Call",
              "quantity": hours,
              "unit": "hours",
              "rate": emergency_rate,
              "amount": emergency_rate * hours,
              "service_period": invoice_date.strftime("%Y-%m-%d")
          })

      # Add additional materials (30% chance)
      if random.random() < 0.3:
          material_cost = Decimal(str(random.uniform(500, 2500)))

          if variation_factors:
              material_cost *= Decimal(str(variation_factors["random"]))

          items.append({
              "description": "Additional Materials and Supplies",
              "quantity": 1,
              "unit": "lot",
              "rate": material_cost,
              "amount": material_cost,
              "service_period": invoice_date.strftime("%Y-%m-%d")
          })

      # Add special maintenance (15% chance)
      if random.random() < 0.15:
          maintenance_rate = Decimal("150.00")
          hours = random.randint(4, 8)

          if variation_factors:
              maintenance_rate *= Decimal(str(variation_factors["random"]))

          items.append({
              "description": "Special Maintenance Work",
              "quantity": hours,
              "unit": "hours",
              "rate": maintenance_rate,
              "amount": maintenance_rate * hours,
              "service_period": invoice_date.strftime("%Y-%m-%d")
          })

      return items

    def calculate_invoice_totals(self, items: List[Dict]) -> Dict:
        """Calculate invoice totals including subtotal, tax, and total"""
        subtotal = sum(item["amount"] for item in items)
        tax_rate = Decimal("0.08")  # 8% tax rate
        tax_amount = subtotal * tax_rate
        total = subtotal + tax_amount

        return {
            "subtotal": subtotal,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
            "total": total
        }

    def generate_invoice_number(self, client_id: str, date: datetime) -> str:
        """Generate a unique invoice number"""
        return f"INV-{client_id}-{date.strftime('%Y%m')}"

    def create_invoice_pdf(self,
                         client_data: Dict,
                         items: List[Dict],
                         totals: Dict,
                         invoice_number: str,
                         invoice_date: datetime,
                         output_path: str):
        """Create a PDF invoice"""
        pdf = FPDF()
        pdf.add_page()

        # Add header
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "INVOICE", ln=True, align="C")

        # Company information
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "ServiceTech Solutions", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, "123 Tech Street", ln=True)
        pdf.cell(0, 5, "Business City, ST 12345", ln=True)
        pdf.cell(0, 5, "Phone: (555) 123-4567", ln=True)
        pdf.ln(5)

        # Invoice details
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 5, f"Invoice Number: {invoice_number}", ln=True)
        pdf.cell(0, 5, f"Invoice Date: {invoice_date.strftime('%B %d, %Y')}", ln=True)
        pdf.cell(0, 5, f"Due Date: {(invoice_date + timedelta(days=30)).strftime('%B %d, %Y')}", ln=True)
        pdf.ln(5)

        # Bill to
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Bill To:", ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 5, client_data["client"]["company"]["name"], ln=True)
        pdf.cell(0, 5, "Attn: " + client_data["client"]["keyContacts"][0]["name"], ln=True)

        # Items table
        pdf.ln(10)
        pdf.set_font("Arial", "B", 10)

        # Table header
        col_widths = [80, 20, 30, 30, 30]
        pdf.cell(col_widths[0], 10, "Description", 1)
        pdf.cell(col_widths[1], 10, "Qty", 1)
        pdf.cell(col_widths[2], 10, "Unit", 1)
        pdf.cell(col_widths[3], 10, "Rate", 1)
        pdf.cell(col_widths[4], 10, "Amount", 1)
        pdf.ln()

        # Table content
        pdf.set_font("Arial", "", 10)
        for item in items:
            # Handle long descriptions
            desc = item["description"]
            if len(desc) > 40:
                desc = desc[:37] + "..."

            pdf.cell(col_widths[0], 10, desc, 1)
            pdf.cell(col_widths[1], 10, str(item["quantity"]), 1)
            pdf.cell(col_widths[2], 10, item["unit"], 1)
            pdf.cell(col_widths[3], 10, f"${item['rate']:,.2f}", 1)
            pdf.cell(col_widths[4], 10, f"${item['amount']:,.2f}", 1)
            pdf.ln()

        # Totals
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(160, 10, "Subtotal:", 0, 0, "R")
        pdf.cell(30, 10, f"${totals['subtotal']:,.2f}", 0, 1, "R")

        pdf.cell(160, 10, f"Tax ({totals['tax_rate']*100}%):", 0, 0, "R")
        pdf.cell(30, 10, f"${totals['tax_amount']:,.2f}", 0, 1, "R")

        pdf.set_font("Arial", "B", 12)
        pdf.cell(160, 10, "Total:", 0, 0, "R")
        pdf.cell(30, 10, f"${totals['total']:,.2f}", 0, 1, "R")

        # Payment terms
        pdf.ln(10)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 10, "Payment Terms", ln=True)
        pdf.set_font("Arial", "", 10)
        payment_terms = client_data["crm"]["contractDetails"]["final"]["specialTerms"]
        pdf.multi_cell(0, 5, str(payment_terms))

        # Save the PDF
        pdf.output(output_path)

    def generate_monthly_invoices(self, client_data: Dict, start_date: datetime, end_date: datetime) -> None:
        """Generate invoices for a date range with realistic variations and calculate commissions"""
        current_date = start_date
        growth_factor = 1.0

        commission_calc = CommissionCalculator()

        while current_date <= end_date:
            variation_factors = self._calculate_variation_factors(
                client_data, current_date, growth_factor
            )

            items = self.generate_invoice_items(
                client_data, current_date, variation_factors
            )

            totals = self.calculate_invoice_totals(items)
            invoice_number = self.generate_invoice_number(
                client_data["client"]["id"], current_date
            )

            # Create output directory structure by year/month
            output_dir = Path(f"company_documents/invoices/outgoing/{current_date.year}/{current_date.strftime('%m')}")
            output_dir.mkdir(parents=True, exist_ok=True)

            output_path = output_dir / f"{invoice_number}.pdf"
            self.create_invoice_pdf(
                client_data, items, totals, invoice_number, current_date, str(output_path)
            )

            # Calculate and store commission data
            sales_rep_id = client_data["crm"]["salesRepId"]
            commission_amount = commission_calc.calculate_commission(sales_rep_id, current_date)
            quota_data = commission_calc.calculate_quota_attainment(sales_rep_id, current_date)
            cac_data = commission_calc.calculate_cac(client_data["client"]["id"], current_date)

            # Store commission data
            commission_dir = Path(f"company_documents/commissions/{current_date.year}/{current_date.strftime('%m')}")
            commission_dir.mkdir(parents=True, exist_ok=True)

            commission_data = {
                "invoice_number": invoice_number,
                "sales_rep_id": sales_rep_id,
                "commission_amount": str(commission_amount),
                "quota_attainment": {
                    "attainment": {k: str(v) for k, v in quota_data[0].items()},
                    "total_attainment": str(quota_data[1])
                },
                "cac_data": {k: str(v) if isinstance(v, Decimal) else
                            {sk: str(sv) for sk, sv in v.items()}
                            for k, v in cac_data.items()} if cac_data else None
            }

            commission_path = commission_dir / f"{invoice_number}_commission.json"
            with open(commission_path, "w") as f:
                json.dump(commission_data, f, indent=2)

            growth_factor *= 1.002  # 0.2% monthly growth
            current_date += relativedelta(months=1)

    def _calculate_variation_factors(self, client_data: Dict, invoice_date: datetime, base_growth: float) -> Dict:
        """Calculate various factors that affect invoice amounts"""
        month_number = invoice_date.month
        seasonal_factor = 1 + 0.15 * np.sin((month_number - 6) * np.pi / 6)
        random_factor = random.uniform(0.95, 1.05)
        industry_factor = self._get_industry_factor(client_data["client"]["company"]["industry"], invoice_date)
        events_factor = self._get_special_events_factor(client_data, invoice_date)
        size_factor = self._get_company_size_factor(client_data)

        return {
            "seasonal": seasonal_factor,
            "random": random_factor,
            "industry": industry_factor,
            "events": events_factor,
            "size": size_factor,
            "growth": base_growth
        }

    def _get_industry_factor(self, industry: str, date: datetime) -> float:
        industry_patterns = {
            "Retail": 1.3 if date.month in [11, 12] else 1.0,
            "Healthcare": 1.0,
            "Education": 0.7 if date.month in [6, 7, 8] else 1.1,
            "Manufacturing": 1.1 if date.month in [3, 4, 9, 10] else 1.0,
            "Technology": 1.15 if date.month in [3, 6, 9, 12] else 1.0,
        }
        return industry_patterns.get(industry, 1.0)

    def _get_special_events_factor(self, client_data: Dict, date: datetime) -> float:
        factor = 1.0

        start_date = datetime.strptime(
            client_data["crm"]["relationshipStatus"]["customerSince"],
            "%Y-%m-%d"
        )
        if date.month == start_date.month:
            factor *= 1.15

        if "peakSeason" in client_data["client"].get("businessProfile", {}).get("uniqueCharacteristics", []):
            if date.month in [6, 7, 8]:  # Summer months
                factor *= 1.25

        return factor

    def _get_company_size_factor(self, client_data: Dict) -> float:
        revenue = client_data["client"]["company"]["annualRevenue"]
        if isinstance(revenue, str):
            revenue = float(revenue.replace("$", "").replace("M", "000000"))

        if revenue > 500000000:
            return 1.2
        elif revenue > 100000000:
            return 1.1
        elif revenue > 50000000:
            return 1.0
        else:
            return 0.9

def generate_invoices():
    generator = InvoiceGenerator()

    with open("seed_data/customer_crm_profiles.json", "r") as f:
        crm_profiles = json.load(f)

    active_clients = [
        client for client in crm_profiles["clientRelationships"]
        if client["relationshipStatus"]["currentState"] == "ACTIVE_CLIENT"
    ]

    print(f"Generating historical and future invoices and commissions for {len(active_clients)} active clients...")

    for client in active_clients:
        client_id = client["clientId"]
        company_name = client["companyName"]
        print(f"\nProcessing {company_name} (ID: {client_id})")

        try:
            client_data = generator.load_data(client_id)
            start_date = datetime.strptime(
                client_data["crm"]["relationshipStatus"]["customerSince"],
                "%Y-%m-%d"
            )
            end_date = datetime(2024, 12, 31)

            generator.generate_monthly_invoices(client_data, start_date, end_date)
            print(f"✓ Successfully generated invoices and commissions from {start_date.strftime('%Y-%m')} to {end_date.strftime('%Y-%m')}")

        except Exception as e:
            print(f"✗ Error processing {company_name}: {str(e)}")

if __name__ == "__main__":
    generate_invoices()
