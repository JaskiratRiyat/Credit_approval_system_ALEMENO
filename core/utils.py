from .models import Loan, Customer
from django.utils import timezone
from django.db.models import Sum, Count

def calculate_credit_score(customer: Customer) -> int:
    """
    Calculates the credit score for a given customer based on historical loan data.
    """
    # Component 1: Past Loans paid on time vs. total EMIs
    past_loans = Loan.objects.filter(customer=customer)
    total_emis_paid_on_time = past_loans.aggregate(total=Sum('emis_paid_on_time'))['total'] or 0
    total_tenure_sum = past_loans.aggregate(total=Sum('tenure'))['total'] or 0

    # A simple ratio for on-time payments. More complex logic can be added.
    # For now, let's assume a score based on the percentage of on-time payments.
    if total_tenure_sum > 0:
        payment_ratio = total_emis_paid_on_time / total_tenure_sum
        score_from_payments = int(payment_ratio * 30) # Max 30 points
    else:
        score_from_payments = 30 # No loans, perfect record so far

    # Component 2: Number of loans taken in the past
    num_loans = past_loans.count()
    score_from_num_loans = min(num_loans * 5, 20) # Max 20 points

    # Component 3: Loan activity in the current year (less is better)
    current_year_loans = past_loans.filter(start_date__year=timezone.now().year).count()
    score_from_activity = max(15 - (current_year_loans * 5), 0) # Max 15 points

    # Component 4: Loan approved volume (lower is better)
    total_loan_volume = past_loans.aggregate(total=Sum('loan_amount'))['total'] or 0
    if total_loan_volume > customer.approved_limit * 2: # High debt ratio
        score_from_volume = 0
    elif total_loan_volume > customer.approved_limit:
        score_from_volume = 15
    else:
        score_from_volume = 35 # Max 35 points

    # Final credit score
    credit_score = score_from_payments + score_from_num_loans + score_from_activity + score_from_volume
    
    # Ensure score is between 0 and 100
    return max(0, min(credit_score, 100))
