# API Documentation

## Authentication
All protected APIs require a valid JWT Token passed in the headers.

**Header:**
```json
{
  "Authorization": "Bearer <YOUR_JWT_TOKEN>"
}
```

---

## 1. Login API

Retrieves a JWT token to access the dashboard and PG management endpoints. 

- **Endpoint:** `POST /api/login/` *(Adjust path based on your actual auth route)*
- **Headers:** None
- **Body:**
```json
{
  "username": "admin_user",
  "password": "secure_password"
}
```
- **Response:** Returns the access and refresh tokens.
```json
{
  "access": "eyJhbGciOi...",
  "refresh": "eyJhbGciOi..."
}
```

---

## 2. Get PG Properties

Retrieves a paginated list of properties and a data summary. If a specific `pg_id` is provided, it returns the full details of that single property.

- **Endpoint:** `GET /addpg/`
- **Headers:** `Authorization: Bearer <token>`
- **Parameters (Can be sent in URL Query Params or Headers):**
  - `pg_id`: *(Optional)* If provided, fetches only this specific PG. All other filters are ignored.
  - `page`: *(Optional)* Page number for pagination (default: 1).
  - `limit`: *(Optional)* Number of items per page (default: 10).
  - `property_type`: *(Optional)* Exact match (e.g., `PG`, `Apartment`).
  - `living_type`: *(Optional)* Exact match (e.g., `Boys`, `Girls`, `Family`).
  - `property_status`: *(Optional)* Exact match (`active` or `inactive`).
  - `city`: *(Optional)* Case-insensitive match.
  - `state`: *(Optional)* Case-insensitive match.
  - `search`: *(Optional)* Case-insensitive substring search matching `pg_id`, `pg_name`, or `contact_person`.

---

## 3. Create a New PG Property

Creates a new PG or Apartment. The backend automatically generates a sequential ID (e.g., `PG001`).

- **Endpoint:** `POST /addpg/`
- **Headers:** `Authorization: Bearer <token>`
- **Body Example:**
```json
{
  "name": "Sunrise PG",
  "pg_type": "PG",
  "living_type": "Boys",
  "contact_person": "Ramesh Singh",
  "mobile": "9876543210",
  "address_line_1": "123 Main St",
  "area": "Koramangala",
  "city": "Bangalore",
  "state": "Karnataka",
  "pincode": "560034",
  "country": "India",
  "no_of_rooms": 2,
  "property_status": true,
  "room_config": [
    {
      "room_number": "101",
      "sharing": 2,
      "rent": 8500
    }
  ]
}
```

---

## 4. Update an Existing PG Property

Updates specific fields of an existing PG property. Uses partial updates, meaning fields not included in the payload will remain unchanged.

- **Endpoint:** `PUT /addpg/`
- **Headers:** `Authorization: Bearer <token>`
- **Body:** **Must include `pg_id`.** Include only the fields you wish to update.
```json
{
  "pg_id": "PG001",
  "name": "Sunrise Premium PG",
  "property_status": false
}
```

---

## 5. Get Unique States

Retrieves an alphabetically sorted list of all unique states found across the properties in the database.

- **Endpoint:** `GET /states/`
- **Headers:** `Authorization: Bearer <token>`
- **Response:**
```json
[
  "Delhi",
  "Karnataka",
  "Maharashtra"
]
```

---

## 6. Get Unique Cities

Retrieves an alphabetically sorted list of all unique cities found across the properties.

- **Endpoint:** `GET /cities/`
- **Headers:** `Authorization: Bearer <token>`
- **Parameters (Query Params or Headers):**
  - `state`: *(Optional)* Filters the cities to only include those in the specified state.
- **Response:**
```json
[
  "Bangalore",
  "Mumbai",
  "Pune"
]
```

---

## 7. Delete a PG Property

Performs a soft-delete on a specific PG property. This does not remove the data from the database permanently; instead, it changes the `property_status` to `false` (inactive).

- **Endpoint:** `DELETE /addpg/`
- **Headers:** `Authorization: Bearer <token>`
- **Parameters:** `pg_id` is required. You can pass it in the **Body**, as a **Query Parameter** (e.g. `?pg_id=PG001`), or in the **Headers**.
- **Body Example:**
```json
{
  "pg_id": "PG001"
}
```
- **Response:**
```json
{
  "message": "PG property PG001 softly deleted (marked inactive) successfully"
}
```
