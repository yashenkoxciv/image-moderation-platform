import os
import boto3
from typing import Optional, List, Dict

from fastapi import FastAPI, Body, HTTPException, status, UploadFile, File, Query
from fastapi.responses import Response
from pydantic import ConfigDict, BaseModel, Field, EmailStr
from pydantic.functional_validators import BeforeValidator

from typing_extensions import Annotated

from bson import ObjectId
import motor.motor_asyncio
from pymongo import ReturnDocument
import uuid
import httpx
import io
from enum import Enum


app = FastAPI(
    title="Image Moderation Platform API",
    summary="An application for content based image categorization.",
)

client = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGODB_URL"])
db = client.imp
image_collection = db.get_collection("imp-images")

s3 = boto3.client(
    's3',
    endpoint_url=os.environ["OBJ_STORAGE_ENDPOINT_URL"],
    aws_access_key_id=os.environ["OBJ_STORAGE_ACCESS_KEY"],
    aws_secret_access_key=os.environ["OBJ_STORAGE_SECRET_KEY"]
)

# Represents an ObjectId field in the database.
# It will be represented as a `str` on the model so that it can be serialized to JSON.
PyObjectId = Annotated[str, BeforeValidator(str)]


class ModerationCategoryEnum(str, Enum):
    NUDITY: str = "nudity"
    GORE: str = "gore"
    VIOLENCE: str = "violence"
    WEAPONS: str = "weapons"
    DRUGS: str = "drugs"
    
    # FACES means any face, kids, women and so on.
    # in future this parameter can be divided to subcategories:
    # KIDS_FACES, WOMEN_FACES, MEN_FACES
    FACES: str = "faces"
    
    # BODIES means any not nude body (part of the men, excepty the head)
    BODIES: str = "bodies"

    # SYMBOLISM means appearance of any symbols of extremism
    SYMBOLISM: str = "symbolism"

    # Document categories:
    PASSPORT: str = "passport"
    DRIVER_LICENSE: str = "driver license"


class ImageModerationRequestModel(BaseModel):
    categories: List[ModerationCategoryEnum] = Field([], description="Check image content for the categories")
    hide_categories: bool = Field(False, description="Hide object of given categories in image")
    remove_image_metadata: bool = Field(False, description="Remove data like: location, device etc.")
    extra: str | None = None


class ImageModerationReportModel(BaseModel):
    categories: Dict[ModerationCategoryEnum, bool] | None = None
    result_image_key: str | None = None


class ImageModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    image_key: str

    request: ImageModerationRequestModel | None = None
    report: ImageModerationReportModel | None = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )


# class UpdateStudentModel(BaseModel):
#     """
#     A set of optional updates to be made to a document in the database.
#     """

#     name: Optional[str] = None
#     email: Optional[EmailStr] = None
#     course: Optional[str] = None
#     gpa: Optional[float] = None
#     model_config = ConfigDict(
#         arbitrary_types_allowed=True,
#         json_encoders={ObjectId: str},
#         json_schema_extra={
#             "example": {
#                 "name": "Jane Doe",
#                 "email": "jdoe@example.com",
#                 "course": "Experiments, Science, and Fashion in Nanophotonics",
#                 "gpa": 3.0,
#             }
#         },
#     )


# class StudentCollection(BaseModel):
#     """
#     A container holding a list of `StudentModel` instances.

#     This exists because providing a top-level array in a JSON response can be a [vulnerability](https://haacked.com/archive/2009/06/25/json-hijacking.aspx/)
#     """

#     students: List[StudentModel]


@app.post(
    "/image/moderation",
    response_description="Add new image for moderation",
    response_model=ImageModel,
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False,
)
async def image_moderation_request(
    image_moderation_request: ImageModerationRequestModel = Query(),
    image: UploadFile = File(...)
    ):
    image_key = uuid.uuid4().hex
    s3.upload_fileobj(
        image.file,
        os.environ["OBJ_STORAGE_BUCKET"],
        image_key,
        ExtraArgs={'ContentType': image.content_type}
    )
    # report=ImageModerationReportModel(
    #        categories={ModerationCategoryEnum.DRUGS: True, ModerationCategoryEnum.NUDITY: True},
    #        result_image_key=image_key
    #    )
    image_model = ImageModel(image_key=image_key, request=image_moderation_request)
    insert_result = await image_collection.insert_one(image_model.model_dump(by_alias=True, exclude=["id"]))
    
    image_document = await image_collection.find_one({"_id": insert_result.inserted_id})
    image_model = ImageModel(**image_document)
    return image_model

# TODO: add users and divide access rights to admin, cutomers and moderators

# @app.post(
#     "/images/url",
#     response_description="Add new image from URL",
#     response_model=ImageModel,
#     status_code=status.HTTP_201_CREATED,
#     response_model_by_alias=False,
#     description="Example URL: https://d2zp5xs5cp8zlg.cloudfront.net/image-79322-800.jpg"
# )
# async def create_image_from_url(image_url: str):
#     async with httpx.AsyncClient() as http_client:
#         response = await http_client.get(image_url)
#     image_file = io.BytesIO(response.content)
    
#     image_image_key = uuid.uuid4().hex
#     s3.upload_fileobj(
#         image_file,
#         os.environ["OBJ_STORAGE_BUCKET"],
#         image_image_key,
#         ExtraArgs={'ContentType': response.headers['content-type']}
#     )
#     image_model = ImageModel(image_key=image_image_key)
#     insert_result = await image_collection.insert_one(image_model.model_dump(by_alias=True, exclude=["id"]))
    
#     image_document = await image_collection.find_one({"_id": insert_result.inserted_id})
#     image_model = ImageModel(**image_document)
#     return image_model

# @app.post(
#     "/students/",
#     response_description="Add new student",
#     response_model=StudentModel,
#     status_code=status.HTTP_201_CREATED,
#     response_model_by_alias=False,
# )
# async def create_student(student: StudentModel = Body(...)):
#     """
#     Insert a new student record.

#     A unique `id` will be created and provided in the response.
#     """
#     new_student = await image_collection.insert_one(
#         student.model_dump(by_alias=True, exclude=["id"])
#     )
#     created_student = await image_collection.find_one(
#         {"_id": new_student.inserted_id}
#     )
#     return created_student


# @app.get(
#     "/students/",
#     response_description="List all students",
#     response_model=StudentCollection,
#     response_model_by_alias=False,
# )
# async def list_students():
#     """
#     List all of the student data in the database.

#     The response is unpaginated and limited to 1000 results.
#     """
#     return StudentCollection(students=await image_collection.find().to_list(1000))


# @app.get(
#     "/students/{id}",
#     response_description="Get a single student",
#     response_model=StudentModel,
#     response_model_by_alias=False,
# )
# async def show_student(id: str):
#     """
#     Get the record for a specific student, looked up by `id`.
#     """
#     if (
#         student := await image_collection.find_one({"_id": ObjectId(id)})
#     ) is not None:
#         return student

#     raise HTTPException(status_code=404, detail=f"Student {id} not found")


# @app.put(
#     "/students/{id}",
#     response_description="Update a student",
#     response_model=StudentModel,
#     response_model_by_alias=False,
# )
# async def update_student(id: str, student: UpdateStudentModel = Body(...)):
#     """
#     Update individual fields of an existing student record.

#     Only the provided fields will be updated.
#     Any missing or `null` fields will be ignored.
#     """
#     student = {
#         k: v for k, v in student.model_dump(by_alias=True).items() if v is not None
#     }

#     if len(student) >= 1:
#         update_result = await image_collection.find_one_and_update(
#             {"_id": ObjectId(id)},
#             {"$set": student},
#             return_document=ReturnDocument.AFTER,
#         )
#         if update_result is not None:
#             return update_result
#         else:
#             raise HTTPException(status_code=404, detail=f"Student {id} not found")

#     # The update is empty, but we should still return the matching document:
#     if (existing_student := await image_collection.find_one({"_id": id})) is not None:
#         return existing_student

#     raise HTTPException(status_code=404, detail=f"Student {id} not found")


# @app.delete("/students/{id}", response_description="Delete a student")
# async def delete_student(id: str):
#     """
#     Remove a single student record from the database.
#     """
#     delete_result = await image_collection.delete_one({"_id": ObjectId(id)})

#     if delete_result.deleted_count == 1:
#         return Response(status_code=status.HTTP_204_NO_CONTENT)

#     raise HTTPException(status_code=404, detail=f"Student {id} not found")