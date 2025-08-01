from celery import shared_task
import pandas as pd
from .models import Customer, Loan
from django.utils.dateparse import parse_date
from datetime import datetime

@shared_task
def ingest_data():
    """
    Celery task to ingest customer and loan data from CSV files.
    """
    # Ingest Customer Data
    try:
        customer_df = pd.read_csv('customer_data.csv')
        for _, row in customer_df.iterrows():
            if pd.notna(row['Customer ID']):
                Customer.objects.update_or_create(
                    customer_id=int(row['Customer ID']),
                    defaults={
                        'first_name': row['First Name'],
                        'last_name': row['Last Name'],
                        'age': row['Age'],
                        'phone_number': row['Phone Number'],
                        'monthly_salary': row['Monthly Salary'],
                        'approved_limit': row['Approved Limit'],
                    }
                )
    except FileNotFoundError:
        return "customer_data.csv not found."

    # Ingest Loan Data
    try:
        loan_df = pd.read_csv('loan_data.csv')
        for index, row in loan_df.iterrows():
            # Skip row if essential IDs or dates are missing
            if pd.notna(row['Customer ID']) and pd.notna(row['Loan ID']) and pd.notna(row['Date of Approval']) and pd.notna(row['End Date']):
                try:
                    start_date = datetime.strptime(str(row['Date of Approval']), '%d-%m-%Y').date()
                    end_date = datetime.strptime(str(row['End Date']), '%d-%m-%Y').date()
                except (ValueError, TypeError):
                    # Add logging for parse failure
                    print(f"Skipping row {index+2}: Date parsing failed.")
                    continue

                try:
                    customer = Customer.objects.get(customer_id=int(row['Customer ID']))
                    Loan.objects.update_or_create(
                        loan_id=int(row['Loan ID']),
                        defaults={
                            'customer': customer,
                            'loan_amount': row['Loan Amount'],
                            'tenure': row['Tenure'],
                            'interest_rate': row['Interest Rate'],
                            'monthly_repayment': row['Monthly payment'],
                            'emis_paid_on_time': row['EMIs paid on Time'],
                            'start_date': start_date,
                            'end_date': end_date,
                            'status': 'COMPLETED' if row['EMIs paid on Time'] == row['Tenure'] else 'ACTIVE'
                        }
                    )
                except Customer.DoesNotExist:
                    # Log or handle cases where a customer for a loan doesn't exist
                    print(f"Skipping row {index+2}: Non-existent customer ID: {int(row['Customer ID'])}")
                    pass
            else:
                # Add logging for missing data
                print(f"Skipping row {index+2}: Missing required data (CustomerID, LoanID, or Dates).")

    except FileNotFoundError:
        return "loan_data.csv not found."

    # Update current_debt for all customers
    for customer in Customer.objects.all():
        customer.update_current_debt()

    return "Data ingestion completed successfully."
