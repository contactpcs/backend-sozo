"""User routes - HTTP layer using Supabase client."""
import logging
from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timezone
import uuid

from app.core.database import db_manager
from app.core.security import PasswordManager, JWTManager
from app.shared.schemas.auth import LoginRequest, TokenResponse, JWTClaims
from app.core.dependencies import get_current_user
from .schemas import UserCreate, UserResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["users"], prefix="/users")
pwd_manager = PasswordManager()
jwt_manager = JWTManager()

# In-memory store for demo (replace with Supabase once table is set up)
registered_users = {}


async def get_role_permissions(role_id: str) -> list[str]:
    """Fetch permissions for a given role_id.
    
    Returns list of permissions in format: ["resource:action", ...]
    Example: ["PATIENT:READ", "PATIENT:CREATE", "REPORT:READ"]
    """
    try:
        logger.info(f"Fetching permissions for role_id: {role_id}")
        
        # Step 1: Get permission_ids from role_permissions table
        role_perms_response = await db_manager.query_table(
            "role_permissions", 
            filters={"role_id": role_id}
        )
        logger.info(f"Role permissions response: {role_perms_response}")
        
        if role_perms_response.get("error"):
            logger.error(f"Error querying role_permissions: {role_perms_response.get('error')}")
            return []
        
        role_perms_data = role_perms_response.get("data", [])
        if not role_perms_data:
            logger.warning(f"No permissions found for role_id: {role_id}")
            return []
        
        # Step 2: Get all permission_ids
        permission_ids = [
            rp.get("permission_id") 
            for rp in role_perms_data 
            if rp.get("permission_id")
        ]
        logger.info(f"Found {len(permission_ids)} permission IDs: {permission_ids}")
        
        if not permission_ids:
            logger.warning(f"No permission_ids extracted from role_permissions")
            return []
        
        # Step 3: Fetch resource:action for each permission_id
        permissions = []
        for perm_id in permission_ids:
            perm_response = await db_manager.query_table(
                "permissions",
                filters={"permission_id": perm_id}
            )
            
            if perm_response.get("error"):
                logger.error(f"Error querying permission {perm_id}: {perm_response.get('error')}")
                continue
            
            perm_data = perm_response.get("data", [])
            if perm_data:
                perm = perm_data[0]
                resource = perm.get("resource", "")
                action = perm.get("action", "")
                
                if resource and action:
                    permission_str = f"{resource}:{action}"
                    permissions.append(permission_str)
                    logger.info(f"Added permission: {permission_str}")
        
        logger.info(f"Total permissions fetched: {len(permissions)} - {permissions}")
        return permissions
        
    except Exception as e:
        logger.error(f"Error fetching role permissions: {str(e)}", exc_info=True)
        return []


