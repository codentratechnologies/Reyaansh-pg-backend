import os
import requests
from requests.adapters import HTTPAdapter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from DashBoard.security import JWTAuthentication

load_dotenv()
DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")

# Reusable HTTP Session with connection pooling for fast Firebase API performance
http_session = requests.Session()
adapter = HTTPAdapter(pool_connections=30, pool_maxsize=30)
http_session.mount("https://", adapter)
http_session.mount("http://", adapter)

def fetch_nodes_parallel(url_dict):
    """
    Fetches multiple Firebase URLs concurrently using thread pool.
    """
    def fetch_one(item):
        key, url = item
        try:
            res = http_session.get(url, timeout=5)
            if res.status_code == 200 and res.json():
                return key, res.json()
        except Exception:
            pass
        return key, {}

    with ThreadPoolExecutor(max_workers=max(1, len(url_dict))) as executor:
        results = dict(executor.map(fetch_one, url_dict.items()))
    return results

def get_ist_now():
    """Returns current time in Indian Standard Time (IST)"""
    return datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()

class MemberView(APIView):
    """
    POST/PUT/DELETE/GET API to manage a member in Firebase Realtime Database.
    Node Name: members
    """
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        if not DATABASE_URL:
            return Response(
                {"detail": "Firebase database URL is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        member_id = request.query_params.get("member_id") or request.query_params.get("id")
        
        try:
            # Parallel fetch of rent records and pg properties
            nodes = fetch_nodes_parallel({
                "rent": f"{DATABASE_URL}/rent_records.json",
                "pgs": f"{DATABASE_URL}/pg_properties.json"
            })
            rent_records = nodes["rent"]
            pg_properties = nodes["pgs"]

            # --- SINGLE MEMBER FULL DETAILS ---
            if member_id:
                url = f"{DATABASE_URL}/members/{member_id}.json"
                res = http_session.get(url)
                res.raise_for_status()
                member_data = res.json()
                
                if not member_data or member_data.get("is_deleted"):
                    return Response({"detail": "Member not found."}, status=status.HTTP_404_NOT_FOUND)
                
                member_data["member_id"] = member_id
                
                pg_id = member_data.get("pg_id", "")
                room_id = member_data.get("room_id", "")
                bed_id = member_data.get("bed_id", "")
                
                member_data["pg_name"] = pg_id
                member_data["room_number"] = room_id
                member_data["bed_name"] = bed_id
                
                if pg_id and pg_id in pg_properties:
                    pg_info = pg_properties[pg_id]
                    member_data["pg_name"] = pg_info.get("property_name", pg_info.get("pg_name", pg_info.get("name", pg_id)))
                    
                    if room_id and "rooms" in pg_info and room_id in pg_info["rooms"]:
                        room_info = pg_info["rooms"][room_id]
                        member_data["room_number"] = room_info.get("room_number", room_info.get("room_name", room_info.get("name", room_id)))
                        
                        if bed_id and "beds" in room_info and bed_id in room_info["beds"]:
                            bed_info = room_info["beds"][bed_id]
                            if isinstance(bed_info, dict):
                                member_data["bed_name"] = bed_info.get("bed_number", bed_info.get("bed_name", bed_info.get("name", bed_id)))
                
                member_rent_record = rent_records.get(member_id, {})
                if isinstance(member_rent_record, dict) and member_rent_record.get("status"):
                    member_data["rent_status"] = member_rent_record.get("status")
                else:
                    member_data["rent_status"] = "Pending"

                return Response({
                    "message": "Member details fetched successfully",
                    "data": member_data
                }, status=status.HTTP_200_OK)

            # --- ALL MEMBERS (PAGINATED) ---
            url = f"{DATABASE_URL}/members.json"
            res = http_session.get(url)
            res.raise_for_status()
            members_dict = res.json() or {}

            formatted_members = []

            for m_id, m_data in members_dict.items():
                if not m_data or m_data.get("is_deleted"):
                    continue
                    
                rent_status = "Pending"
                member_rent_record = rent_records.get(m_id, {})
                if isinstance(member_rent_record, dict) and member_rent_record.get("status"):
                    rent_status = member_rent_record.get("status")

                pg_id = m_data.get("pg_id", "")
                room_id = m_data.get("room_id", "")
                bed_id = m_data.get("bed_id", "")
                
                pg_name = pg_id
                room_name = room_id
                bed_name = bed_id
                
                if pg_id and pg_id in pg_properties:
                    pg_info = pg_properties[pg_id]
                    pg_name = pg_info.get("property_name", pg_info.get("pg_name", pg_info.get("name", pg_id)))
                    
                    if room_id and "rooms" in pg_info and room_id in pg_info["rooms"]:
                        room_info = pg_info["rooms"][room_id]
                        room_name = room_info.get("room_number", room_info.get("room_name", room_info.get("name", room_id)))
                        
                        if bed_id and "beds" in room_info and bed_id in room_info["beds"]:
                            bed_info = room_info["beds"][bed_id]
                            if isinstance(bed_info, dict):
                                bed_name = bed_info.get("bed_number", bed_info.get("bed_name", bed_info.get("name", bed_id)))

                formatted_members.append({
                    "id": m_id,
                    "name": m_data.get("full_name", ""),
                    "mobile": m_data.get("mobile_number", ""),
                    "pg_name": pg_name,
                    "room_number": room_name,
                    "bed_name": bed_name,
                    "monthly_rent": m_data.get("monthly_rent", 0),
                    "due_date": m_data.get("rent_due_date", ""),
                    "rent_status": rent_status,
                    "member_status": m_data.get("status", "")
                })

            formatted_members.reverse()

            # Pagination
            try:
                page = max(1, int(request.query_params.get("page", 1)))
            except (ValueError, TypeError):
                page = 1

            try:
                page_size = max(1, int(request.query_params.get("page_size", 10)))
            except (ValueError, TypeError):
                page_size = 10

            total_records = len(formatted_members)
            total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 1

            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            paginated_data = formatted_members[start_index:end_index]

            return Response({
                "message": "Members fetched successfully",
                "pagination": {
                    "total_records": total_records,
                    "total_pages": total_pages,
                    "current_page": page,
                    "page_size": page_size,
                    "has_next": page < total_pages,
                    "has_previous": page > 1
                },
                "data": paginated_data
            }, status=status.HTTP_200_OK)

        except requests.exceptions.RequestException as e:
            return Response(
                {"detail": f"Failed to fetch members: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        data = request.data

        if not DATABASE_URL:
            return Response(
                {"detail": "Firebase database URL is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 1. Validate Required Fields
        required_fields = [
            "full_name", "mobile_number", "occupation", "dob", "gender", "company_college_name",
            "aadhaar_number",
            "emergency_contact_name", "emergency_contact_relationship", "emergency_contact_number",
            "address_line_1", "country", "state", "city", "pincode",
            "pg_type", "pg_id", "room_id",
            "monthly_rent", "security_deposit", "maintenance_charge", "rent_due_date", "notice_period_days",
            "status"
        ]
        
        missing_fields = [field for field in required_fields if data.get(field) in [None, ""]]
        
        pg_type = str(data.get("pg_type", ""))
        status_val = str(data.get("status", ""))
        
        # Conditional required fields
        if pg_type == 'PG' and not data.get("bed_id"):
            missing_fields.append("bed_id")
            
        if status_val == 'Notice Period' and not data.get("status_reason"):
            missing_fields.append("status_reason")

        if missing_fields:
            return Response(
                {"detail": f"Missing required fields: {', '.join(missing_fields)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        pg_id = str(data.get("pg_id"))
        room_id = str(data.get("room_id"))
        bed_id = str(data.get("bed_id")) if pg_type == 'PG' else None

        # 2. Check bed availability if it's a PG
        if pg_type == 'PG':
            bed_url = f"{DATABASE_URL}/pg_properties/{pg_id}/rooms/{room_id}/beds/{bed_id}.json"
            try:
                bed_res = requests.get(bed_url)
                bed_res.raise_for_status()
                bed_data = bed_res.json()
                
                if not bed_data:
                    return Response({"detail": "The specified bed does not exist."}, status=status.HTTP_404_NOT_FOUND)
                
                if bed_data.get("is_occupied") is True:
                    return Response({"detail": "The specified bed is already occupied."}, status=status.HTTP_400_BAD_REQUEST)
                    
            except requests.exceptions.RequestException as e:
                return Response(
                    {"detail": f"Failed to verify bed availability: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # 3. Build payload
        payload = {
            # Personal Info
            "full_name": str(data.get("full_name")),
            "mobile_number": str(data.get("mobile_number")),
            "occupation": str(data.get("occupation")),
            "dob": str(data.get("dob")),
            "gender": str(data.get("gender")),
            "company_college_name": str(data.get("company_college_name")),
            
            # Identity Verification
            "aadhaar_number": str(data.get("aadhaar_number")),
            
            # Emergency Contact
            "emergency_contact_name": str(data.get("emergency_contact_name")),
            "emergency_contact_relationship": str(data.get("emergency_contact_relationship")),
            "emergency_contact_number": str(data.get("emergency_contact_number")),
            
            # Address Details
            "address_line_1": str(data.get("address_line_1")),
            "country": str(data.get("country")),
            "state": str(data.get("state")),
            "city": str(data.get("city")),
            "pincode": str(data.get("pincode")),
            
            # Stay Details
            "pg_type": pg_type,
            "pg_id": pg_id,
            "room_id": room_id,
            
            # Rent Details
            "monthly_rent": int(data.get("monthly_rent")),
            "security_deposit": int(data.get("security_deposit")),
            "maintenance_charge": int(data.get("maintenance_charge")),
            "rent_due_date": str(data.get("rent_due_date")),
            "notice_period_days": int(data.get("notice_period_days")),
            
            # Member Status
            "status": status_val,
            
            # Timestamps
            "created_at": get_ist_now(),
            "updated_at": get_ist_now(),
        }
        
        # Optional fields
        if "alternate_mobile_number" in data and data.get("alternate_mobile_number"):
            payload["alternate_mobile_number"] = str(data.get("alternate_mobile_number"))
        if "email" in data and data.get("email"):
            payload["email"] = str(data.get("email"))
        if "pan_number" in data and data.get("pan_number"):
            payload["pan_number"] = str(data.get("pan_number"))
        if "driving_licence_number" in data and data.get("driving_licence_number"):
            payload["driving_licence_number"] = str(data.get("driving_licence_number"))
        if "address_line_2" in data and data.get("address_line_2"):
            payload["address_line_2"] = str(data.get("address_line_2"))
        if pg_type == 'PG' and bed_id:
            payload["bed_id"] = bed_id
        if status_val == 'Notice Period' and data.get("status_reason"):
            payload["status_reason"] = str(data.get("status_reason"))

        # 4. Generate Proper Member ID (MEM001, MEM002, etc.)
        try:
            get_url = f"{DATABASE_URL}/members.json?shallow=true"
            response = requests.get(get_url)
            response.raise_for_status()
            existing_members = response.json()
            
            next_num = 1
            if existing_members:
                numbers = []
                for key in existing_members.keys():
                    if key.startswith("MEM"):
                        try:
                            num = int(key[3:])
                            numbers.append(num)
                        except ValueError:
                            pass
                if numbers:
                    next_num = max(numbers) + 1
                    
            member_id = f"MEM{next_num:03d}"
            payload["member_id"] = member_id
        except requests.exceptions.RequestException as e:
            return Response(
                {"detail": f"Failed to generate member ID: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 5. Save to Firebase Members Node
        member_url = f"{DATABASE_URL}/members/{member_id}.json"
        try:
            member_res = requests.put(member_url, json=payload)
            member_res.raise_for_status()
        except requests.exceptions.RequestException as e:
            return Response(
                {"detail": f"Failed to create member: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 5. Update Bed Status if PG
        if pg_type == 'PG':
            try:
                # Update bed to occupied and map the member_id
                bed_patch = {
                    "is_occupied": True,
                    "member_id": member_id
                }
                requests.patch(bed_url, json=bed_patch)
            except requests.exceptions.RequestException as e:
                # Note: This means member was created, but bed wasn't updated. 
                # A manual rollback or retry logic might be needed in a robust system.
                return Response(
                    {"detail": f"Member created, but failed to update bed status: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # 6. Create Rent Record automatically (as mentioned: "Referenced in the rent_records node via member_id")
        rent_record_url = f"{DATABASE_URL}/rent_records/{member_id}.json"
        rent_payload = {
            "member_id": member_id,
            "pg_id": pg_id,
            "monthly_rent": payload["monthly_rent"],
            "security_deposit": payload["security_deposit"],
            "maintenance_charge": payload["maintenance_charge"],
            "rent_due_date": payload["rent_due_date"],
            "notice_period_days": payload["notice_period_days"],
            "created_at": payload["created_at"]
        }
        try:
            requests.put(rent_record_url, json=rent_payload)
        except requests.exceptions.RequestException as e:
            # We silently ignore rent record creation failure or just log it.
            pass

        # Append member_id to response payload
        payload["member_id"] = member_id
        
        return Response({
            "message": "Member created successfully",
            "member_id": member_id,
            "data": payload
        }, status=status.HTTP_201_CREATED)

    def put(self, request):
        return self.update_member(request)

    def patch(self, request):
        return self.update_member(request)

    def update_member(self, request):
        data = request.data
        member_id = data.get("member_id")

        if not DATABASE_URL:
            return Response(
                {"detail": "Firebase database URL is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if not member_id:
            return Response(
                {"detail": "member_id is required for updating."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Fetch existing member
        member_url = f"{DATABASE_URL}/members/{member_id}.json"
        try:
            member_res = requests.get(member_url)
            member_res.raise_for_status()
            existing_member = member_res.json()
            
            if not existing_member:
                return Response(
                    {"detail": "Member not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
        except requests.exceptions.RequestException as e:
            return Response(
                {"detail": f"Failed to fetch member details: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Keep track of old bed for bed status update if it changes
        old_pg_type = existing_member.get("pg_type")
        old_pg_id = existing_member.get("pg_id")
        old_room_id = existing_member.get("room_id")
        old_bed_id = existing_member.get("bed_id")

        # 2. Update fields
        update_data = existing_member.copy()
        
        for key, value in data.items():
            if key not in ["member_id", "created_at"] and value is not None and str(value).strip() != "":
                if isinstance(value, (int, bool, dict, list)):
                    update_data[key] = value
                else:
                    update_data[key] = str(value)
                    
        update_data["updated_at"] = get_ist_now()

        new_pg_type = update_data.get("pg_type")
        new_pg_id = update_data.get("pg_id")
        new_room_id = update_data.get("room_id")
        new_bed_id = update_data.get("bed_id")

        bed_changed = False
        if new_pg_type == 'PG' and (old_pg_id != new_pg_id or old_room_id != new_room_id or old_bed_id != new_bed_id):
            bed_changed = True
            
            if new_bed_id:
                new_bed_url = f"{DATABASE_URL}/pg_properties/{new_pg_id}/rooms/{new_room_id}/beds/{new_bed_id}.json"
                try:
                    new_bed_res = requests.get(new_bed_url)
                    new_bed_res.raise_for_status()
                    new_bed_data = new_bed_res.json()
                    
                    if not new_bed_data:
                        return Response({"detail": "The specified new bed does not exist."}, status=status.HTTP_404_NOT_FOUND)
                    
                    if new_bed_data.get("is_occupied") is True and str(new_bed_data.get("member_id", "")) != member_id:
                        return Response({"detail": "The specified new bed is already occupied."}, status=status.HTTP_400_BAD_REQUEST)
                except requests.exceptions.RequestException as e:
                    return Response(
                        {"detail": f"Failed to verify new bed availability: {str(e)}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

        # 3. Save to Firebase Members Node
        try:
            update_res = requests.put(member_url, json=update_data)
            update_res.raise_for_status()
        except requests.exceptions.RequestException as e:
            return Response(
                {"detail": f"Failed to update member: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 4. Update Bed Status if PG
        if bed_changed:
            # Free old bed
            if old_pg_type == 'PG' and old_pg_id and old_room_id and old_bed_id:
                old_bed_url = f"{DATABASE_URL}/pg_properties/{old_pg_id}/rooms/{old_room_id}/beds/{old_bed_id}.json"
                try:
                    requests.patch(old_bed_url, json={"is_occupied": False, "member_id": None})
                except:
                    pass
            
            # Occupy new bed
            if new_pg_type == 'PG' and new_pg_id and new_room_id and new_bed_id:
                try:
                    requests.patch(new_bed_url, json={"is_occupied": True, "member_id": member_id})
                except:
                    pass

        # 5. Update rent records if rent details changed
        rent_fields = ["monthly_rent", "security_deposit", "maintenance_charge", "rent_due_date", "notice_period_days", "pg_id"]
        if any(key in data for key in rent_fields):
            rent_record_url = f"{DATABASE_URL}/rent_records/{member_id}.json"
            try:
                rent_res = requests.get(rent_record_url)
                if rent_res.status_code == 200 and rent_res.json():
                    rent_payload = rent_res.json()
                    for field in rent_fields:
                        if field in update_data:
                            rent_payload[field] = update_data[field]
                    
                    requests.put(rent_record_url, json=rent_payload)
            except:
                pass

        return Response({
            "message": "Member updated successfully",
            "member_id": member_id,
            "data": update_data
        }, status=status.HTTP_200_OK)

    def delete(self, request):
        member_id = request.query_params.get("member_id") or request.data.get("member_id")

        if not DATABASE_URL:
            return Response(
                {"detail": "Firebase database URL is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if not member_id:
            return Response(
                {"detail": "member_id is required for deletion."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Fetch existing member
        member_url = f"{DATABASE_URL}/members/{member_id}.json"
        try:
            member_res = requests.get(member_url)
            member_res.raise_for_status()
            existing_member = member_res.json()
            
            if not existing_member:
                return Response(
                    {"detail": "Member not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
        except requests.exceptions.RequestException as e:
            return Response(
                {"detail": f"Failed to fetch member details: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 2. Free up the bed if occupied
        pg_type = existing_member.get("pg_type")
        pg_id = existing_member.get("pg_id")
        room_id = existing_member.get("room_id")
        bed_id = existing_member.get("bed_id")

        if pg_type == 'PG' and pg_id and room_id and bed_id:
            bed_url = f"{DATABASE_URL}/pg_properties/{pg_id}/rooms/{room_id}/beds/{bed_id}.json"
            try:
                requests.patch(bed_url, json={"is_occupied": False, "member_id": None})
            except:
                pass # Silently ignore bed update failure for now

        # 3. Delete rent record
        rent_record_url = f"{DATABASE_URL}/rent_records/{member_id}.json"
        try:
            requests.delete(rent_record_url)
        except:
            pass

        # 4. Soft Delete member
        try:
            patch_data = {
                "is_deleted": True,
                "status": "Deleted",
                "updated_at": get_ist_now()
            }
            delete_res = requests.patch(member_url, json=patch_data)
            delete_res.raise_for_status()
        except requests.exceptions.RequestException as e:
            return Response(
                {"detail": f"Failed to delete member: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            "message": "Member deleted successfully",
            "member_id": member_id
        }, status=status.HTTP_200_OK)
