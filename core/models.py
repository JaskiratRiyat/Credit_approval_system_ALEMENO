from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import math


class Customer(models.Model):
    customer_id = models.IntegerField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    age = models.PositiveIntegerField(
        validators=[MinValueValidator(18), MaxValueValidator(100)]
    )
    phone_number = models.CharField(max_length=15, unique=True)
    monthly_salary = models.PositiveIntegerField()
    approved_limit = models.PositiveIntegerField()
    current_debt = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customers'
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['customer_id']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} (ID: {self.customer_id})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def calculate_approved_limit(self):
        """
        Calculate approved limit based on salary: 36 * monthly_salary (rounded to nearest lakh)
        """
        limit = 36 * self.monthly_salary
        return round(limit / 100000) * 100000

    def update_current_debt(self):
        """
        Calculate and update the customer's current debt based on active loans.
        """
        total_debt = sum(loan.outstanding_amount for loan in self.loans.filter(status='ACTIVE'))
        self.current_debt = total_debt
        self.save(update_fields=['current_debt', 'updated_at'])

    def save(self, *args, **kwargs):
        if not self.approved_limit:
            self.approved_limit = self.calculate_approved_limit()
        super().save(*args, **kwargs)


class Loan(models.Model):
    """
    Loan model based on loan_data.csv structure and requirements
    """
    LOAN_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('DEFAULTED', 'Defaulted'),
    ]

    loan_id = models.IntegerField(primary_key=True)
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.CASCADE, 
        related_name='loans'
    )
    loan_amount = models.DecimalField(max_digits=12, decimal_places=2)
    tenure = models.PositiveIntegerField(help_text="Loan tenure in months")
    interest_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(50)]
    )
    monthly_repayment = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Monthly EMI amount"
    )
    emis_paid_on_time = models.PositiveIntegerField(default=0)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=10, 
        choices=LOAN_STATUS_CHOICES, 
        default='ACTIVE'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loans'
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['loan_id']),
        ]

    def __str__(self):
        return f"Loan {self.loan_id} - {self.customer.full_name} - ₹{self.loan_amount}"

    @property
    def remaining_emis(self):
        """Calculate remaining EMIs"""
        return max(0, self.tenure - self.emis_paid_on_time)

    @property
    def outstanding_amount(self):
        """Calculate outstanding loan amount"""
        if self.status == 'COMPLETED':
            return Decimal('0.00')
        return Decimal(self.remaining_emis) * self.monthly_repayment

    @property
    def payment_completion_percentage(self):
        """Calculate payment completion percentage"""
        if self.tenure == 0:
            return 0
        return (self.emis_paid_on_time / self.tenure) * 100

    def calculate_monthly_emi(self):
        """
        Calculate monthly EMI using compound interest formula
        EMI = P * r * (1+r)^n / ((1+r)^n - 1)
        Where P = Principal, r = monthly interest rate, n = tenure in months
        """
        principal = float(self.loan_amount)
        monthly_rate = float(self.interest_rate) / (12 * 100)  
        
        if monthly_rate == 0:  
            return Decimal(str(principal / self.tenure))
        
        emi = principal * monthly_rate * (1 + monthly_rate) ** self.tenure / ((1 + monthly_rate) ** self.tenure - 1)
        return Decimal(str(round(emi, 2)))

    def save(self, *args, **kwargs):
        if not self.monthly_repayment:
            self.monthly_repayment = self.calculate_monthly_emi()
        super().save(*args, **kwargs)


class CreditScore(models.Model):
    """
    Model to store and track customer credit scores
    """
    customer = models.OneToOneField(
        Customer, 
        on_delete=models.CASCADE, 
        related_name='credit_score'
    )
    score = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Credit score out of 100"
    )
    last_calculated = models.DateTimeField(auto_now=True)
    past_loans_paid_on_time_score = models.PositiveIntegerField(default=0)
    loan_activity_current_year_score = models.PositiveIntegerField(default=0)
    loan_approved_volume_score = models.PositiveIntegerField(default=0)
    number_of_loans_taken_score = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'credit_scores'

    def __str__(self):
        return f"{self.customer.full_name} - Credit Score: {self.score}"
