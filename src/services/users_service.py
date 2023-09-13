from redis_client.crud import set_user, get_user, ResponseError, get_all_users_db, delete_user_db, delete_all_users_db
from models.users.user import *
from schemas.user_schema import get_user_schema, get_users_schema
from fastapi import HTTPException, status
from routers.jwt_auth_users import get_password_hash


async def process_create_user(first_name: str,
                              gender: Gender,
                              roles: List[Role],
                              password: str,
                              in_charge: Optional[Set[UUID]],
                              managed_by: Optional[UUID],
                              user_id: Optional[UUID],
                              last_name: Optional[str]) -> dict:
    if user_id and get_user(str(user_id)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already created")
    try:

        user = UserDB(
            id=user_id,
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            roles=roles,
            in_charge=in_charge,
            managed_by=managed_by,
            hashed_password=get_password_hash(password)
        )
        if user.managed_by:
            manager = UserDB(**get_user_schema(get_user(str(user.managed_by))))
            if not manager:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"Manager with id= {user.managed_by} does not exist")
            elif Role.manager not in manager.roles and Role.admin not in manager.roles:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"Invalid manager with id= {user.managed_by} for user with id={user.id}")
            else:
                # Creating the new user
                set_user(str(user.id), user.model_dump_json())
                # Updating users set managed by the manager
                manager.in_charge.add(user.id)
                set_user(str(manager.id), manager.model_dump_json())

        else:
            # Creating the new user not managed
            set_user(str(user.id), user.model_dump_json())

    except ValueError as value_error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"ERROR: {value_error}")

    except ResponseError as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"ERROR: {error.args}, "
                                                                                      f"the user may not have been "
                                                                                      f"created properly")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"ERROR:"
                                                                                      f"the user may not have been "
                                                                                      f"created properly")
    else:
        return get_user_schema(get_user(str(user.id)))


async def process_get_user(user_id: UUID) -> dict:
    user_id = str(user_id)
    try:
        user = get_user(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User id={user_id} not found")

    except ResponseError as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"ERROR: {error.args}")

    return get_user_schema(user)


async def process_get_all_users(total_number: Optional[int]) -> List[UserResponse]:
    try:
        users = get_all_users_db(total_number)
        if not users:
            return list()
    except ResponseError as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"ERROR: {error.args}")

    return [UserResponse(**dict(user)) for user in get_users_schema(users)]


async def process_update_user(user_id: UUID,
                              first_name: str,
                              gender: Gender,
                              roles: List[Role],
                              in_charge: Optional[Set[UUID]],
                              managed_by: Optional[UUID],
                              last_name: Optional[str]) -> dict:
    try:
        user = await process_get_user(user_id)
        outdated_user = UserDB(**get_user_schema(user))
        updated_user = UserDB(id=user_id,
                              first_name=first_name,
                              last_name=last_name,
                              gender=gender,
                              roles=roles,
                              in_charge=in_charge,
                              managed_by=managed_by,
                              activated_at=outdated_user.activated_at,
                              updated_at=time_ns(),
                              hashed_password=outdated_user.hashed_password)
        # Managers update
        __user_update_managed_by_check(outdated_user, updated_user)
        # User update
        set_user(str(user_id), updated_user.model_dump_json())

    except ValueError as validation_error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"ERROR: {validation_error}")

    except ResponseError as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"DB ERROR: {error.args}, "
                                                                                      f"the user may not have been "
                                                                                      f"updated properly")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"ERROR:"
                                                                                      f"the user may not have been "
                                                                                      f"updated properly")

    return updated_user.model_dump()


async def process_patch_user(user_id: UUID,
                             first_name: Optional[str],
                             last_name: Optional[str],
                             gender: Optional[Gender],
                             roles: Optional[List[Role]],
                             managed_by: Optional[UUID],
                             in_charge: Optional[Set[UUID]]) -> dict:
    try:
        user = await process_get_user(user_id)

        outdated_user = UserDB(**user)
        updated_user = UserDB(id=user_id,
                              first_name=first_name if first_name else outdated_user.first_name,
                              last_name=last_name if last_name else outdated_user.last_name,
                              gender=gender if gender else outdated_user.gender,
                              roles=roles if roles else outdated_user.roles,
                              managed_by=managed_by if managed_by else outdated_user.managed_by,
                              in_charge=in_charge if in_charge else outdated_user.in_charge,
                              activated_at=outdated_user.activated_at,
                              updated_at=time_ns())
        # Managers update
        __user_update_managed_by_check(outdated_user, updated_user)
        # Update
        set_user(str(user_id), updated_user.model_dump_json())
    except ValueError as validation_error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"VALIDATION ERROR: {validation_error.args}")
    except ResponseError as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"ERROR: {error.args}, the user "
                                                                                      f"may not have been patched "
                                                                                      f"properly")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"ERROR: the user "
                                                                                      f"may not have been patched "
                                                                                      f"properly")
    return updated_user.model_dump()


async def process_delete_user(user_id: UUID) -> dict:
    try:
        user = User(**await process_get_user(user_id))
        if user.managed_by:
            manager = User(**await process_get_user(user.managed_by))
            manager.in_charge.remove(user_id)
            set_user(str(manager.id), manager.model_dump_json())

        delete_user_db(str(user.id))

    except ResponseError as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"ERROR: {error.args}, the user "
                                                                                      f"may not have been deleted")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"ERROR: The user "
                                                                                      f"may not have been deleted")
    return user.model_dump()


async def process_delete_all_users() -> None:
    try:
        delete_all_users_db()
    except ResponseError as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"ERROR: {error.args}, "
                                                                                      f"the users may not have been "
                                                                                      f"deleted")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"ERROR:"
                                                                                      f"The users may not have been "
                                                                                      f"deleted")


def __user_update_managed_by_check(outdated_user: User, updated_user: User) -> None:
    # Updating managers 'in_charge' list
    if outdated_user.managed_by != updated_user.managed_by:
        if outdated_user.managed_by:
            outdated_manager = UserDB(**get_user_schema(get_user(str(outdated_user.managed_by))))
            outdated_manager.in_charge.remove(outdated_user.id)
            set_user(str(outdated_manager.id), outdated_manager.model_dump_json())
        if updated_user.managed_by:
            updated_manager = UserDB(**get_user_schema(get_user(str(updated_user.managed_by))))
            updated_manager.in_charge.add(updated_manager.id)
            set_user(str(updated_manager.id), updated_manager.model_dump_json())