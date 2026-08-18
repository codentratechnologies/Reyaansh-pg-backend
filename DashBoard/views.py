from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import timedelta, datetime, date
from zoneinfo import ZoneInfo
import os
import requests
from requests.adapters import HTTPAdapter
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

from .security import hash_password, create_token, JWTAuthentication, verify_token
from .firebase_client import get_admin_user, create_admin_user, update_last_login

load_dotenv()
DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")

# Reusable HTTP Session with connection pooling for high performance
http_session = requests.Session()
adapter = HTTPAdapter(pool_connections=30, pool_maxsize=30)
http_session.mount("https://", adapter)
http_session.mount("http://", adapter)

def fetch_nodes_parallel(url_dict):
    """
    Fetches multiple Firebase URLs concurrently using thread pool for ultra-fast API responses.
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

class SetupAdminView(APIView):
    """
    Utility endpoint to set up an admin user in Firebase with SHA-256 password.
    """
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        
        if not username or not password:
            return Response({"detail": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if user already exists
        try:
            existing_user = get_admin_user(username)
            if existing_user:
                return Response({"detail": "Admin with this username/email already exists."}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            return Response({"detail": f"Database check failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        hashed_pwd = hash_password(password)
        try:
            create_admin_user(username, hashed_pwd)
            return Response({"message": "Admin user created successfully", "username": username}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LoginView(APIView):
    """
    Login endpoint. Checks Firebase 'admin' node for the user.
    """
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        
        if not username or not password:
            return Response({"detail": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_data = get_admin_user(username)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if not user_data:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
            
        if not user_data.get("is_active", True):
            return Response({"detail": "Account is disabled"}, status=status.HTTP_403_FORBIDDEN)
        
        # Hash provided password
        hashed_pwd = hash_password(password)
        
        # Compare passwords
        if user_data.get("password") != hashed_pwd:
             return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
             
        # Update last_login
        try:
            update_last_login(username)
        except Exception as e:
            # We can just log this or ignore it, shouldn't block login
            print(f"Failed to update last login: {e}")
             
        # Mint tokens
        access_token = create_token(
            data={"sub": username, "type": "access"}, 
            expires_delta=timedelta(days=7)
        )
        refresh_token = create_token(
            data={"sub": username, "type": "refresh"}, 
            expires_delta=timedelta(days=15)
        )
        
        response = Response({
            "message": "Login successful",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        })
        
        # Store in HTTPOnly cookies
        # secure=True should be used in production (requires HTTPS)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=7 * 24 * 60 * 60,  # 7 days in seconds
            samesite='Lax'
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            max_age=15 * 24 * 60 * 60, # 15 days in seconds
            samesite='Lax'
        )
        return response

class RefreshTokenView(APIView):
    """
    Refresh endpoint to mint a new access token using a valid refresh token cookie.
    """
    def post(self, request):
        # Look for refresh token in cookies
        refresh_token = request.COOKIES.get('refresh_token')
        
        if not refresh_token:
            return Response({"detail": "Refresh token missing"}, status=status.HTTP_401_UNAUTHORIZED)
            
        payload = verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return Response({"detail": "Invalid or expired refresh token"}, status=status.HTTP_401_UNAUTHORIZED)
            
        username = payload.get("sub")
        
        # Mint new access token
        access_token = create_token(
            data={"sub": username, "type": "access"}, 
            expires_delta=timedelta(days=7)
        )
        
        response = Response({
            "message": "Token refreshed successfully",
            "access_token": access_token,
            "token_type": "bearer"
        })
        
        # Set new access token cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=7 * 24 * 60 * 60,
            samesite='Lax'
        )
        return response

class ProtectedDataView(APIView):
    """
    An example protected POST API. Requires JWT token in header or cookie.
    """
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        username = request.user.get("sub")
        data = request.data.get("data")
        
        return Response({
            "message": f"Hello {username}, this is a protected API.",
            "received_data": data
        })

class AdminDetailsView(APIView):
    """
    GET API to retrieve the currently logged in admin's details.
    Requires a valid JWT token.
    """
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        email = request.user.get("sub")
        if not email:
            return Response({"detail": "User not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
            
        try:
            admin_data = get_admin_user(email)
            if not admin_data:
                return Response({"detail": "Admin not found"}, status=status.HTTP_404_NOT_FOUND)
                
            # Remove the password from the response for security
            if "password" in admin_data:
                del admin_data["password"]
                
            return Response(admin_data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DashboardKPIView(APIView):
    """
    GET API to calculate and return dashboard KPI metrics dynamically from Firebase.
    """
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        if not DATABASE_URL:
            return Response(
                {"detail": "Firebase database URL is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            # Parallel fetch of PGs, Members, and Rent Records
            nodes = fetch_nodes_parallel({
                "pgs": f"{DATABASE_URL}/pg_properties.json",
                "members": f"{DATABASE_URL}/members.json",
                "rent": f"{DATABASE_URL}/rent_records.json"
            })
            pgs_data = nodes["pgs"]
            members_data = nodes["members"]
            rent_data = nodes["rent"]

            total_pgs = 0
            active_pgs = 0
            inactive_pgs = 0
            total_rooms = 0
            total_beds = 0
            occupied_beds = 0

            for pg_id, pg_info in pgs_data.items():
                if not pg_info:
                    continue
                total_pgs += 1
                status_val = pg_info.get("property_status")
                if status_val is True or str(status_val).lower() in ["true", "active"]:
                    active_pgs += 1
                else:
                    inactive_pgs += 1

                rooms = pg_info.get("rooms", {})
                if isinstance(rooms, dict):
                    total_rooms += len(rooms)
                    for r_id, r_info in rooms.items():
                        if isinstance(r_info, dict):
                            beds = r_info.get("beds", {})
                            if isinstance(beds, dict):
                                total_beds += len(beds)
                                for b_id, b_info in beds.items():
                                    if isinstance(b_info, dict) and b_info.get("is_occupied"):
                                        occupied_beds += 1

            total_members = 0
            active_members = 0
            notice_members = 0

            for m_id, m_info in members_data.items():
                if not m_info or m_info.get("is_deleted"):
                    continue
                total_members += 1
                m_status = m_info.get("status", "")
                if m_status == "Active":
                    active_members += 1
                elif m_status == "Notice Period":
                    notice_members += 1

            # 3. Fetch Rent Records
            rent_res = requests.get(f"{DATABASE_URL}/rent_records.json")
            rent_data = rent_res.json() if rent_res.status_code == 200 and rent_res.json() else {}

            rent_collected_amount = 0
            pending_rent_amount = 0
            pending_members_count = 0

            for r_id, r_info in rent_data.items():
                if not r_info:
                    continue
                r_status = str(r_info.get("status", "")).lower()
                monthly_rent = 0
                try:
                    monthly_rent = int(r_info.get("monthly_rent", 0))
                except (ValueError, TypeError):
                    pass

                if r_status == "paid":
                    rent_collected_amount += monthly_rent
                else:
                    pending_rent_amount += monthly_rent
                    pending_members_count += 1

            # Calculate occupancy percentage
            if total_beds > 0:
                occupancy_perc = round((occupied_beds / total_beds) * 100)
            elif total_rooms > 0:
                occupancy_perc = round((active_members / total_rooms) * 100)
            else:
                occupancy_perc = 0

            kpis = {
                "total_pgs": {
                    "value": total_pgs,
                    "active": active_pgs,
                    "inactive": inactive_pgs
                },
                "total_rooms": total_rooms,
                "total_members": {
                    "value": total_members,
                    "active": active_members,
                    "notice": notice_members
                },
                "occupancy_rate": {
                    "percentage": occupancy_perc,
                    "occupied": occupied_beds if total_beds > 0 else active_members,
                    "trend": "+2.5%"
                },
                "rent_collected": {
                    "amount": rent_collected_amount,
                    "trend": "+12.4%"
                },
                "pending_rent": {
                    "amount": pending_rent_amount,
                    "members": pending_members_count,
                    "trend": "+8.7%"
                }
            }

            return Response({"kpis": kpis}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DashboardChartsView(APIView):
    """
    GET API to calculate and return dashboard charts data dynamically from Firebase.
    """
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        if not DATABASE_URL:
            return Response(
                {"detail": "Firebase database URL is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            # Parallel fetch of PGs and Members
            nodes = fetch_nodes_parallel({
                "pgs": f"{DATABASE_URL}/pg_properties.json",
                "members": f"{DATABASE_URL}/members.json"
            })
            pgs_data = nodes["pgs"]
            members_data = nodes["members"]

            total_beds = 0
            occupied_beds = 0
            pg_revenue_map = {}

            for pg_id, pg_info in pgs_data.items():
                if not pg_info:
                    continue
                pg_name = pg_info.get("property_name", pg_info.get("pg_name", pg_info.get("name", pg_id)))
                pg_revenue_map[pg_name] = 0

                rooms = pg_info.get("rooms", {})
                if isinstance(rooms, dict):
                    for r_id, r_info in rooms.items():
                        if isinstance(r_info, dict):
                            beds = r_info.get("beds", {})
                            if isinstance(beds, dict):
                                total_beds += len(beds)
                                for b_id, b_info in beds.items():
                                    if isinstance(b_info, dict) and b_info.get("is_occupied"):
                                        occupied_beds += 1

            vacant_beds = max(0, total_beds - occupied_beds)

            # Occupancy Overview
            occ_total = total_beds if total_beds > 0 else (occupied_beds + vacant_beds)
            if occ_total > 0:
                occ_perc = round((occupied_beds / occ_total) * 100, 1)
                vac_perc = round((vacant_beds / occ_total) * 100, 1)
            else:
                occ_perc, vac_perc = 0.0, 0.0

            occupancy_overview = {
                "occupied_beds": {"count": occupied_beds, "percentage": occ_perc},
                "vacant_beds": {"count": vacant_beds, "percentage": vac_perc}
            }

            # 2. Fetch Members & Calculate Status Distribution + PG Revenue
            members_res = requests.get(f"{DATABASE_URL}/members.json")
            members_data = members_res.json() if members_res.status_code == 200 and members_res.json() else {}

            active_cnt = 0
            notice_cnt = 0
            inactive_cnt = 0
            vacant_left_cnt = 0

            monthly_trend_map = {}

            for m_id, m_info in members_data.items():
                if not m_info:
                    continue

                is_deleted = m_info.get("is_deleted")
                m_status = m_info.get("status", "")
                rent_val = 0
                try:
                    rent_val = int(m_info.get("monthly_rent", 0))
                except (ValueError, TypeError):
                    pass

                pg_id = m_info.get("pg_id", "")
                if pg_id and pg_id in pgs_data:
                    pg_info = pgs_data[pg_id]
                    pg_name = pg_info.get("property_name", pg_info.get("pg_name", pg_info.get("name", pg_id)))
                    if pg_name in pg_revenue_map:
                        pg_revenue_map[pg_name] += rent_val

                created_at = m_info.get("created_at", "")
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at)
                        month_abbr = dt.strftime("%b")
                        monthly_trend_map[month_abbr] = monthly_trend_map.get(month_abbr, 0) + rent_val
                    except Exception:
                        pass

                if is_deleted:
                    vacant_left_cnt += 1
                elif m_status == "Active":
                    active_cnt += 1
                elif m_status == "Notice Period":
                    notice_cnt += 1
                elif m_status == "Inactive":
                    inactive_cnt += 1
                else:
                    active_cnt += 1

            total_dist_base = active_cnt + notice_cnt + inactive_cnt + vacant_left_cnt
            if total_dist_base == 0:
                total_dist_base = 1

            member_status_distribution = {
                "active": {
                    "count": active_cnt,
                    "percentage": round((active_cnt / total_dist_base) * 100, 1)
                },
                "notice_period": {
                    "count": notice_cnt,
                    "percentage": round((notice_cnt / total_dist_base) * 100, 1)
                },
                "inactive": {
                    "count": inactive_cnt,
                    "percentage": round((inactive_cnt / total_dist_base) * 100, 1)
                },
                "vacant_left": {
                    "count": vacant_left_cnt,
                    "percentage": round((vacant_left_cnt / total_dist_base) * 100, 1)
                }
            }

            # Revenue by PG list
            revenue_by_pg = [
                {"pg_name": name, "revenue": rev}
                for name, rev in pg_revenue_map.items()
            ]
            revenue_by_pg.sort(key=lambda x: x["revenue"], reverse=True)

            # Monthly rent collection trend list
            monthly_rent_collection_trend = []
            for month_name, amt in monthly_trend_map.items():
                monthly_rent_collection_trend.append({"month": month_name, "amount": amt})

            return Response({
                "monthly_rent_collection_trend": monthly_rent_collection_trend,
                "revenue_by_pg": revenue_by_pg,
                "occupancy_overview": occupancy_overview,
                "member_status_distribution": member_status_distribution
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DashboardTablesView(APIView):
    """
    GET API to calculate and return dashboard tables data (upcoming rent dues and recent payments) dynamically from Firebase.
    """
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        if not DATABASE_URL:
            return Response(
                {"detail": "Firebase database URL is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            # Parallel fetch of PGs, Members, Rent Records, and Payments
            nodes = fetch_nodes_parallel({
                "pgs": f"{DATABASE_URL}/pg_properties.json",
                "members": f"{DATABASE_URL}/members.json",
                "rent": f"{DATABASE_URL}/rent_records.json",
                "payments": f"{DATABASE_URL}/payments.json"
            })
            pgs_data = nodes["pgs"]
            members_data = nodes["members"]
            rent_data = nodes["rent"]
            payments_data = nodes["payments"]

            today = datetime.now(ZoneInfo("Asia/Kolkata")).date()

            upcoming_rent_due = []
            recent_payments = []

            # Build lookup maps for Member name and PG details
            member_map = {}
            for m_id, m_info in members_data.items():
                if isinstance(m_info, dict):
                    member_map[m_id] = m_info

            pg_map = {}
            for pg_id, pg_info in pgs_data.items():
                if isinstance(pg_info, dict):
                    pg_map[pg_id] = pg_info

            # Process Rent Records for Upcoming Rent Due
            for r_id, r_info in rent_data.items():
                if not r_info or not isinstance(r_info, dict):
                    continue

                r_status = str(r_info.get("status", "")).lower()
                m_id = r_info.get("member_id", r_id)
                m_info = member_map.get(m_id, {})
                
                if m_info.get("is_deleted"):
                    continue

                m_name = m_info.get("full_name", r_info.get("member_name", "Unknown Member"))
                pg_id = r_info.get("pg_id", m_info.get("pg_id", ""))
                pg_info = pg_map.get(pg_id, {})
                pg_name = pg_info.get("property_name", pg_info.get("pg_name", pg_info.get("name", pg_id)))

                room_id = m_info.get("room_id", "")
                room_number = room_id
                if pg_id and "rooms" in pg_info and isinstance(pg_info.get("rooms"), dict) and room_id in pg_info["rooms"]:
                    room_info = pg_info["rooms"][room_id]
                    if isinstance(room_info, dict):
                        room_number = room_info.get("room_number", room_info.get("room_name", room_number))

                try:
                    rent_amt = int(r_info.get("monthly_rent", m_info.get("monthly_rent", 0)))
                except (ValueError, TypeError):
                    rent_amt = 0

                due_date_str = str(r_info.get("rent_due_date", m_info.get("rent_due_date", "")))

                # Calculate days left
                days_left = 0
                formatted_due_date = due_date_str
                if due_date_str:
                    try:
                        if len(due_date_str) <= 2:
                            day_num = int(due_date_str)
                            due_dt = date(today.year, today.month, day_num)
                            if due_dt < today:
                                month_val = today.month % 12 + 1
                                year_val = today.year + (1 if today.month == 12 else 0)
                                due_dt = date(year_val, month_val, day_num)
                            formatted_due_date = due_dt.strftime("%Y-%m-%d")
                            days_left = (due_dt - today).days
                        else:
                            dt = datetime.fromisoformat(due_date_str).date()
                            formatted_due_date = dt.strftime("%Y-%m-%d")
                            days_left = (dt - today).days
                    except Exception:
                        pass

                if r_status == "paid":
                    recent_payments.append({
                        "payment_id": f"PAY_{r_id}",
                        "member_id": m_id,
                        "pg_id": pg_id,
                        "member_name": m_name,
                        "pg_name": pg_name,
                        "amount": rent_amt,
                        "date": r_info.get("updated_at", r_info.get("created_at", datetime.now().isoformat())),
                        "status": "Paid"
                    })
                else:
                    upcoming_rent_due.append({
                        "rent_id": r_id,
                        "member_id": m_id,
                        "pg_id": pg_id,
                        "member_name": m_name,
                        "pg_name": pg_name,
                        "room_number": room_number,
                        "rent_amount": rent_amt,
                        "due_date": formatted_due_date,
                        "days_left": max(0, days_left),
                        "status": "Upcoming" if days_left >= 0 else "Overdue"
                    })

            # Process explicit payments node if present
            if payments_data and isinstance(payments_data, dict):
                recent_payments = []
                for p_id, p_info in payments_data.items():
                    if not p_info or not isinstance(p_info, dict):
                        continue
                    m_id = p_info.get("member_id", "")
                    m_info = member_map.get(m_id, {})
                    pg_id = p_info.get("pg_id", m_info.get("pg_id", ""))
                    pg_info = pg_map.get(pg_id, {})
                    pg_name = pg_info.get("property_name", pg_info.get("pg_name", pg_info.get("name", pg_id)))

                    try:
                        amt = int(p_info.get("amount", p_info.get("monthly_rent", 0)))
                    except (ValueError, TypeError):
                        amt = 0

                    recent_payments.append({
                        "payment_id": p_id,
                        "member_id": m_id,
                        "pg_id": pg_id,
                        "member_name": m_info.get("full_name", p_info.get("member_name", "Unknown Member")),
                        "pg_name": pg_name,
                        "amount": amt,
                        "date": p_info.get("date", p_info.get("created_at", datetime.now().isoformat())),
                        "status": p_info.get("status", "Paid")
                    })

            return Response({
                "upcoming_rent_due": upcoming_rent_due,
                "recent_payments": recent_payments
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DashboardAlertsView(APIView):
    """
    GET API to calculate and return dashboard alerts (rent overdue and pending payment approvals) dynamically from Firebase.
    """
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        if not DATABASE_URL:
            return Response(
                {"detail": "Firebase database URL is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            # Parallel fetch of PGs, Members, Rent Records, Payments, and Pending Approvals
            nodes = fetch_nodes_parallel({
                "pgs": f"{DATABASE_URL}/pg_properties.json",
                "members": f"{DATABASE_URL}/members.json",
                "rent": f"{DATABASE_URL}/rent_records.json",
                "payments": f"{DATABASE_URL}/payments.json",
                "pending_approvals": f"{DATABASE_URL}/pending_approvals.json"
            })
            pgs_data = nodes["pgs"]
            members_data = nodes["members"]
            rent_data = nodes["rent"]
            payments_data = nodes["payments"]
            pending_appr_data = nodes["pending_approvals"]
            today = datetime.now(ZoneInfo("Asia/Kolkata")).date()

            rent_overdue = []
            pending_approvals = []

            # Lookup maps
            member_map = {m_id: m_info for m_id, m_info in members_data.items() if isinstance(m_info, dict)}
            pg_map = {pg_id: pg_info for pg_id, pg_info in pgs_data.items() if isinstance(pg_info, dict)}

            # Process Rent Overdue
            for r_id, r_info in rent_data.items():
                if not r_info or not isinstance(r_info, dict):
                    continue

                r_status = str(r_info.get("status", "")).lower()
                if r_status == "paid":
                    continue

                m_id = r_info.get("member_id", r_id)
                m_info = member_map.get(m_id, {})
                if m_info.get("is_deleted"):
                    continue

                m_name = m_info.get("full_name", r_info.get("member_name", "Unknown Member"))
                pg_id = r_info.get("pg_id", m_info.get("pg_id", ""))
                pg_info = pg_map.get(pg_id, {})
                pg_name = pg_info.get("property_name", pg_info.get("pg_name", pg_info.get("name", pg_id)))

                room_id = m_info.get("room_id", "")
                room_number = room_id
                if pg_id and "rooms" in pg_info and isinstance(pg_info.get("rooms"), dict) and room_id in pg_info["rooms"]:
                    room_info = pg_info["rooms"][room_id]
                    if isinstance(room_info, dict):
                        room_number = room_info.get("room_number", room_info.get("room_name", room_number))

                try:
                    rent_amt = int(r_info.get("monthly_rent", m_info.get("monthly_rent", 0)))
                except (ValueError, TypeError):
                    rent_amt = 0

                due_date_str = str(r_info.get("rent_due_date", m_info.get("rent_due_date", "")))

                overdue_by_days = 0
                formatted_due_date = due_date_str

                if due_date_str:
                    try:
                        if len(due_date_str) <= 2:
                            day_num = int(due_date_str)
                            due_dt = date(today.year, today.month, day_num)
                            if due_dt > today:
                                month_val = today.month - 1 if today.month > 1 else 12
                                year_val = today.year - (1 if today.month == 1 else 0)
                                due_dt = date(year_val, month_val, day_num)
                            formatted_due_date = due_dt.strftime("%Y-%m-%d")
                            overdue_by_days = (today - due_dt).days
                        else:
                            dt = datetime.fromisoformat(due_date_str).date()
                            formatted_due_date = dt.strftime("%Y-%m-%d")
                            overdue_by_days = (today - dt).days
                    except Exception:
                        pass

                if overdue_by_days > 0 or r_status == "overdue":
                    rent_overdue.append({
                        "rent_id": r_id,
                        "member_id": m_id,
                        "pg_id": pg_id,
                        "member_name": m_name,
                        "pg_name": pg_name,
                        "room_number": room_number,
                        "rent_amount": rent_amt,
                        "due_date": formatted_due_date,
                        "overdue_by_days": max(1, overdue_by_days),
                        "status": "Overdue"
                    })

            # Process Pending Approvals (from pending_approvals node or payments node)
            combined_pending = {}
            if pending_appr_data and isinstance(pending_appr_data, dict):
                combined_pending.update(pending_appr_data)

            if payments_data and isinstance(payments_data, dict):
                for p_id, p_info in payments_data.items():
                    if isinstance(p_info, dict) and str(p_info.get("status", "")).lower() in ["pending", "pending_approval", "pending approval"]:
                        combined_pending[p_id] = p_info

            for p_id, p_info in combined_pending.items():
                if not p_info or not isinstance(p_info, dict):
                    continue
                m_id = p_info.get("member_id", "")
                m_info = member_map.get(m_id, {})
                pg_id = p_info.get("pg_id", m_info.get("pg_id", ""))
                pg_info = pg_map.get(pg_id, {})
                pg_name = pg_info.get("property_name", pg_info.get("pg_name", pg_info.get("name", pg_id)))

                try:
                    amt = int(p_info.get("amount", p_info.get("monthly_rent", 0)))
                except (ValueError, TypeError):
                    amt = 0

                pending_approvals.append({
                    "payment_id": p_id,
                    "member_id": m_id,
                    "pg_id": pg_id,
                    "member_name": m_info.get("full_name", p_info.get("member_name", "Unknown Member")),
                    "pg_name": pg_name,
                    "amount": amt,
                    "payment_type": p_info.get("payment_type", p_info.get("mode", "UPI")),
                    "submitted_on": p_info.get("submitted_on", p_info.get("created_at", datetime.now().isoformat()))
                })

            return Response({
                "rent_overdue": rent_overdue,
                "pending_approvals": pending_approvals
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




