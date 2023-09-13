from fastapi import APIRouter, HTTPException, status, Depends
from models.users.user import *
from routers.jwt_auth_users import role_current_user
from services import users_service
from models.responses.api_response import ApiResponse

router_user = APIRouter()


@router_user.post(path="/users/bulk", response_model=ApiResponse, response_description="User created successfully",
                  status_code=status.HTTP_201_CREATED, dependencies=[Depends(role_current_user)])
async def create_user_bulk(user: UserDTO):
    user_created = await users_service.process_create_user(first_name=user.first_name, gender=user.gender,
                                                           roles=user.roles, password=user.password,
                                                           in_charge=user.in_charge, managed_by=user.managed_by,
                                                           user_id=user.id, last_name=user.last_name)

    return ApiResponse(success=True,
                       message=f"User {user_created['id']} created successfully",
                       data=UserResponse(**user_created))


@router_user.post(path="/users", response_model=ApiResponse, response_description="User created successfully",
                  status_code=status.HTTP_201_CREATED, dependencies=[Depends(role_current_user)])
async def create_user(
        first_name: str,
        gender: Gender,
        roles: List[Role],
        password: str,
        in_charge: Optional[Set[UUID]] = None,
        managed_by: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        last_name: Optional[str] = None):
    user_created = await users_service.process_create_user(first_name=first_name, gender=gender, roles=roles,
                                                           password=password, in_charge=in_charge,
                                                           managed_by=managed_by, user_id=user_id, last_name=last_name)

    return ApiResponse(success=True,
                       message=f"User {user_created['id']} created successfully",
                       data=UserResponse(**user_created))


@router_user.get(path="/users", response_model=ApiResponse, status_code=status.HTTP_200_OK)
async def get_all(total_number: Optional[int] = None):

    return ApiResponse(success=True, message="Data found", data=await users_service.process_get_all_users(total_number))


@router_user.get("/users/{user_id}", response_model=ApiResponse, status_code=status.HTTP_200_OK)
async def get(user_id: UUID):
    return ApiResponse(success=True,
                       message="Data found",
                       data=UserResponse(**await users_service.process_get_user(user_id)))


@router_user.put(path="/users/{user_id}", response_model=ApiResponse,
                 response_description="User updated successfully",
                 status_code=status.HTTP_200_OK, dependencies=[Depends(role_current_user)])
async def put(user_id: UUID,
              first_name: str,
              gender: Gender,
              roles: List[Role],
              in_charge: Optional[List[UUID]] = None,
              managed_by: Optional[UUID] = None,
              last_name: Optional[str] = None):
    updated_user = await users_service.process_update_user(user_id=user_id, first_name=first_name, gender=gender,
                                                           roles=roles,
                                                           in_charge=in_charge, managed_by=managed_by,
                                                           last_name=last_name)

    return ApiResponse(success=True,
                       message=f"User {user_id} updated",
                       data=UserResponse(**updated_user))


@router_user.put(path="/users/{user_id}/bulk", response_model=UserResponse,
                 response_description="User updated successfully",
                 status_code=status.HTTP_200_OK, dependencies=[Depends(role_current_user)])
async def put_bulk(user: UserDTO):
    updated_user = await users_service.process_update_user(user_id=user.id, first_name=user.first_name,
                                                           gender=user.gender,
                                                           roles=user.roles, in_charge=user.in_charge,
                                                           managed_by=user.managed_by, last_name=user.last_name)

    return ApiResponse(success=True,
                       message=f"User {user.id} updated",
                       data=UserResponse(**updated_user))


@router_user.patch(path="/users/{user_id}", response_model=ApiResponse,
                   response_description="User patched successfully", status_code=status.HTTP_200_OK)
async def patch(user_id: UUID,
                first_name: Optional[str] = None,
                last_name: Optional[str] = None,
                gender: Optional[Gender] = None,
                roles: Optional[List[Role]] = None,
                managed_by: Optional[UUID] = None,
                in_charge: Optional[Set[UUID]] = None):
    if not first_name and not last_name and not gender and not roles and not managed_by and not in_charge:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"No field modified")

    patched_user = await users_service.process_patch_user(user_id, first_name, last_name,
                                                          gender, roles, managed_by, in_charge)
    return ApiResponse(success=True,
                       message=f"User {user_id} patched",
                       data=UserResponse(**patched_user))


@router_user.delete(path="/users/{user_id}", response_model=ApiResponse,
                    response_description="User deleted successfully",
                    status_code=status.HTTP_200_OK, dependencies=[Depends(role_current_user)])
async def delete(user_id: UUID):
    deleted_user = await users_service.process_delete_user(user_id)
    return ApiResponse(success=True,
                       message=f"User {user_id} deleted successfully",
                       data=UserResponse(**deleted_user))


@router_user.delete(path="/users", status_code=status.HTTP_200_OK, response_model=ApiResponse,
                    response_description="All users deleted successfully", dependencies=[Depends(role_current_user)])
async def delete_all():
    await users_service.process_delete_all_users()
    return ApiResponse(success=True, message="All users deleted successfully")