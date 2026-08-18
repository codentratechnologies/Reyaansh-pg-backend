# Dashboard API Documentation

Complete API documentation for the **Dashboard** module in the PG Management Backend system.

---

## Base URL
```http
http://<your-domain-or-localhost>:8000/api
```

---

## Authentication & Authorization

Most dashboard endpoints require JWT authentication. Authentication tokens can be supplied in **either** of two ways:

1. **Authorization Header**:
   ```http
   Authorization: Bearer <your_access_token>
   ```
2. **HTTPOnly Cookie**:
   - `access_token`: Access token (valid for 7 days).
   - `refresh_token`: Refresh token (valid for 15 days).

---

## Summary of Dashboard Endpoints

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/setup-admin/` | Initialize an admin user in Firebase with SHA-256 password | ❌ No |
| `POST` | `/api/login/` | Authenticate admin user and issue access/refresh JWT tokens & cookies | ❌ No |
| `POST` | `/api/refresh/` | Refresh JWT access token using the HTTPOnly refresh cookie | 🍪 Refresh Cookie |
| `POST` | `/api/protected-data/` | Test endpoint to verify JWT authentication | ✅ Yes |
| `GET` | `/api/admin-details/` | Retrieve profile details of the logged-in admin user | ✅ Yes |
| `GET` | `/api/dashboard-kpis/` | Fetch high-level KPI metrics (PGs, Rooms, Members, Occupancy, Rent) | ✅ Yes |
| `GET` | `/api/dashboard-charts/` | Fetch data for dashboard charts (Monthly Rent, Revenue by PG, Occupancy, Statuses) | ✅ Yes |
| `GET` | `/api/dashboard-tables/` | Fetch data for dashboard tables (Upcoming Rent Dues & Recent Payments) | ✅ Yes |
| `GET` | `/api/dashboard-alerts/` | Fetch actionable dashboard alerts (Overdue Rents & Pending Approvals) | ✅ Yes |

---

## Endpoint Details

### 1. Setup Admin User
Create a new admin user in Firebase with SHA-256 encrypted password hashing.

- **HTTP Method:** `POST`
- **Endpoint:** `/api/setup-admin/`
- **Authentication:** None

#### Parameters
- **Headers:** `Content-Type: application/json`
- **Request Body (JSON):**
  | Parameter | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `username` | String | Yes | Admin email or username |
  | `password` | String | Yes | Admin password |

#### Example Request
```json
{
  "username": "admin@pgmanagement.com",
  "password": "SecurePassword123"
}
```

#### Example Responses

- **`201 Created`**
```json
{
  "message": "Admin user created successfully",
  "username": "admin@pgmanagement.com"
}
```

- **`400 Bad Request`**
```json
{
  "detail": "Username and password are required."
}
```

- **`409 Conflict`**
```json
{
  "detail": "Admin with this username/email already exists."
}
```

---

### 2. Admin Login
Authenticate admin credentials, mint access and refresh tokens, and return them in payload and set HTTPOnly cookies.

- **HTTP Method:** `POST`
- **Endpoint:** `/api/login/`
- **Authentication:** None

#### Parameters
- **Headers:** `Content-Type: application/json`
- **Request Body (JSON):**
  | Parameter | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `username` | String | Yes | Admin email or username |
  | `password` | String | Yes | Admin password |

#### Example Request
```json
{
  "username": "admin@pgmanagement.com",
  "password": "SecurePassword123"
}
```

#### Example Response (`200 OK`)
Sets `access_token` and `refresh_token` HTTPOnly cookies automatically.

```json
{
  "message": "Login successful",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Error Responses
- `400 Bad Request`: `{"detail": "Username and password are required."}`
- `401 Unauthorized`: `{"detail": "Invalid credentials"}`
- `403 Forbidden`: `{"detail": "Account is disabled"}`

---

### 3. Refresh Token
Mints a new access token using a valid `refresh_token` supplied in HTTPOnly cookies.

- **HTTP Method:** `POST`
- **Endpoint:** `/api/refresh/`
- **Authentication:** Cookie-based (`refresh_token`)

#### Parameters
- **Cookies:**
  | Cookie Name | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `refresh_token` | String | Yes | Valid JWT Refresh Token |

#### Example Response (`200 OK`)
```json
{
  "message": "Token refreshed successfully",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Error Responses
- `401 Unauthorized`: `{"detail": "Refresh token missing"}` or `{"detail": "Invalid or expired refresh token"}`

---

### 4. Protected Data (Test Endpoint)
A test protected POST endpoint to verify authentication token validity.

- **HTTP Method:** `POST`
- **Endpoint:** `/api/protected-data/`
- **Authentication:** Required (`Bearer Token` or `access_token` Cookie)

#### Parameters
- **Headers:** 
  - `Authorization: Bearer <access_token>`
  - `Content-Type: application/json`
- **Request Body (JSON):**
  | Parameter | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `data` | Any | No | Arbitrary test payload |

#### Example Request Body
```json
{
  "data": "test_payload"
}
```

#### Example Response (`200 OK`)
```json
{
  "message": "Hello admin@pgmanagement.com, this is a protected API.",
  "received_data": "test_payload"
}
```

---

### 5. Admin Details
Retrieves the logged-in admin user's account profile details (excluding password hash).

- **HTTP Method:** `GET`
- **Endpoint:** `/api/admin-details/`
- **Authentication:** Required (`Bearer Token` or `access_token` Cookie)

#### Parameters
- **Headers:** `Authorization: Bearer <access_token>`
- **Query Parameters:** None

#### Example Response (`200 OK`)
```json
{
  "admin_id": 1,
  "email": "admin@pgmanagement.com",
  "is_active": true,
  "last_login": "2026-08-18T13:43:43+05:30"
}
```

#### Error Responses
- `401 Unauthorized`: `{"detail": "User not authenticated"}`
- `404 Not Found`: `{"detail": "Admin not found"}`

---

### 6. Dashboard KPIs
Fetches aggregated top-level KPI metrics across properties, rooms, beds, members, occupancy rates, collected rent, and pending rent.

- **HTTP Method:** `GET`
- **Endpoint:** `/api/dashboard-kpis/`
- **Authentication:** Required (`Bearer Token` or `access_token` Cookie)

#### Parameters
- **Headers:** `Authorization: Bearer <access_token>`
- **Query Parameters:** None

#### Example Response (`200 OK`)
```json
{
  "kpis": {
    "total_pgs": {
      "value": 5,
      "active": 4,
      "inactive": 1
    },
    "total_rooms": 32,
    "total_members": {
      "value": 48,
      "active": 42,
      "notice": 6
    },
    "occupancy_rate": {
      "percentage": 85,
      "occupied": 42,
      "trend": "+2.5%"
    },
    "rent_collected": {
      "amount": 357000,
      "trend": "+12.4%"
    },
    "pending_rent": {
      "amount": 51000,
      "members": 6,
      "trend": "+8.7%"
    }
  }
}
```

---

### 7. Dashboard Charts
Fetches dataset for rendering dashboard visual analytics and charts (Monthly Collection Trend, Revenue by PG, Occupancy Breakdown, and Member Status Distribution).

- **HTTP Method:** `GET`
- **Endpoint:** `/api/dashboard-charts/`
- **Authentication:** Required (`Bearer Token` or `access_token` Cookie)

#### Parameters
- **Headers:** `Authorization: Bearer <access_token>`
- **Query Parameters:** None

#### Example Response (`200 OK`)
```json
{
  "monthly_rent_collection_trend": [
    {
      "month": "Jan",
      "amount": 120000
    },
    {
      "month": "Feb",
      "amount": 145000
    }
  ],
  "revenue_by_pg": [
    {
      "pg_name": "Sunrise PG",
      "revenue": 180000
    },
    {
      "pg_name": "Starlight PG",
      "revenue": 125000
    }
  ],
  "occupancy_overview": {
    "occupied_beds": {
      "count": 42,
      "percentage": 84.0
    },
    "vacant_beds": {
      "count": 8,
      "percentage": 16.0
    }
  },
  "member_status_distribution": {
    "active": {
      "count": 42,
      "percentage": 80.8
    },
    "notice_period": {
      "count": 6,
      "percentage": 11.5
    },
    "inactive": {
      "count": 2,
      "percentage": 3.8
    },
    "vacant_left": {
      "count": 2,
      "percentage": 3.8
    }
  }
}
```

---

### 8. Dashboard Tables
Retrieves data for dashboard data tables including upcoming rent dues and recent payment transactions.

- **HTTP Method:** `GET`
- **Endpoint:** `/api/dashboard-tables/`
- **Authentication:** Required (`Bearer Token` or `access_token` Cookie)

#### Parameters
- **Headers:** `Authorization: Bearer <access_token>`
- **Query Parameters:** None

#### Example Response (`200 OK`)
```json
{
  "upcoming_rent_due": [
    {
      "rent_id": "R001",
      "member_id": "M001",
      "pg_id": "PG001",
      "member_name": "Rohan Sharma",
      "pg_name": "Sunrise PG",
      "room_number": "101",
      "rent_amount": 8500,
      "due_date": "2026-08-25",
      "days_left": 7,
      "status": "Upcoming"
    }
  ],
  "recent_payments": [
    {
      "payment_id": "PAY_R002",
      "member_id": "M002",
      "pg_id": "PG001",
      "member_name": "Ankit Verma",
      "pg_name": "Sunrise PG",
      "amount": 8500,
      "date": "2026-08-15T10:30:00+05:30",
      "status": "Paid"
    }
  ]
}
```

---

### 9. Dashboard Alerts
Retrieves actionable dashboard notifications, including overdue rent items and payments pending approval.

- **HTTP Method:** `GET`
- **Endpoint:** `/api/dashboard-alerts/`
- **Authentication:** Required (`Bearer Token` or `access_token` Cookie)

#### Parameters
- **Headers:** `Authorization: Bearer <access_token>`
- **Query Parameters:** None

#### Example Response (`200 OK`)
```json
{
  "rent_overdue": [
    {
      "rent_id": "R003",
      "member_id": "M003",
      "pg_id": "PG002",
      "member_name": "Suresh Patel",
      "pg_name": "Starlight PG",
      "room_number": "204",
      "rent_amount": 9000,
      "due_date": "2026-08-10",
      "overdue_by_days": 8,
      "status": "Overdue"
    }
  ],
  "pending_approvals": [
    {
      "payment_id": "P_PENDING_01",
      "member_id": "M004",
      "pg_id": "PG001",
      "member_name": "Vikas Singh",
      "pg_name": "Sunrise PG",
      "amount": 8500,
      "payment_type": "UPI",
      "submitted_on": "2026-08-17T14:20:00+05:30"
    }
  ]
}
```

---

## Standard Error Response Format

In case of server errors (HTTP 500) or client errors (400, 401, 403, 404, 409), responses follow DRF JSON format:

```json
{
  "detail": "Detailed error message describing the failure."
}
```
