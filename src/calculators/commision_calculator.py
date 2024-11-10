import json
from datetime import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta

class CommissionCalculator:
  def __init__(self, sales_data_path="seed_data/sales_performance.json"):
    self.sales_data = self.load_sales_data(sales_data_path)

  def load_sales_data(self, path):
    """Load sales performance data"""
    with open(path, 'r') as f:
      return json.load(f)

  def get_quarterly_quota(self, date):
    """Get quarterly quota for the given date"""
    year = str(date.year)
    quarter = f"Q{(date.month - 1) // 3 + 1}"
    return self.sales_data['salesPerformance']['quarterlyQuotas'][year][quarter]

  def calculate_quota_attainment(self, sales_rep_id, period_date):
    """Calculate quota attainment for the sales rep"""
    quarterly_quota = self.get_quarterly_quota(period_date)

    # Filter transactions for this rep in this quarter
    quarter_start = period_date.replace(day=1, month=((period_date.month - 1) // 3) * 3 + 1)
    quarter_end = quarter_start + relativedelta(months=3, days=-1)

    rep_transactions = [
      t for t in self.sales_data['salesPerformance']['salesTransactions']
      if (t['salesRepId'] == sales_rep_id and
        quarter_start <= datetime.strptime(t['activityLog']['closedDate'], '%Y-%m-%d') <= quarter_end)
    ]

    # Calculate attainment by deal type
    attainment = {
      'newBusiness': Decimal('0'),
      'renewal': Decimal('0'),
      'upsell': Decimal('0')
    }

    for transaction in rep_transactions:
      deal_type = transaction['dealDetails']['type']
      annual_value = Decimal(str(transaction['dealDetails']['annualValue']))
      attainment[deal_type] += annual_value

    # Calculate percentage attainment
    total_attainment = sum(
      attainment[deal_type] / Decimal(str(quota))
      for deal_type, quota in quarterly_quota.items()
    ) / Decimal('3')

    return attainment, total_attainment

  def calculate_commission(self, sales_rep_id, period_date):
    """Calculate commission for the given period"""
    commission_structure = self.sales_data['salesPerformance']['commissionStructure']

    # Get transactions for this month
    month_start = period_date.replace(day=1)
    month_end = (month_start + relativedelta(months=1, days=-1))

    monthly_transactions = [
      t for t in self.sales_data['salesPerformance']['salesTransactions']
      if (t['salesRepId'] == sales_rep_id and
        month_start <= datetime.strptime(t['activityLog']['closedDate'], '%Y-%m-%d') <= month_end)
    ]

    # Calculate base commission
    base_commission = Decimal('0')
    for transaction in monthly_transactions:
      deal_type = transaction['dealDetails']['type']
      annual_value = Decimal(str(transaction['dealDetails']['annualValue']))
      base_rate = Decimal(str(commission_structure['base'][deal_type]))

      # Add strategic account bonus if applicable
      if transaction['dealDetails'].get('category') == 'strategic':
        base_rate += Decimal(str(commission_structure['specialIncentives']['strategicAccounts']))

      # Add long-term contract bonus
      if transaction['dealDetails']['termLength'] >= 24:
        base_rate += Decimal(str(commission_structure['specialIncentives']['longTermContracts']))

      base_commission += annual_value * base_rate

    # Calculate accelerators based on quota attainment
    _, attainment = self.calculate_quota_attainment(sales_rep_id, period_date)

    # Apply accelerator if quota thresholds are met
    multiplier = Decimal('1.0')
    for accelerator in reversed(commission_structure['accelerators']):
      if attainment >= Decimal(str(accelerator['threshold'])):
        multiplier = Decimal(str(accelerator['multiplier']))
        break

    total_commission = (base_commission * multiplier).quantize(Decimal('0.01'))

    return total_commission

  def calculate_cac(self, client_id, period_date):
    """Calculate Customer Acquisition Cost for a specific client"""
    client_transactions = [
      t for t in self.sales_data['salesPerformance']['salesTransactions']
      if t['clientId'] == client_id
    ]

    if not client_transactions:
      return None

    # Get the first transaction (acquisition)
    first_transaction = min(
      client_transactions,
      key=lambda t: datetime.strptime(t['activityLog']['firstContact'], '%Y-%m-%d')
    )

    # Calculate direct acquisition costs
    acquisition_costs = first_transaction['acquisition']
    marketing_costs = sum(Decimal(str(cost)) for cost in acquisition_costs['marketingCosts'].values())
    sales_costs = sum(Decimal(str(cost)) for cost in acquisition_costs['salesCosts'].values())

    # Calculate allocated marketing costs
    monthly_marketing_budget = Decimal(str(self.sales_data['salesPerformance']['marketingCosts']['digital']['monthlyBudget']))
    num_new_customers = len([
      t for t in self.sales_data['salesPerformance']['salesTransactions']
      if t['dealDetails']['type'] == 'newBusiness' and
      datetime.strptime(t['activityLog']['closedDate'], '%Y-%m-%d').month == period_date.month
    ])

    allocated_marketing = monthly_marketing_budget / Decimal(str(max(1, num_new_customers)))

    total_cac = marketing_costs + sales_costs + allocated_marketing

    return {
      'total_cac': total_cac.quantize(Decimal('0.01')),
      'breakdown': {
        'direct_marketing': marketing_costs.quantize(Decimal('0.01')),
        'direct_sales': sales_costs.quantize(Decimal('0.01')),
        'allocated_marketing': allocated_marketing.quantize(Decimal('0.01'))
      }
    }
