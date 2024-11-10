import json
from pathlib import Path
import jinja2
from fpdf import FPDF
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal, ROUND_HALF_UP
import random
from typing import Dict, List, Tuple
import calendar
import os
from dotenv import load_dotenv

load_dotenv()


class PayrollGenerator:
  def __init__(self, template_dir="templates"):
    self.template_loader = jinja2.FileSystemLoader(template_dir)
    self.template_env = jinja2.Environment(loader=self.template_loader)

    # Tax rates and deduction percentages
    self.tax_rates = {
      "federal": {
        "brackets": [
          (0, 11000, 0.10),
          (11001, 44725, 0.12),
          (44726, 95375, 0.22),
          (95376, 182100, 0.24),
          (182101, 231250, 0.32),
          (231251, 578125, 0.35),
          (578126, float("inf"), 0.37),
        ]
      },
      "social_security": 0.062,  # 6.2%
      "medicare": 0.0145,  # 1.45%
      "state": 0.05,  # Example state tax rate
    }

  def load_employee_data(self):
    """Load employee data from seed files"""
    with open("seed_data/employees.json", "r") as f:
      return json.load(f)

  def calculate_payroll_period(
    self, base_salary: float, period_date: datetime
  ) -> Dict:
    """Calculate payroll amounts for a specific period"""
    # Convert annual to monthly
    monthly_base = Decimal(str(base_salary)) / 12

    # Add random variation to hours worked (for hourly employees)
    standard_hours = Decimal("173.33")  # Average monthly hours
    # Convert random float to Decimal before multiplication
    variation = Decimal(str(random.uniform(0.95, 1.05)))
    actual_hours = standard_hours * variation

    return {
      "base_salary": monthly_base.quantize(Decimal("0.01")),
      "hours_worked": actual_hours.quantize(Decimal("0.01")),
    }

  def calculate_commission(
    self, employee_data: Dict, period_date: datetime
  ) -> Decimal:
    """Calculate commission based on role and sales targets"""
    if "sales" not in employee_data["role"].lower():
      return Decimal("0.00")

    # Base commission calculation on quoted average
    base_commission = Decimal(
      str(employee_data["compensation"]["baseSalary"])
    ) * Decimal("0.08")

    # Add seasonal variation
    month = period_date.month
    seasonal_factor = Decimal("1.0")
    if month in [3, 6, 9, 12]:  # Quarter ends
      seasonal_factor = Decimal("1.3")
    elif month in [1, 7]:  # Slow months
      seasonal_factor = Decimal("0.7")

    return (base_commission * seasonal_factor).quantize(Decimal("0.01"))

  def calculate_bonus(self, employee_data: Dict, period_date: datetime) -> Decimal:
    """Calculate bonus payments based on employee level and period"""
    if "bonus" not in employee_data["compensation"]:
      return Decimal("0.00")

    # Parse bonus potential
    bonus_str = employee_data["compensation"]["bonus"]
    if "Up to" in bonus_str and "of base" in bonus_str:
      max_percent = Decimal(bonus_str.split("%")[0].split()[-1]) / 100
      base_salary = Decimal(str(employee_data["compensation"]["baseSalary"]))

      # Distribute annual bonus across December and June
      if period_date.month == 12:
        return (base_salary * max_percent * Decimal("0.7")).quantize(
          Decimal("0.01")
        )
      elif period_date.month == 6:
        return (base_salary * max_percent * Decimal("0.3")).quantize(
          Decimal("0.01")
        )

    return Decimal("0.00")

  def calculate_taxes(self, gross_pay: Decimal) -> Dict:
    """Calculate all tax withholdings"""
    annual_equivalent = gross_pay * 12
    federal_tax = Decimal("0.00")

    # Calculate federal tax using brackets
    for lower, upper, rate in self.tax_rates["federal"]["brackets"]:
      # Convert bracket values to Decimal
      lower = Decimal(str(lower))
      upper = Decimal(str(upper))
      rate = Decimal(str(rate))

      if annual_equivalent <= lower:
        break
      taxable_in_bracket = min(annual_equivalent - lower, upper - lower)
      federal_tax += taxable_in_bracket * rate

    # Convert annual tax to monthly
    federal_tax = (federal_tax / 12).quantize(Decimal("0.01"))

    # Calculate other taxes
    social_security = (
      gross_pay * Decimal(str(self.tax_rates["social_security"]))
    ).quantize(Decimal("0.01"))
    medicare = (gross_pay * Decimal(str(self.tax_rates["medicare"]))).quantize(
      Decimal("0.01")
    )
    state_tax = (gross_pay * Decimal(str(self.tax_rates["state"]))).quantize(
      Decimal("0.01")
    )

    return {
      "federal": federal_tax,
      "social_security": social_security,
      "medicare": medicare,
      "state": state_tax,
      "total": federal_tax + social_security + medicare + state_tax,
    }

  def calculate_deductions(self, employee_data: Dict, gross_pay: Decimal) -> Dict:
    """Calculate all benefit deductions"""
    deductions = {}

    # Health Insurance
    if "Health insurance" in employee_data["compensation"]["benefits"]:
      deductions["health_insurance"] = Decimal(
        "250.00"
      )  # Example monthly premium

    # 401k
    if any(
      "401k" in benefit for benefit in employee_data["compensation"]["benefits"]
    ):
      contribution_rate = Decimal("0.06")  # Example 6% contribution
      deductions["401k"] = (gross_pay * contribution_rate).quantize(
        Decimal("0.01")
      )

    # Life Insurance
    if any(
      "life insurance" in benefit.lower()
      for benefit in employee_data["compensation"]["benefits"]
    ):
      deductions["life_insurance"] = Decimal("35.00")

    return deductions

  def generate_paystub(
    self, employee_data: Dict, period_date: datetime, output_path: str
  ):
    """Generate PDF paystub"""
    # Calculate period amounts
    base_period = self.calculate_payroll_period(
      employee_data["compensation"]["baseSalary"], period_date
    )

    commission = self.calculate_commission(employee_data, period_date)
    bonus = self.calculate_bonus(employee_data, period_date)

    gross_pay = base_period["base_salary"] + commission + bonus

    # Calculate deductions and taxes
    taxes = self.calculate_taxes(gross_pay)
    deductions = self.calculate_deductions(employee_data, gross_pay)

    # Calculate net pay
    total_deductions = sum(deductions.values())
    net_pay = gross_pay - taxes["total"] - total_deductions

    # Create PDF
    pdf = FPDF()
    pdf.add_page()

    # Company Header
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "PAYROLL STATEMENT", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 5, "ServiceTech Solutions", ln=True, align="C")
    pdf.cell(
      0, 5, "Pay Period: " + period_date.strftime("%B %Y"), ln=True, align="C"
    )
    pdf.ln(5)

    # Employee Information
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Employee Information", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 5, f"Name: {employee_data['name']}", ln=True)
    pdf.cell(0, 5, f"ID: {employee_data['id']}", ln=True)
    pdf.cell(0, 5, f"Department: {employee_data['department']}", ln=True)
    pdf.cell(0, 5, f"Role: {employee_data['role']}", ln=True)
    pdf.ln(5)

    # Earnings
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Earnings", ln=True)
    pdf.set_font("Arial", "", 10)

    col_width = 47.5
    pdf.cell(col_width, 10, "Description", 1)
    pdf.cell(col_width, 10, "Hours/Units", 1)
    pdf.cell(col_width, 10, "Rate", 1)
    pdf.cell(col_width, 10, "Amount", 1, ln=True)

    pdf.cell(col_width, 10, "Regular Pay", 1)
    pdf.cell(col_width, 10, f"{base_period['hours_worked']:.2f}", 1)
    pdf.cell(
      col_width,
      10,
      f"${(base_period['base_salary']/base_period['hours_worked']):.2f}",
      1,
    )
    pdf.cell(col_width, 10, f"${base_period['base_salary']:.2f}", 1, ln=True)

    if commission > 0:
      pdf.cell(col_width, 10, "Commission", 1)
      pdf.cell(col_width, 10, "", 1)
      pdf.cell(col_width, 10, "", 1)
      pdf.cell(col_width, 10, f"${commission:.2f}", 1, ln=True)

    if bonus > 0:
      pdf.cell(col_width, 10, "Bonus", 1)
      pdf.cell(col_width, 10, "", 1)
      pdf.cell(col_width, 10, "", 1)
      pdf.cell(col_width, 10, f"${bonus:.2f}", 1, ln=True)

    pdf.ln(5)

    # Taxes
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Taxes", ln=True)
    pdf.set_font("Arial", "", 10)

    for tax_type, amount in taxes.items():
      if tax_type != "total":
        pdf.cell(95, 10, tax_type.replace("_", " ").title(), 1)
        pdf.cell(95, 10, f"${amount:.2f}", 1, ln=True)

    pdf.ln(5)

    # Deductions
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Deductions", ln=True)
    pdf.set_font("Arial", "", 10)

    for deduction_type, amount in deductions.items():
      pdf.cell(95, 10, deduction_type.replace("_", " ").title(), 1)
      pdf.cell(95, 10, f"${amount:.2f}", 1, ln=True)

    pdf.ln(5)

    # Summary
    pdf.set_font("Arial", "B", 12)
    pdf.cell(95, 10, "Gross Pay", 1)
    pdf.cell(95, 10, f"${gross_pay:.2f}", 1, ln=True)
    pdf.cell(95, 10, "Total Deductions", 1)
    pdf.cell(95, 10, f"${(taxes['total'] + total_deductions):.2f}", 1, ln=True)
    pdf.cell(95, 10, "Net Pay", 1)
    pdf.cell(95, 10, f"${net_pay:.2f}", 1, ln=True)

    # Save the PDF
    pdf.output(output_path)


  def generate_department_payroll_report(self, period_date: datetime, output_path: str):
      """Generate department-wise payroll summary report"""
      employees = self.load_employee_data()
      department_totals, department_headcount = self.initialize_department_trackers(employees)

      department_totals, department_headcount = self.calculate_department_totals(
          employees, department_totals, department_headcount, period_date
      )

      self.generate_pdf_report(department_totals, department_headcount, period_date, output_path)

  def initialize_department_trackers(self, employees: Dict) -> Tuple[Dict, Dict]:
      """Initialize department_totals and department_headcount dictionaries"""
      department_totals = {}
      department_headcount = {}

      for employee in employees["employees"]:
          dept = employee["department"]
          if dept not in department_totals:
              department_totals[dept] = {
                  "base_salary": Decimal("0.00"),
                  "commission": Decimal("0.00"),
                  "bonus": Decimal("0.00"),
                  "taxes": Decimal("0.00"),
                  "deductions": Decimal("0.00"),
                  "net_pay": Decimal("0.00"),
                  "total_cost": Decimal("0.00"),  # Including employer taxes/contributions
              }
              department_headcount[dept] = 0
      return department_totals, department_headcount

  def calculate_department_totals(
      self,
      employees: Dict,
      department_totals: Dict,
      department_headcount: Dict,
      period_date: datetime
  ) -> Tuple[Dict, Dict]:
      """Calculate payroll totals for each department"""
      for employee in employees["employees"]:
          dept = employee["department"]
          department_headcount[dept] += 1

          # Calculate all components
          base_period = self.calculate_payroll_period(
              employee["compensation"]["baseSalary"], period_date
          )
          commission = self.calculate_commission(employee, period_date)
          bonus = self.calculate_bonus(employee, period_date)

          gross_pay = base_period["base_salary"] + commission + bonus
          taxes = self.calculate_taxes(gross_pay)
          deductions = self.calculate_deductions(employee, gross_pay)

          total_deductions = sum(deductions.values())
          net_pay = gross_pay - taxes["total"] - total_deductions

          # Add employer contributions (e.g., matching 401k, employer portion of FICA)
          employer_fica = (gross_pay * Decimal("0.0765")).quantize(Decimal("0.01"))  # 7.65% for SS and Medicare
          employer_401k = self.calculate_employer_401k(employee, gross_pay)
          total_cost = gross_pay + employer_fica + employer_401k

          # Update department totals
          department_totals[dept]["base_salary"] += base_period["base_salary"]
          department_totals[dept]["commission"] += commission
          department_totals[dept]["bonus"] += bonus
          department_totals[dept]["taxes"] += taxes["total"]
          department_totals[dept]["deductions"] += total_deductions
          department_totals[dept]["net_pay"] += net_pay
          department_totals[dept]["total_cost"] += total_cost

      return department_totals, department_headcount

  def calculate_employer_401k(self, employee: Dict, gross_pay: Decimal) -> Decimal:
      """Calculate employer 401k contributions"""
      for benefit in employee["compensation"].get("benefits", []):
          if "401k" in benefit:
              return (gross_pay * Decimal("0.06")).quantize(Decimal("0.01"))
      return Decimal("0.00")

  def generate_pdf_report(
      self,
      department_totals: Dict,
      department_headcount: Dict,
      period_date: datetime,
      output_path: str
  ):
      """Generate PDF report based on department payroll data"""
      pdf = FPDF()
      pdf.add_page("L")  # Landscape orientation for wider tables

      # Set page margins to maximize usable space
      pdf.set_margins(10, 10, 10)

      # Calculate available width
      page_width = pdf.w - 20  # Total width minus margins

      # Header
      pdf.set_font("Arial", "B", 14)  # Slightly smaller header
      pdf.cell(0, 10, "DEPARTMENT PAYROLL SUMMARY REPORT", ln=True, align="C")
      pdf.set_font("Arial", "", 10)
      pdf.cell(0, 5, f"Period: {period_date.strftime('%B %Y')}", ln=True, align="C")
      pdf.ln(5)

      # Define column widths (total should equal page_width)
      col_widths = {
          "Department": 35,  # Reduced from 45
          "Headcount": 20,
          "Base Salary": 34,  # Slightly increased
          "Commission": 34,
          "Bonus": 34,
          "Taxes": 34,
          "Deductions": 34,
          "Net Pay": 34,
          "Total Cost": 34,
      }

      # Table Header
      pdf.set_font("Arial", "B", 8)  # Smaller font for header
      for title, width in col_widths.items():
          pdf.cell(width, 8, title, 1, align="C")
      pdf.ln()

      # Table Data
      pdf.set_font("Arial", "", 8)  # Smaller font for data
      company_totals = {key: Decimal("0.00") for key in department_totals[next(iter(department_totals))].keys()}
      total_headcount = 0

      for dept, totals in department_totals.items():
          pdf.cell(col_widths["Department"], 8, dept, 1)
          pdf.cell(col_widths["Headcount"], 8, str(department_headcount[dept]), 1, align="R")

          for key, label in [
              ("base_salary", "Base Salary"),
              ("commission", "Commission"),
              ("bonus", "Bonus"),
              ("taxes", "Taxes"),
              ("deductions", "Deductions"),
              ("net_pay", "Net Pay"),
              ("total_cost", "Total Cost"),
          ]:
              pdf.cell(col_widths[label], 8, f"${totals[key]:,.2f}", 1, align="R")
              company_totals[key] += totals[key]

          total_headcount += department_headcount[dept]
          pdf.ln()

      # Company Totals
      pdf.set_font("Arial", "B", 8)
      pdf.cell(col_widths["Department"], 8, "TOTAL", 1)
      pdf.cell(col_widths["Headcount"], 8, str(total_headcount), 1, align="R")

      for key, label in [
          ("base_salary", "Base Salary"),
          ("commission", "Commission"),
          ("bonus", "Bonus"),
          ("taxes", "Taxes"),
          ("deductions", "Deductions"),
          ("net_pay", "Net Pay"),
          ("total_cost", "Total Cost"),
      ]:
          pdf.cell(col_widths[label], 8, f"${company_totals[key]:,.2f}", 1, align="R")

      # Statistics section with adjusted positioning
      pdf.ln(15)
      pdf.set_font("Arial", "B", 10)
      pdf.cell(0, 8, "Key Statistics", ln=True)
      pdf.set_font("Arial", "", 9)

      avg_cost_per_employee = (
          company_totals["total_cost"] / Decimal(str(total_headcount))
      ).quantize(Decimal("0.01"))
      total_compensation_ratio = (
          (company_totals["total_cost"] / company_totals["base_salary"]).quantize(Decimal("0.01"))
      )

      # Use shorter labels and two-column layout for statistics
      stats_col_width = page_width / 2
      pdf.cell(stats_col_width, 6, f"Avg Cost/Employee: ${avg_cost_per_employee:,.2f}", ln=False)
      pdf.cell(stats_col_width, 6, f"Total Comp Ratio: {total_compensation_ratio:,.2f}", ln=True)

      # Save the PDF
      pdf.output(output_path)


