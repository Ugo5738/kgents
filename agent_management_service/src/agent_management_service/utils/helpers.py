"""
Helper functions for the agent_management_service.
"""
import json
from typing import Any, Dict, List, Optional, TypeVar, Union
from uuid import UUID

from pydantic import BaseModel


class UUIDEncoder(json.JSONEncoder):
    """JSON encoder that handles UUID objects."""

    def default(self, obj: Any) -> Any:
        """Convert UUID objects to strings."""
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


def to_camel(string: str) -> str:
    """
    Convert a snake_case string to camelCase.
    
    Example:
        >>> to_camel("snake_case")
        'snakeCase'
    """
    first, *others = string.split('_')
    return first + ''.join(word.capitalize() for word in others)


T = TypeVar('T', bound=BaseModel)

def filter_none_values(model_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove None values from a dictionary.
    Useful for creating partial update dictionaries.
    
    Args:
        model_dict: Dictionary potentially containing None values
        
    Returns:
        Dictionary with None values removed
    """
    return {k: v for k, v in model_dict.items() if v is not None}


def serialize_model_to_json(model: Union[BaseModel, List[BaseModel], Dict[str, Any]]) -> str:
    """
    Serialize a Pydantic model to JSON, handling UUID conversion.
    
    Args:
        model: Pydantic model, list of models, or dictionary
        
    Returns:
        JSON string
    """
    if isinstance(model, BaseModel):
        model_dict = model.model_dump()
    elif isinstance(model, list) and all(isinstance(m, BaseModel) for m in model):
        model_dict = [m.model_dump() for m in model]
    else:
        model_dict = model
    
    return json.dumps(model_dict, cls=UUIDEncoder)


def parse_json_to_dict(json_str: str) -> Dict[str, Any]:
    """
    Parse a JSON string to a dictionary.
    
    Args:
        json_str: JSON string
        
    Returns:
        Dictionary
    """
    if not json_str:
        return {}
        
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return {}
