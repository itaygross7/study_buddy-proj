from pydantic import BaseModel
from typing import Type

def model_to_dict(model_instance: BaseModel) -> dict:
    """
    Converts a Pydantic model instance to a dictionary.
    """
    return model_instance.dict()

def dict_to_model(data: dict, model_class: Type[BaseModel]) -> BaseModel:
    """
    Converts a dictionary to a Pydantic model instance.
    """
    return model_class(**data)