def generate_payrolls():
  generator = PayrollGenerator()

  # Load employee data
  employees = generator.load_employee_data()

  print(
    f"Generating payroll documents for {len(employees['employees'])} employees..."
  )

  # Process each employee
  for employee in employees["employees"]:
    print(f"\nProcessing payroll for {employee['name']}")

    # Generate monthly paystubs from start date through 2024
    start_date = datetime.strptime("2023-01-01", "%Y-%m-%d")  # Example start date
    end_date = datetime(2024, 12, 31)
    current_date = start_date

    while current_date <= end_date:
      try:
        # Create directory structure
        output_dir = Path(
          f"company_documents/payroll/{current_date.year}/{current_date.strftime('%m')}"
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate paystub
        output_path = (
          output_dir
          / f"paystub_{employee['id']}_{current_date.strftime('%Y%m')}.pdf"
        )
        generator.generate_paystub(employee, current_date, str(output_path))

        # Generate department report for each month
        dept_report_path = (
          output_dir
          / f"department_summary_{current_date.strftime('%Y%m')}.pdf"
        )
        generator.generate_department_payroll_report(
          current_date, str(dept_report_path)
        )

        print(f"✓ Generated paystub for {current_date.strftime('%Y-%m')}")

      except Exception as e:
        print(
          f"✗ Error generating paystub for {current_date.strftime('%Y-%m')}: {str(e)}"
        )

      current_date += relativedelta(months=1)


if __name__ == "__main__":
  generate_payrolls()
