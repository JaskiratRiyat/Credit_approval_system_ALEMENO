# Credit Approval System Backend

## How to Run

1.  **Build and start the services:**

    ```bash
    docker-compose up --build -d
    ```

2.  **Ingest the initial data:**

    Open a new terminal and run the following command to execute the data ingestion task inside the running `web` container.

    ```bash
    docker-compose exec web python manage.py ingest_data
    ```

The backend API will be available at `http://127.0.0.1:8000/api/`.

## Testing the API Endpoints

Here are sample `curl` commands to test the 5 API endpoints.

### 1. Register a new customer

```bash
curl -X POST http://127.0.0.1:8000/api/register/ \
-H "Content-Type: application/json" \
-d '{
    "first_name": "Jaskirat Test",
    "last_name": "Future Alemeno intern",
    "age": 20,
    "monthly_income": 60000,
    "phone_number": "1234567890"
}'
```

### 2. Check loan eligibility

```bash
curl -X POST http://127.0.0.1:8000/api/check-eligibility/ \
-H "Content-Type: application/json" \
-d '{
    "customer_id": 1,
    "loan_amount": 10000,
    "interest_rate": 12.5,
    "tenure": 12
}'
```

### 3. Create a new loan

```bash
curl -X POST http://127.0.0.1:8000/api/create-loan/ \
-H "Content-Type: application/json" \
-d '{
    "customer_id": 1,
    "loan_amount": 10000,
    "interest_rate": 12.5,
    "tenure": 12
}'
```

### 4. View details of a specific loan

Replace `<loan_id>` with an actual loan ID from your database.

```bash
curl -X GET http://127.0.0.1:8000/api/view-loan/<loan_id>/
```

### 5. View all loans for a specific customer

Replace `<customer_id>` with an actual customer ID from your database.

```bash
curl -X GET http://127.0.0.1:8000/api/view-loans/<customer_id>/

### You can use postman to test the API endpoints.