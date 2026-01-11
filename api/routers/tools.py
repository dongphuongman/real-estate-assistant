from fastapi import APIRouter, HTTPException, status
from typing import List
from pydantic import BaseModel

from tools.property_tools import (
    MortgageCalculatorTool, 
    MortgageInput, 
    MortgageResult,
    create_property_tools
)

router = APIRouter()

class ToolInfo(BaseModel):
    """Information about an available tool."""
    name: str
    description: str

@router.get("/tools", response_model=List[ToolInfo], tags=["Tools"])
async def list_tools():
    """List available tools."""
    tools = create_property_tools()
    return [
        ToolInfo(name=tool.name, description=tool.description)
        for tool in tools
    ]

@router.post("/tools/mortgage-calculator", response_model=MortgageResult, tags=["Tools"])
async def calculate_mortgage(input_data: MortgageInput):
    """
    Calculate mortgage payments.
    """
    try:
        return MortgageCalculatorTool.calculate(
            property_price=input_data.property_price,
            down_payment_percent=input_data.down_payment_percent,
            interest_rate=input_data.interest_rate,
            loan_years=input_data.loan_years
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation failed: {str(e)}"
        )
