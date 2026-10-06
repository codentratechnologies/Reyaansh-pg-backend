# Expenses API Documentation

This document outlines the API endpoints, methods, and payload structures for managing Expenses within the PG Management application. 

**Base URL path:** `/api/pg/add_expense/`  
**Authentication:** `Bearer <JWT_TOKEN>` is required for all requests.

---

## 1. Add Expense

Creates a new expense record in the Firebase Realtime Database. The backend automatically generates a sequential ID (e.g., `EXP001`).

- **Endpoint**: `/api/pg/add_expense/`
- **Method**: `POST`
- **Content-Type**: `application/json`

### Request Payload

| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `expense_name` | String | Yes | Name or title of the expense (You can also pass this as `name`). |
| `amount` | Number | Yes | The cost/amount of the expense. |
| `pg_name` | String | No | The ID of the PG this expense is associated with. |
| `description` | String | No | Additional details or notes about the expense. |
| `expense_date` | String | No | Date when the expense occurred (e.g., `2026-10-06`). |

**Example Request:**
```json
{
    "expense_name": "Electricity Bill",
    "amount": 2500,
    "pg_name": "PG Sera Estate",
    "description": "Monthly electricity bill for October",
    "expense_date": "2026-10-06"
}
```

**Example Success Response (201 Created):**
```json
{
    "message": "Expense added successfully",
    "expense_id": "EXP005",
    "data": {
        "expense_id": "EXP005",
        "expense_name": "Electricity Bill",
        "amount": 2500.0,
        "created_at": "2026-10-06 20:45:00",
        "pg_name": "PG Sera Estate",
        "description": "Monthly electricity bill for October",
        "expense_date": "2026-10-06"
    }
}
```

---

## 2. Fetch Expenses

Retrieves expenses. It can fetch a specific expense, all expenses for a specific PG, or all expenses in the system.

- **Endpoint**: `/api/pg/add_expense/`
- **Method**: `GET`

### Query Parameters

| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `expense_id` | String | No | Fetch a single specific expense by its ID. |
| `pg_name` | String | No | Filter all expenses associated with a specific PG. |

*(Note: These can also be sent via headers instead of query parameters).*

**Example 1: Fetch all expenses for a specific PG**
`GET /api/pg/add_expense/?pg_name=PG Sera Estate`

**Example 2: Fetch a single expense**
`GET /api/pg/add_expense/?expense_id=EXP005`

**Example Success Response (List) (200 OK):**
```json
[
    {
        "expense_id": "EXP005",
        "expense_name": "Electricity Bill",
        "amount": 2500.0,
        "created_at": "2026-10-06 20:45:00",
        "pg_name": "PG Sera Estate",
        "description": "Monthly electricity bill for October",
        "expense_date": "2026-10-06"
    }
]
```

---

## 3. Update Expense

Updates an existing expense. You only need to pass the fields you wish to change.

- **Endpoint**: `/api/pg/add_expense/`
- **Method**: `PUT`
- **Content-Type**: `application/json`

### Request Payload

| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `expense_id` | String | Yes | The ID of the expense to update. |
| `expense_name` | String | No | Updated name of the expense. |
| `amount` | Number | No | Updated amount. |
| `pg_name` | String | No | Updated PG name. |
| `description` | String | No | Updated description. |
| `expense_date` | String | No | Updated expense date. |

**Example Request:**
```json
{
    "expense_id": "EXP005",
    "amount": 2800,
    "description": "Electricity bill included late fees"
}
```

**Example Success Response (200 OK):**
```json
{
    "message": "Expense updated successfully",
    "expense_id": "EXP005",
    "updated_data": {
        "amount": 2800.0,
        "description": "Electricity bill included late fees",
        "updated_at": "2026-10-06 20:50:00"
    }
}
```

---

## 4. Delete Expense

Deletes an expense permanently from the database.

- **Endpoint**: `/api/pg/add_expense/`
- **Method**: `DELETE`

### Request Parameters / Payload

| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `expense_id` | String | Yes | The ID of the expense to delete. |

*(Note: `expense_id` can be sent in the JSON body payload, as a URL query parameter, or in the Headers).*

**Example Request (JSON Body):**
```json
{
    "expense_id": "EXP005"
}
```

**Example Success Response (200 OK):**
```json
{
    "message": "Expense EXP005 deleted successfully"
}
```
