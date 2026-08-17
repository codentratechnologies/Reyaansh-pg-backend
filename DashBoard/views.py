from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import timedelta
import os
import requests
from dotenv import load_dotenv

from .security import hash_password, create_token, JWTAuthentication, verify_token
from .firebase_client import get_admin_user, create_admin_user, update_last_login

load_dotenv()
DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")

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
            # 1. Fetch PGs
            pg_res = requests.get(f"{DATABASE_URL}/pg_properties.json")
            pgs_data = pg_res.json() if pg_res.status_code == 200 and pg_res.json() else {}

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

            # 2. Fetch Members
            members_res = requests.get(f"{DATABASE_URL}/members.json")
            members_data = members_res.json() if members_res.status_code == 200 and members_res.json() else {}

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
            # 1. Fetch PGs
            pg_res = requests.get(f"{DATABASE_URL}/pg_properties.json")
            pgs_data = pg_res.json() if pg_res.status_code == 200 and pg_res.json() else {}

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


