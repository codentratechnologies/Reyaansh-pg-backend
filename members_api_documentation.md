# Members API Documentation

Complete API documentation for the **PgMembers** module in the PG Management Backend system.

---

## Base URL
```http
http://<your-domain-or-localhost>:8000/api
```

---

## Authentication & Authorization

All member endpoints require JWT authentication.

1. **Authorization Header**:
   ```http
   Authorization: Bearer <your_access_token>
   ```
2. **HTTPOnly Cookie**:
   - `access_token`: Access token stored in HTTPOnly cookie.

---

## Summary of Members Endpoints

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/members` | Fetch paginated list of all active members or single member details | ✅ Yes |
| `POST` | `/api/members` | Register a new member, check bed availability, and assign bed/rent | ✅ Yes |
| `PUT` / `PATCH` | `/api/members` | Update existing member profile, handle room/bed transfer & rent sync | ✅ Yes |
| `DELETE` | `/api/members` | Soft-delete a member, free occupied bed, and delete rent record | ✅ Yes |

---

## Endpoint Details

### 1. Get Members / Member Details
Retrieves a paginated list of all active members or single member details if `member_id` is provided.

- **HTTP Method:** `GET`
- **Endpoint:** `/api/members`
- **Authentication:** Required (`Bearer Token` or `access_token` Cookie)

#### Query Parameters

| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `member_id` *(or `id`)* | String | No | - | If provided, returns complete details of this single member. |
| `page` | Integer | No | `1` | Page number for paginated list. |
| `page_size` | Integer | No | `10` | Number of items per page. |

---

#### Example Request 1: Get All Members (Paginated)
```http
GET /api/members?page=1&page_size=10 HTTP/1.1
Authorization: Bearer <access_token>
```

##### Example Response (`200 OK`)
```json
{
  "message": "Members fetched successfully",
  "pagination": {
    "total_records": 25,
    "total_pages": 3,
    "current_page": 1,
    "page_size": 10,
    "has_next": true,
    "has_previous": false
  },
  "data": [
    {
      "id": "MEM001",
      "name": "Rahul Kumar",
      "mobile": "9876543210",
      "pg_name": "Sunrise PG",
      "room_number": "101",
      "bed_name": "Bed A",
      "monthly_rent": 8500,
      "due_date": "05",
      "rent_status": "Paid",
      "member_status": "Active"
    },
    {
      "id": "MEM002",
      "name": "Amit Sharma",
      "mobile": "9123456789",
      "pg_name": "Starlight PG",
      "room_number": "202",
      "bed_name": "Bed B",
      "monthly_rent": 9000,
      "due_date": "10",
      "rent_status": "Pending",
      "member_status": "Notice Period"
    }
  ]
}
```

---

#### Example Request 2: Get Single Member Details
```http
GET /api/members?member_id=MEM001 HTTP/1.1
Authorization: Bearer <access_token>
```

##### Example Response (`200 OK`)
```json
{
  "message": "Member details fetched successfully",
  "data": {
    "member_id": "MEM001",
    "full_name": "Rahul Kumar",
    "mobile_number": "9876543210",
    "alternate_mobile_number": "9876543211",
    "email": "rahul.kumar@example.com",
    "occupation": "Software Engineer",
    "dob": "1998-05-15",
    "gender": "Male",
    "company_college_name": "Tech Corp",
    "aadhaar_number": "123456789012",
    "pan_number": "ABCDE1234F",
    "driving_licence_number": "DL1234567890",
    "emergency_contact_name": "Suresh Kumar",
    "emergency_contact_relationship": "Father",
    "emergency_contact_number": "9876543212",
    "address_line_1": "123 Main Street",
    "address_line_2": "Sector 4",
    "country": "India",
    "state": "Karnataka",
    "city": "Bangalore",
    "pincode": "560034",
    "pg_type": "PG",
    "pg_id": "PG001",
    "room_id": "101",
    "bed_id": "BED_A",
    "pg_name": "Sunrise PG",
    "room_number": "101",
    "bed_name": "Bed A",
    "monthly_rent": 8500,
    "security_deposit": 10000,
    "maintenance_charge": 500,
    "rent_due_date": "05",
    "notice_period_days": 30,
    "status": "Active",
    "rent_status": "Paid",
    "created_at": "2026-08-01T10:00:00+05:30",
    "updated_at": "2026-08-18T12:00:00+05:30"
  }
}
```

##### Error Response
- `404 Not Found`: `{"detail": "Member not found."}`

---

### 2. Create Member
Registers a new member in Firebase, generates a sequential ID (`MEM001`, `MEM002`, etc.), checks bed availability, updates bed occupancy status, and automatically initializes a rent record.

- **HTTP Method:** `POST`
- **Endpoint:** `/api/members`
- **Authentication:** Required (`Bearer Token` or `access_token` Cookie)

#### Parameters

- **Headers:** 
  - `Authorization: Bearer <access_token>`
  - `Content-Type: application/json`

- **Request Body Parameters:**

  | Parameter | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `full_name` | String | Yes | Full name of member |
  | `mobile_number` | String | Yes | Primary mobile number |
  | `occupation` | String | Yes | Job or study occupation |
  | `dob` | String | Yes | Date of birth (YYYY-MM-DD) |
  | `gender` | String | Yes | Gender (`Male`, `Female`, `Other`) |
  | `company_college_name` | String | Yes | Company or college name |
  | `aadhaar_number` | String | Yes | 12-digit Aadhaar number |
  | `emergency_contact_name` | String | Yes | Emergency contact full name |
  | `emergency_contact_relationship` | String | Yes | Relationship (e.g. `Father`, `Mother`, `Spouse`) |
  | `emergency_contact_number` | String | Yes | Emergency contact mobile number |
  | `address_line_1` | String | Yes | Permanent address line 1 |
  | `country` | String | Yes | Country |
  | `state` | String | Yes | State |
  | `city` | String | Yes | City |
  | `pincode` | String | Yes | Postal Pincode |
  | `pg_type` | String | Yes | `PG` or `Apartment` |
  | `pg_id` | String | Yes | PG Property ID |
  | `room_id` | String | Yes | Room ID |
  | `bed_id` | String | **Conditional** | Required if `pg_type` is `PG` |
  | `monthly_rent` | Integer | Yes | Monthly rent amount |
  | `security_deposit` | Integer | Yes | Security deposit amount |
  | `maintenance_charge` | Integer | Yes | Maintenance charges |
  | `rent_due_date` | String | Yes | Rent due day (e.g. `05` or `2026-09-05`) |
  | `notice_period_days` | Integer | Yes | Notice period in days (e.g. `30`) |
  | `status` | String | Yes | Member status (`Active`, `Notice Period`, `Inactive`) |
  | `status_reason` | String | **Conditional** | Required if `status` is `Notice Period` |
  | `alternate_mobile_number` | String | No | Secondary contact number |
  | `email` | String | No | Email address |
  | `pan_number` | String | No | PAN card number |
  | `driving_licence_number` | String | No | Driving license number |
  | `address_line_2` | String | No | Permanent address line 2 |

#### Example Request Body
```json
{
  "full_name": "Rahul Kumar",
  "mobile_number": "9876543210",
  "alternate_mobile_number": "9876543211",
  "email": "rahul.kumar@example.com",
  "occupation": "Software Engineer",
  "dob": "1998-05-15",
  "gender": "Male",
  "company_college_name": "Tech Corp",
  "aadhaar_number": "123456789012",
  "pan_number": "ABCDE1234F",
  "driving_licence_number": "DL1234567890",
  "emergency_contact_name": "Suresh Kumar",
  "emergency_contact_relationship": "Father",
  "emergency_contact_number": "9876543212",
  "address_line_1": "123 Main Street",
  "address_line_2": "Sector 4",
  "country": "India",
  "state": "Karnataka",
  "city": "Bangalore",
  "pincode": "560034",
  "pg_type": "PG",
  "pg_id": "PG001",
  "room_id": "101",
  "bed_id": "BED_A",
  "monthly_rent": 8500,
  "security_deposit": 10000,
  "maintenance_charge": 500,
  "rent_due_date": "05",
  "notice_period_days": 30,
  "status": "Active"
}
```

#### Example Responses

- **`201 Created`**
```json
{
  "message": "Member created successfully",
  "member_id": "MEM001",
  "data": {
    "full_name": "Rahul Kumar",
    "mobile_number": "9876543210",
    "member_id": "MEM001",
    "status": "Active",
    "created_at": "2026-08-18T13:45:00+05:30",
    "updated_at": "2026-08-18T13:45:00+05:30"
  }
}
```

- **`400 Bad Request` (Missing Fields)**
```json
{
  "detail": "Missing required fields: full_name, bed_id"
}
```

- **`400 Bad Request` (Bed Occupied)**
```json
{
  "detail": "The specified bed is already occupied."
}
```

- **`404 Not Found`**
```json
{
  "detail": "The specified bed does not exist."
}
```

---

### 3. Update Member
Updates member profile. Supports partial updates (`PUT` or `PATCH`). If property/room/bed assignment changes, it automatically frees the old bed and marks the new bed as occupied.

- **HTTP Method:** `PUT` / `PATCH`
- **Endpoint:** `/api/members`
- **Authentication:** Required (`Bearer Token` or `access_token` Cookie)

#### Parameters

- **Headers:**
  - `Authorization: Bearer <access_token>`
  - `Content-Type: application/json`

- **Request Body Parameters:**
  | Parameter | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `member_id` | String | **Yes** | ID of the member to update (e.g. `MEM001`) |
  | *(Any Member Field)* | Various | No | Any fields to update (e.g. `status`, `monthly_rent`, `room_id`, `bed_id`, `mobile_number`) |

#### Example Request Body
```json
{
  "member_id": "MEM001",
  "status": "Notice Period",
  "status_reason": "Relocating to another city",
  "monthly_rent": 9000
}
```

#### Example Response (`200 OK`)
```json
{
  "message": "Member updated successfully",
  "member_id": "MEM001",
  "data": {
    "member_id": "MEM001",
    "full_name": "Rahul Kumar",
    "status": "Notice Period",
    "status_reason": "Relocating to another city",
    "monthly_rent": 9000,
    "updated_at": "2026-08-18T13:46:00+05:30"
  }
}
```

#### Error Responses
- `400 Bad Request`: `{"detail": "member_id is required for updating."}` or `{"detail": "The specified new bed is already occupied."}`
- `404 Not Found`: `{"detail": "Member not found."}` or `{"detail": "The specified new bed does not exist."}`

---

### 4. Delete Member (Soft Delete)
Soft-deletes a member (`is_deleted: true`), sets status to `Deleted`, frees up the occupied bed in Firebase property node, and removes the associated rent record.

- **HTTP Method:** `DELETE`
- **Endpoint:** `/api/members`
- **Authentication:** Required (`Bearer Token` or `access_token` Cookie)

#### Parameters

- **Headers:** `Authorization: Bearer <access_token>`
- **Query Parameter:** `?member_id=MEM001`
- **OR JSON Body:** `{"member_id": "MEM001"}`

#### Example Request Body / Query
```http
DELETE /api/members?member_id=MEM001 HTTP/1.1
Authorization: Bearer <access_token>
```

#### Example Response (`200 OK`)
```json
{
  "message": "Member deleted successfully",
  "member_id": "MEM001"
}
```

#### Error Responses
- `400 Bad Request`: `{"detail": "member_id is required for deletion."}`
- `404 Not Found`: `{"detail": "Member not found."}`

---

## Standard Error Response Format

In case of server errors (HTTP 500) or client errors (400, 404), responses follow standard JSON error schema:

```json
{
  "detail": "Detailed error message describing the failure."
}
```
