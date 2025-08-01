from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import (
    RegisterRequestSerializer, RegisterResponseSerializer, 
    EligibilityRequestSerializer, EligibilityResponseSerializer,
    CreateLoanRequestSerializer, CreateLoanResponseSerializer,
    ViewLoanResponseSerializer, ViewLoansResponseSerializer
)
from .models import Customer, Loan
from django.utils import timezone
from datetime import timedelta
from .utils import calculate_credit_score
import math
from django.db.models import Max
from decimal import Decimal


class RegisterView(APIView):
    """
    API endpoint for registering a new customer.
    """
    def post(self, request):
        serializer = RegisterRequestSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            # Check if customer with phone number already exists
            if Customer.objects.filter(phone_number=data['phone_number']).exists():
                return Response({'error': 'Customer with this phone number already exists.'}, status=status.HTTP_400_BAD_REQUEST)

            # Calculate approved limit: 36 * monthly_salary, rounded to nearest lakh
            monthly_salary = data['monthly_income']
            approved_limit = round(36 * monthly_salary / 100000) * 100000

            # Get the next available customer_id
            last_customer_id = Customer.objects.aggregate(max_id=Max('customer_id'))['max_id']
            new_customer_id = (last_customer_id or 0) + 1

            # Create customer instance
            customer = Customer.objects.create(
                customer_id=new_customer_id,
                first_name=data['first_name'],
                last_name=data['last_name'],
                age=data['age'],
                monthly_salary=monthly_salary,
                phone_number=data['phone_number'],
                approved_limit=approved_limit
            )
            
            # Prepare and return the response
            response_serializer = RegisterResponseSerializer(customer)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckEligibilityView(APIView):
    """
    API endpoint to check loan eligibility for a customer.
    """
    def post(self, request):
        serializer = EligibilityRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        customer_id = data['customer_id']
        loan_amount = data['loan_amount']
        interest_rate = data['interest_rate']
        tenure = data['tenure']

        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)

        credit_score = calculate_credit_score(customer)
        
        # Rule 1: Check current debt vs approved limit
        if customer.current_debt > customer.approved_limit:
            approval = False

        # Rule 2: Credit score based approval and interest rate correction
        corrected_interest_rate = interest_rate
        if credit_score > 50:
            approval = True
        elif 30 < credit_score <= 50:
            approval = True
            if corrected_interest_rate < 12.0:
                 corrected_interest_rate = 12.0
        elif 10 < credit_score <= 30:
            approval = True
            if corrected_interest_rate < 16.0:
                corrected_interest_rate = 16.0
        else: # credit_score <= 10
            approval = False

        # Rule 3: Check if sum of all current EMIs > 50% of monthly salary
        current_loans = Loan.objects.filter(customer=customer, status='ACTIVE')
        total_current_emi = sum([loan.monthly_repayment for loan in current_loans])
        
        # Calculate EMI for the new loan
        new_emi = (loan_amount * (corrected_interest_rate / 1200) * (1 + (corrected_interest_rate / 1200))**tenure) / ((1 + (corrected_interest_rate / 1200))**tenure - 1)

        if total_current_emi + Decimal(str(new_emi)) > customer.monthly_salary * 0.5:
            approval = False

        response_data = {
            'customer_id': customer_id,
            'approval': approval,
            'interest_rate': interest_rate,
            'corrected_interest_rate': corrected_interest_rate if approval else None,
            'tenure': tenure,
            'monthly_installment': round(new_emi, 2) if approval else None
        }

        return Response(response_data, status=status.HTTP_200_OK)


class CreateLoanView(APIView):
    """
    API endpoint to create a new loan for a customer.
    """
    def post(self, request):
        serializer = CreateLoanRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        customer_id = data['customer_id']
        loan_amount = data['loan_amount']
        interest_rate = data['interest_rate']
        tenure = data['tenure']

        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)

        # Perform eligibility check
        credit_score = calculate_credit_score(customer)
        approval = True
        corrected_interest_rate = interest_rate

        if customer.current_debt > customer.approved_limit:
            approval = False

        if credit_score > 50:
            pass # Approved with given interest rate
        elif 30 < credit_score <= 50:
            if corrected_interest_rate < 12.0:
                corrected_interest_rate = 12.0
        elif 10 < credit_score <= 30:
            if corrected_interest_rate < 16.0:
                corrected_interest_rate = 16.0
        else: # credit_score <= 10
            approval = False

        current_loans = Loan.objects.filter(customer=customer, status='ACTIVE')
        total_current_emi = sum([loan.monthly_repayment for loan in current_loans])
        new_emi = (loan_amount * (corrected_interest_rate / 1200) * (1 + (corrected_interest_rate / 1200))**tenure) / ((1 + (corrected_interest_rate / 1200))**tenure - 1)

        if total_current_emi + Decimal(str(new_emi)) > customer.monthly_salary * 0.5:
            approval = False

        # Create loan if approved
        if approval:
            # Get the next available loan_id
            last_loan_id = Loan.objects.aggregate(max_id=Max('loan_id'))['max_id']
            new_loan_id = (last_loan_id or 0) + 1

            loan = Loan.objects.create(
                loan_id=new_loan_id,
                customer=customer,
                loan_amount=loan_amount,
                interest_rate=corrected_interest_rate,
                tenure=tenure,
                monthly_repayment=round(new_emi, 2),
                start_date=timezone.now().date(),
                end_date=timezone.now().date() + timedelta(days=30*tenure),
                status='ACTIVE'
            )
            # Update customer's current debt
            customer.current_debt += loan_amount
            customer.save()

            response_data = {
                'loan_id': loan.loan_id,
                'customer_id': customer.customer_id,
                'loan_approved': True,
                'message': 'Loan approved and created successfully.',
                'monthly_installment': loan.monthly_repayment
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            response_data = {
                'loan_id': None,
                'customer_id': customer.customer_id,
                'loan_approved': False,
                'message': 'Loan application was not approved based on eligibility criteria.',
                'monthly_installment': None
            }
            return Response(response_data, status=status.HTTP_200_OK)


class ViewLoanView(APIView):
    """
    API endpoint to view details of a specific loan.
    """
    def get(self, request, loan_id):
        try:
            loan = Loan.objects.get(loan_id=loan_id)
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ViewLoanResponseSerializer(loan)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ViewLoansView(APIView):
    """
    API endpoint to view all loans for a specific customer.
    """
    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)

        loans = Loan.objects.filter(customer=customer)
        serializer = ViewLoansResponseSerializer(loans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