@router.get("/debug/check-role/{user_email}")
async def debug_check_user_role(user_email: str):
    """Debug endpoint to check what role a user has in the database.
    
    USE THIS TO DEBUG: /api/v1/users/debug/check-role/doctor@example.com
    """
    try:
        logger.info(f"=== DEBUG: Checking role for {user_email} ===")
        
        # Find user by email
        user_response = await db_manager.query_table("users", filters={"email": user_email})
        logger.info(f"Step 1 - User query response: {user_response}")
        
        if not user_response.get("data") or len(user_response["data"]) == 0:
            return {
                "status": "ERROR",
                "step": "1_user_lookup",
                "error": "User not found in users table",
                "email": user_email,
                "suggestion": "Register this user first"
            }
        
        user = user_response["data"][0]
        user_id = user.get("user_id") or user.get("id")
        
        if not user_id:
            return {
                "status": "ERROR",
                "step": "1_user_lookup",
                "error": "User record has no user_id or id field",
                "available_fields": list(user.keys()),
                "suggestion": "Database schema issue - check column names"
            }
        
        logger.info(f"Step 2 - Found user_id: {user_id}")
        
        # Get user's role from user_roles table
        user_roles_response = await db_manager.query_table("user_roles", filters={"user_id": user_id})
        logger.info(f"Step 3 - user_roles query response: {user_roles_response}")
        
        if user_roles_response.get("error"):
            return {
                "status": "ERROR",
                "step": "2_user_roles_lookup",
                "error": "Database error querying user_roles",
                "db_error": user_roles_response.get("error"),
                "user_id": user_id,
                "suggestion": "Check if user_roles table exists and has correct permissions"
            }
        
        if not user_roles_response.get("data") or len(user_roles_response["data"]) == 0:
            return {
                "status": "ERROR",
                "step": "2_user_roles_lookup",
                "error": "No role assignment found in user_roles table!",
                "user_id": user_id,
                "email": user_email,
                "suggestion": "User exists but has no entry in user_roles table. Re-register this user or manually insert into user_roles.",
                "sql_check": f"SELECT * FROM user_roles WHERE user_id = '{user_id}'"
            }
        
        user_role_record = user_roles_response["data"][0]
        role_id = user_role_record.get("role_id") or user_role_record.get("roleId")
        
        if not role_id:
            return {
                "status": "ERROR",
                "step": "2_user_roles_lookup",
                "error": "user_roles record has no role_id field",
                "available_fields": list(user_role_record.keys()),
                "suggestion": "Database schema issue - check column names in user_roles table"
            }
        
        logger.info(f"Step 4 - Found role_id: {role_id}")
        
        # Get role details
        role_response = await db_manager.query_table("roles", filters={"role_id": role_id})
        logger.info(f"Step 5 - roles query response: {role_response}")
        
        if role_response.get("error"):
            return {
                "status": "ERROR",
                "step": "3_roles_lookup",
                "error": "Database error querying roles",
                "db_error": role_response.get("error"),
                "role_id": role_id,
                "suggestion": "Check if roles table exists and has correct permissions"
            }
        
        if not role_response.get("data") or len(role_response["data"]) == 0:
            return {
                "status": "ERROR",
                "step": "3_roles_lookup",
                "error": "Role ID exists in user_roles but not found in roles table!",
                "user_id": user_id,
                "email": user_email,
                "role_id": role_id,
                "suggestion": "Database integrity issue - the role_id in user_roles doesn't match any role in roles table",
                "sql_check": f"SELECT * FROM roles WHERE role_id = '{role_id}'"
            }
        
        role = role_response["data"][0]
        role_name = role.get("role_name") or role.get("roleName")
        
        if not role_name:
            return {
                "status": "ERROR",
                "step": "3_roles_lookup",
                "error": "Role record has no role_name field",
                "available_fields": list(role.keys()),
                "suggestion": "Database schema issue - check column names in roles table"
            }
        
        # Map to internal role - matches actual Supabase database role names
        role_name_reverse_map = {
            "PATIENT": "patient",
            "DOCTOR": "doctor",
            "CLINICAL_ASSISTANT": "clinical_assistant",
            "SUPER_ADMIN": "super_admin",
            "PLATFORM_ADMIN": "platform_admin",
            "CLINICAL_ADMIN": "clinical_admin",
            "RECEPTIONIST": "receptionist",
        }
        internal_role = role_name_reverse_map.get(role_name, "patient")
        
        return {
            "✓✓✓ status": "SUCCESS",
            "email": user_email,
            "user_id": user_id,
            "role_id": role_id,
            "role_in_database": role_name,
            "role_in_jwt_token": internal_role,
            "role_description": role.get("description"),
            "assigned_at": user_role_record.get("assigned_at"),
            "full_chain": {
                "1_users_table": {"user_id": user_id, "email": user_email},
                "2_user_roles_table": {"user_id": user_id, "role_id": role_id},
                "3_roles_table": {"role_id": role_id, "role_name": role_name}
            },
            "message": f"This user will login with role: '{internal_role}'"
        }
        
    except Exception as e:
        logger.error(f"Debug check failed: {str(e)}", exc_info=True)
        return {
            "status": "EXCEPTION",
            "error": str(e),
            "email": user_email,
            "suggestion": "Check backend logs for full error details"
        }


