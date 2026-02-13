"""User routes - HTTP layer using Supabase client."""
import logging
from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timezone
import uuid

from app.core.database import db_manager
from app.core.security import PasswordManager, JWTManager
from app.shared.schemas.auth import LoginRequest, TokenResponse
from .schemas import UserCreate, UserResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["users"], prefix="/users")
pwd_manager = PasswordManager()
jwt_manager = JWTManager()

# In-memory store for demo (replace with Supabase once table is set up)
registered_users = {}


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
        role_name_map = {
            "patient": "PATIENT_PORTAL",
            "clinician": "DOCTOR_UI",
            "nurse": "CLINIC_ASSISTANT",
            "admin": "SUPER_ADMIN",
            "center_manager": "CLINICIAN_ADMIN",
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
            logger.warning(f"Role not found: {role_name}, trying default PATIENT_PORTAL")
            patient_response = await db_manager.query_table("roles", filters={"role_name": "PATIENT_PORTAL"})
            if patient_response.get("data") and len(patient_response["data"]) > 0:
                role_id = patient_response["data"][0]["role_id"]
                logger.info(f"Using default patient role_id: {role_id}")
            else:
                logger.error("Could not find PATIENT_PORTAL role in database")
        
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
    
    # Now get PATIENT_PORTAL role and assign it
    logger.info("Querying for PATIENT_PORTAL role...")
    role_query_result = await db_manager.query_table("roles", filters={"role_name": "PATIENT_PORTAL"})
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
            "error": "PATIENT_PORTAL role not found in roles table"
        }


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
        
        # Get user info
        user_id = user_data.get("user_id", str(uuid.uuid4()))
        
        # Get user's role from user_roles table
        user_role = "patient"  # default role
        try:
            user_roles_response = await db_manager.query_table("user_roles", filters={"user_id": user_id})
            logger.info(f"User roles response: {user_roles_response}")
            
            if user_roles_response.get("data") and len(user_roles_response["data"]) > 0:
                role_id = user_roles_response["data"][0]["role_id"]
                logger.info(f"Found role_id for user: {role_id}")
                
                # Get role details from roles table
                role_response = await db_manager.query_table("roles", filters={"role_id": role_id})
                logger.info(f"Role response: {role_response}")
                
                if role_response.get("data") and len(role_response["data"]) > 0:
                    role_name = role_response["data"][0]["role_name"]
                    
                    # Map Supabase role name back to our role enum
                    role_name_reverse_map = {
                        "PATIENT_PORTAL": "patient",
                        "DOCTOR_UI": "clinician",
                        "CLINIC_ASSISTANT": "nurse",
                        "SUPER_ADMIN": "admin",
                        "PLATFORM_ADMIN": "admin",
                        "CLINICIAN_ADMIN": "center_manager",
                        "RECEPTIONIST": "patient",
                    }
                    user_role = role_name_reverse_map.get(role_name, "patient")
                    logger.info(f"User role: {user_role} (from {role_name})")
        except Exception as e:
            logger.warning(f"Failed to get user role: {str(e)}, using default 'patient'")
        
        # Create JWT tokens
        access_token = jwt_manager.create_access_token(
            user_id=user_id,
            user_email=credentials.email,
            roles=[user_role]
        )
        
        refresh_token = jwt_manager.create_refresh_token(user_id)
        
        logger.info(f"User login successful: {credentials.email}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )



