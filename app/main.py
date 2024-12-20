import datetime
from math import ceil
from typing import Annotated, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse
from pydantic import AfterValidator, BaseModel, Field

app = FastAPI()

# in memory dictionary of receipt IDs to the calculated points
receipt_points: dict[str, int] = {}


class Item(BaseModel):
    shortDescription: Annotated[
        str, Field(pattern=r"^[\w\s\-]+$"), AfterValidator(lambda sd: sd.strip())
    ]
    price: Annotated[str, Field(pattern=r"^\d+\.\d{2}$")]

    @property
    def price_float(self) -> float:
        return float(self.price)


# Validate that the item list isn't empty
def contains_items(value: List[Item]) -> List[Item]:
    if len(value) == 0:
        raise ValueError("The item list has no items")
    return value


# Validate that the provided purchase time doesn't have timezone info
def offset_naive_time(value: datetime.time) -> datetime.time:
    if isinstance(value.tzinfo, datetime.tzinfo):
        raise ValueError("Time must be offset-naive")
    return value


class Receipt(BaseModel):
    model_config = {"extra": "forbid"}
    retailer: Annotated[str, Field(pattern=r"^[\w\s\-&]+$")]
    purchaseDate: datetime.date

    # 24-hr time expected
    purchaseTime: Annotated[datetime.time, AfterValidator(offset_naive_time)]

    # Min 1 item
    items: Annotated[List[Item], AfterValidator(contains_items)]
    total: Annotated[str, Field(pattern=r"^\d+\.\d{2}$")]

    @property
    def total_float(self) -> float:
        return float(self.total)


def calculate_points(receipt: Receipt) -> int:
    points = 0

    # Count number of alphanumeric chars in retailer name
    points += len(list(filter(lambda r: r.isalnum(), receipt.retailer)))

    # 50 points if total is a round dollar amt w/ no cents
    points += 50 if receipt.total_float.is_integer() else 0

    # 25 points if the total is a multiple of 0.25.
    points += 25 if receipt.total_float % 0.25 == 0 else 0

    # 5 points for every two items on the receipt.
    points += (len(receipt.items) // 2) * 5

    # If the trimmed length of the item description is a multiple of 3, multiply the price by 0.2 and round up to the nearest integer. The result is the number of points earned.
    for item in receipt.items:
        if len(item.shortDescription) % 3 == 0:
            points += ceil(item.price_float * 0.2)

    # 6 points if the day in the purchase date is odd.
    points += 6 if receipt.purchaseDate.day % 2 == 1 else 0

    # 10 points if the time of purchase is after 2:00pm and before 4:00pm.
    if datetime.time(14, 0) < receipt.purchaseTime < datetime.time(16, 0):
        points += 10
    return points


# Custom Exception Handler to return the error message provided in api.yml
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return PlainTextResponse("The receipt is invalid", status_code=400)


@app.get("/")
def read_root():
    return "Receipt Processor Challenge implemented by Mani Sundararajan"


@app.post("/receipts/process")
async def process_receipt(receipt: Receipt):
    points = calculate_points(receipt)
    receipt_id = str(uuid4())

    receipt_points[receipt_id] = points
    return {"id": receipt_id}


@app.get("/receipts/{id}/points")
async def read_points(id: str):
    if id not in receipt_points:
        raise HTTPException(status_code=404, detail="No receipt found for that id")
    return {"points": receipt_points[id]}