@router.get("/roles")
async def get_all_roles():
    """Get all available roles from roles table.
    
    Used by frontend to populate role dropdown during registration.
    """
    try:
        logger.info("Fetching all roles from database")
        roles_response = await db_manager.query_table("roles")
        logger.info(f"Roles response: {roles_response}")
        
        if roles_response.get("error"):
            logger.error(f"Failed to fetch roles: {roles_response['error']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch roles"
            )
        
        roles = roles_response.get("data", [])
        
        # Format response for frontend
        formatted_roles = [
            {
                "role_id": role.get("role_id"),
                "role_name": role.get("role_name"),
                "description": role.get("description")
            }
            for role in roles
        ]
        
        logger.info(f"Returning {len(formatted_roles)} roles")
        return {
            "roles": formatted_roles,
            "count": len(formatted_roles)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching roles: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch roles"
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate):
    """Register new user and assign role.
    
    1. Creates user in Supabase users table
    2. Queries roles table for the selected role (or defaults to 'patient')
    3. Inserts into user_roles junction table to link user with role
    """
    try:
        # First, check if user already exists in Supabase
        logger.info(f"Checking if user exists: {user_data.email}")
        existing_user_response = await db_manager.query_table("users", filters={"email": user_data.email})
        logger.info(f"Query response: {existing_user_response}")
        
        if existing_user_response.get("data") and len(existing_user_response["data"]) > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email {user_data.email} already exists"
            )
        
        # Also check in-memory for consistency
        if user_data.email in registered_users:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email {user_data.email} already exists"
            )
        
        # Generate user ID
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        # Hash password
        hashed_password = pwd_manager.hash_password(user_data.password)
        
        # Prepare user record for Supabase (WITHOUT role column)
        supabase_user_record = {
            "user_id": user_id,
            "email": user_data.email,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "hashed_password": hashed_password,
            "phone": user_data.phone,
            "is_active": True,
            "verified_email": False,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        
        logger.info(f"Attempting to insert user to Supabase: {supabase_user_record}")
        
        # INSERT TO SUPABASE FIRST - this is the source of truth
        insert_response = await db_manager.insert_record("users", supabase_user_record)
        
        if insert_response.get("error"):
            error_detail = insert_response['error']
            logger.error(f"Supabase insert failed: {error_detail}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {error_detail}"
            )
        
        logger.info(f"User successfully inserted to Supabase: {user_data.email}")
        
        # NOW assign role - map UserRole enum to Supabase role table names
        # Updated to match actual Supabase database role names
        role_name_map = {
            "patient": "PATIENT",
            "doctor": "DOCTOR",
            "clinical_assistant": "CLINICAL_ASSISTANT",
            "super_admin": "SUPER_ADMIN",
            "platform_admin": "PLATFORM_ADMIN",
            "clinical_admin": "CLINICAL_ADMIN",
            "receptionist": "RECEPTIONIST",
        }
        
        # Get the role from user data, default to patient if not specified
        role_enum_value = user_data.role.value if user_data.role else "patient"
        role_name = role_name_map.get(role_enum_value, "PATIENT_PORTAL")
        
        logger.info(f"Looking for role: {role_name}")
        
        # Query roles table to get role_id
        roles_response = await db_manager.query_table("roles", filters={"role_name": role_name})
        logger.info(f"Roles query response: {roles_response}")
        
        role_id = None
        if roles_response.get("data") and len(roles_response["data"]) > 0:
            role_id = roles_response["data"][0]["role_id"]
            logger.info(f"Found role_id: {role_id} for role: {role_name}")
        else:
            # If role not found, try to get patient role as default
            logger.warning(f"Role not found: {role_name}, trying default PATIENT")
            patient_response = await db_manager.query_table("roles", filters={"role_name": "PATIENT"})
            if patient_response.get("data") and len(patient_response["data"]) > 0:
                role_id = patient_response["data"][0]["role_id"]
                logger.info(f"Using default patient role_id: {role_id}")
            else:
                logger.error("Could not find PATIENT role in database")
        
        # Insert into user_roles junction table
        if role_id:
            user_role_record = {
                "user_id": user_id,
                "role_id": role_id,
                "assigned_at": now.isoformat(),
            }
            logger.info(f"Assigning role to user: {user_role_record}")
            
            role_insert_response = await db_manager.insert_record("user_roles", user_role_record)
            if role_insert_response.get("error"):
                logger.error(f"Failed to assign role: {role_insert_response['error']}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to assign role: {role_insert_response['error']}"
                )
            else:
                logger.info(f"User role assigned successfully: {user_id} -> {role_name}")
        else:
            logger.error("Could not assign role - role_id not found")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to assign role to user"
            )
        
        # Store in memory (only after successful Supabase operations)
        user_record = {
            "user_id": user_id,
            "email": user_data.email,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "phone": user_data.phone,
            "role": role_enum_value,
            "is_active": True,
            "verified_email": False,
            "created_at": now,
            "updated_at": now,
            "hashed_password": hashed_password,
        }
        registered_users[user_data.email] = user_record
        logger.info(f"User stored in memory: {user_data.email}")
        
        logger.info(f"User registered successfully: {user_data.email}")
        
        # Return user response
        return UserResponse(
            id=user_id,
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            role=user_data.role,
            is_active=True,
            verified_email=False,
            created_at=now,
            updated_at=now,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/test-insert")
async def test_insert():
    """Debug endpoint to test Supabase insert with full user_roles flow."""
    import uuid
    from datetime import datetime
    
    test_user_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Test user record (WITHOUT role column)
    test_record = {
        "user_id": test_user_id,
        "email": f"test-{now.timestamp()}@example.com",
        "first_name": "Test",
        "last_name": "User",
        "hashed_password": pwd_manager.hash_password("testpass123"),
        "phone": "555-0000",
        "is_active": True,
        "verified_email": False,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    
    logger.info(f"Testing Supabase user insert: {test_record}")
    
    # Insert user
    user_insert_result = await db_manager.insert_record("users", test_record)
    logger.info(f"User insert result: {user_insert_result}")
    
    if user_insert_result.get("error"):
        return {
            "success": False,
            "user_result": user_insert_result,
            "role_result": None,
            "error": user_insert_result.get("error")
        }
    
    # Now get PATIENT role and assign it
    logger.info("Querying for PATIENT role...")
    role_query_result = await db_manager.query_table("roles", filters={"role_name": "PATIENT"})
    logger.info(f"Role query result: {role_query_result}")
    
    role_id = None
    if role_query_result.get("data") and len(role_query_result["data"]) > 0:
        role_id = role_query_result["data"][0]["role_id"]
        
        # Create user_role entry
        test_user_role = {
            "user_id": test_user_id,
            "role_id": role_id,
            "assigned_at": now.isoformat(),
        }
        
        logger.info(f"Testing user_roles insert: {test_user_role}")
        user_role_insert_result = await db_manager.insert_record("user_roles", test_user_role)
        logger.info(f"User role insert result: {user_role_insert_result}")
        
        return {
            "success": user_insert_result.get("error") is None and user_role_insert_result.get("error") is None,
            "user_result": user_insert_result,
            "role_result": user_role_insert_result,
            "test_user_id": test_user_id,
            "test_email": test_record["email"],
            "role_id": role_id
        }
    else:
        return {
            "success": False,
            "user_result": user_insert_result,
            "role_result": None,
            "error": "PATIENT role not found in roles table"
        }


@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: JWTClaims = Depends(get_current_user)):
    """Return basic profile for the currently authenticated user.

    This endpoint returns the user's profile information derived from the JWT claims.
    """
    try:
        now = datetime.now(timezone.utc)
        role = current_user.roles[0] if current_user.roles else "patient"
        return UserResponse(
            id=current_user.user_id,
            email=current_user.email,
            first_name=current_user.first_name or "",
            last_name="",
            phone=None,
            role=role,
            is_active=True,
            verified_email=False,
            created_at=now,
            updated_at=now,
        )
    except Exception as e:
        logger.error(f"Failed to build profile response: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch profile")


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    """Login user with JWT token generation.
    
    1. Verifies email and password against users table
    2. Gets user's role from user_roles and roles tables
    3. Creates JWT token with user info and role
    """
    try:
        # First try to check Supabase database
        logger.info(f"Login attempt for: {credentials.email}")
        user_response = await db_manager.query_table("users", filters={"email": credentials.email})
        
        user_data = None
        if user_response.get("data") and len(user_response["data"]) > 0:
            user_data = user_response["data"][0]
            logger.info(f"User found in Supabase: {credentials.email}")
        
        # Fallback to in-memory store
        if not user_data:
            user_record = registered_users.get(credentials.email)
            if user_record:
                logger.info(f"User found in memory: {credentials.email}")
                user_data = user_record
        
        # If user not found anywhere
        if not user_data:
            logger.warning(f"User not found: {credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password if we have hashed_password
        if "hashed_password" in user_data:
            if not pwd_manager.verify_password(credentials.password, user_data["hashed_password"]):
                logger.warning(f"Invalid password for user: {credentials.email}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
        
        # Get user info - handle different possible field names
        user_id = user_data.get("user_id") or user_data.get("id")
        if not user_id:
            logger.error(f"✗ No user_id or id field found in user data: {user_data.keys()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User ID not found in database"
            )
        
        logger.info(f"=== ROLE LOOKUP START for user_id: {user_id} ===")
        
        # Get user's role from user_roles table
        user_role = "patient"  # default role
        role_id = None  # Initialize role_id to use later for permissions
        try:
            logger.info(f"Step 1: Querying user_roles table with user_id: {user_id}")
            user_roles_response = await db_manager.query_table("user_roles", filters={"user_id": user_id})
            logger.info(f"Step 1 Response: {user_roles_response}")
            
            if user_roles_response.get("error"):
                logger.error(f"✗ Database error querying user_roles: {user_roles_response.get('error')}")
                raise Exception(f"Database error: {user_roles_response.get('error')}")
            
            if user_roles_response.get("data") and len(user_roles_response["data"]) > 0:
                user_role_record = user_roles_response["data"][0]
                logger.info(f"Step 2: Found user_role record: {user_role_record}")
                
                # Handle different possible field names for role_id
                role_id = user_role_record.get("role_id") or user_role_record.get("roleId")
                if not role_id:
                    logger.error(f"✗ No role_id field in user_role record. Available fields: {user_role_record.keys()}")
                    raise Exception("role_id field not found in user_roles table")
                
                logger.info(f"Step 3: Found role_id: {role_id}, now querying roles table")
                
                # Get role details from roles table
                role_response = await db_manager.query_table("roles", filters={"role_id": role_id})
                logger.info(f"Step 3 Response: {role_response}")
                
                if role_response.get("error"):
                    logger.error(f"✗ Database error querying roles: {role_response.get('error')}")
                    raise Exception(f"Database error: {role_response.get('error')}")
                
                if role_response.get("data") and len(role_response["data"]) > 0:
                    role_record = role_response["data"][0]
                    logger.info(f"Step 4: Found role record: {role_record}")
                    
                    # Handle different possible field names
                    role_name = role_record.get("role_name") or role_record.get("roleName")
                    if not role_name:
                        logger.error(f"✗ No role_name field in role record. Available fields: {role_record.keys()}")
                        raise Exception("role_name field not found in roles table")
                    
                    logger.info(f"Step 5: Role name from DB: {role_name}")
                    
                    # Map Supabase role name back to our role enum
                    # Updated to match actual Supabase database role names
                    role_name_reverse_map = {
                        "PATIENT": "patient",
                        "DOCTOR": "doctor",
                        "CLINICAL_ASSISTANT": "clinical_assistant",
                        "SUPER_ADMIN": "super_admin",
                        "PLATFORM_ADMIN": "platform_admin",
                        "CLINICAL_ADMIN": "clinical_admin",
                        "RECEPTIONIST": "receptionist",
                    }
                    user_role = role_name_reverse_map.get(role_name, "patient")
                    logger.info(f"✓✓✓ SUCCESS: User role resolved: {user_role} (from DB role: {role_name})")
                else:
                    logger.error(f"✗ NO ROLE FOUND in roles table for role_id: {role_id}")
                    logger.error(f"   This means the role_id in user_roles doesn't match any role in roles table")
            else:
                logger.error(f"✗ NO USER_ROLE RECORD found in user_roles table for user_id: {user_id}")
                logger.error(f"   The user exists but has no entry in user_roles table!")
                logger.error(f"   This user was likely registered incorrectly - user will default to 'patient'")
        except Exception as e:
            logger.error(f"✗✗✗ EXCEPTION while fetching user role: {str(e)}", exc_info=True)
            logger.error(f"   User will default to 'patient' role - CHECK THE LOGS ABOVE!")
        
        logger.info(f"=== ROLE LOOKUP END: Final role = {user_role} ===")

        # Fetch role permissions
        permissions = []
        if role_id:
            logger.info(f"Fetching permissions for role_id: {role_id}")
            permissions = await get_role_permissions(role_id)
            logger.info(f"Permissions for role {user_role}: {permissions}")
        else:
            logger.warning("No role_id available to fetch permissions")
        
        # Create JWT tokens
        access_token = jwt_manager.create_access_token(
            user_id=user_id,
            user_email=credentials.email,
            roles=[user_role],
            user_first_name=user_data.get("first_name") if isinstance(user_data, dict) else None,
            permissions=permissions,
        )
        
        refresh_token = jwt_manager.create_refresh_token(user_id)
        
        # Prepare user data for response
        user_response_data = {
            "user_id": user_id,
            "email": user_data.get("email"),
            "first_name": user_data.get("first_name"),
            "last_name": user_data.get("last_name"),
            "role": user_role,
            "is_active": user_data.get("is_active", True),
        }
        
        logger.info(f"User login successful: {credentials.email}")
        logger.info(f"User response data: {user_response_data}")
        
        response = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600,
            user=user_response_data
        )
        
        logger.info(f"TokenResponse dict: {response.model_dump()}")
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )