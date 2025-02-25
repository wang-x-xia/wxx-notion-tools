from datetime import date

from pydantic import BaseModel


class Buy(BaseModel):
    """
    Buy operation
    """
    id: str
    date: date
    quantity: float
    price: float
    fee: float
