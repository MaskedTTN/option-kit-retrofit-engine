"""
BMW Retrofit Comparison Service
Main API application
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
import requests

app = FastAPI(
    title="BMW Retrofit Comparison Service",
    description="Compares vehicle configurations and generates retrofit BOMs",
    version="0.1.0"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Models
# ============================================================================

class PartCategory(str, Enum):
    """Part categories for classification"""
    WIRING = "wiring"
    CONTROL_MODULE = "control_module"
    TRIM = "trim"
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    HARDWARE = "hardware"
    OTHER = "other"


class Part(BaseModel):
    """Individual part information"""
    part_number: str = Field(..., description="BMW part number")
    description: str = Field(..., description="Part description")
    quantity: int = Field(default=1, ge=1, description="Quantity needed")
    category: Optional[PartCategory] = Field(None, description="Part category")
    superseded_by: Optional[str] = Field(None, description="Superseded part number if applicable")
    notes: Optional[str] = Field(None, description="Additional notes")

class Part(BaseModel):
    id: int
    position: str
    description: str
    part_number: str
    quantity: str
    supplement: str
    from_date: str
    up_to_date: str
    price: str
    notes: str
    option_requirements: Optional[str]
    option_codes: Optional[str]


class RetrofitComparisonRequest(BaseModel):
    """Request model for retrofit comparison"""
    VID: str = Field(..., description="Vehicle identification string")
    current_vo_codes: List[str] = Field(..., description="Current vehicle option codes")
    target_vo_codes: List[str] = Field(..., description="Target vehicle option codes after retrofit")


class RetrofitBOM(BaseModel):
    """Bill of Materials for a retrofit"""
    parts_to_add: List[Part] = Field(default_factory=list, description="Parts that need to be added")
    parts_to_remove: List[Part] = Field(default_factory=list, description="Parts that need to be removed")
    total_parts_count: int = Field(..., description="Total number of parts needed")
    estimated_complexity: str = Field(..., description="Estimated complexity: simple, moderate, complex")


class RetrofitComparisonResponse(BaseModel):
    """Response model for retrofit comparison"""
    added_options: List[str] = Field(..., description="Option codes being added")
    removed_options: List[str] = Field(..., description="Option codes being removed")
    bom: RetrofitBOM = Field(..., description="Bill of materials")


# ============================================================================
# Service Layer
# ============================================================================

class RetrofitService:
    """Business logic for retrofit comparison"""
    
    def __init__(self, parts_service_url: Optional[str] = None):
        """
        Initialize the retrofit service
        
        Args:
            parts_service_url: URL of the parts service API (if using microservice)
                             If None, will use direct database access
        """
        self.parts_service_url = parts_service_url
    
    def _getCarParts(self, VID, option_codes):
        """
        Get parts for a vehicle based on VID and option codes
        
        Args:
            VID: Vehicle identification string
            option_codes: List of option codes to query
            
        Returns:
            JSON response with parts data
        """
        # Build proper JSON payload
        data = {
            "vid": VID,
            "order_codes": [
                {"code": code, "description": ""}  # Add description if you have it
                for code in option_codes
            ]
        }
        
        print(f"Requesting parts for VID {VID} with options: {option_codes}")
        
        try:
            response = requests.get(
                f"{self.parts_service_url}/vehicles/{VID}/complete",
                json=data  # If you need to send data as query params
                # OR use: json=data  # If you need to send as JSON body (but GET usually doesn't have body)
            )
            response.raise_for_status()  # Raise exception for bad status codes
            
            #print(f"Received response: {response.status_code}")
            result = response.json()
            #print(f"Response content: {result}")
            return result
            
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error: Unable to reach {self.parts_service_url}")
            raise
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error: {response.status_code} - {response.text}")
            raise
        except requests.exceptions.JSONDecodeError as e:
            print(f"Invalid JSON response: {response.text}")
            raise
    
    def calculate_option_delta(
        self, 
        current_codes: List[str], 
        target_codes: List[str]
    ) -> tuple[List[str], List[str]]:
        """
        Calculate which options are being added and removed
        
        Args:
            current_codes: Current vehicle option codes
            target_codes: Target vehicle option codes
            
        Returns:
            Tuple of (added_options, removed_options)
        """
        current_set = set(current_codes)
        target_set = set(target_codes)
        
        added = list(target_set - current_set)
        removed = list(current_set - target_set)
        
        return added, removed
    
    async def get_parts_for_option(self, option_code: str) -> List[Part]:
        """
        Get all parts associated with an option code
        
        This is where you'd call your Parts Service or query the database directly
        For now, returns mock data for the PoC
        
        Args:
            option_code: BMW option code (e.g., "SA456")
            
        Returns:
            List of parts needed for this option
        """
        # Example: response = await http_client.get(f"{self.parts_service_url}/parts/by-option/{option_code}")
        
        # Mock data for demonstration
        mock_parts = {
            "SA456": [
                Part(
                    part_number="61319200316",
                    description="Wiring harness, door",
                    quantity=1,
                    category=PartCategory.WIRING
                ),
                Part(
                    part_number="61359200317",
                    description="Control module, comfort access",
                    quantity=1,
                    category=PartCategory.CONTROL_MODULE
                )
            ],
            "SA302": [
                Part(
                    part_number="51167891234",
                    description="M Sport steering wheel",
                    quantity=1,
                    category=PartCategory.TRIM
                )
            ]
        }
        
        return mock_parts.get(option_code, [])
    
    def estimate_complexity(self, bom: RetrofitBOM) -> str:
        """
        Estimate the complexity of the retrofit based on BOM
        Args:
            bom: Bill of Materials
        Returns:
            Complexity level as a string
        part_count = bom.total_parts_count
        if part_count < 5:
            return "simple"
        elif part_count < 15:
            return "moderate"
        else:
            return "complex"""
        part_count = bom.total_parts_count
        if part_count < 5:
            return "simple"
        elif part_count < 15:
            return "moderate"
        else:
            return "complex"

    async def compare_configurations(self, VID, current_codes: List[str], target_codes: List[str]) -> RetrofitComparisonResponse:
        """
        Main comparison logic
        
        Args:
            VID: Vehicle identification string
            current_codes: Current vehicle option codes
            target_codes: Target vehicle option codes
            
        Returns:
            Complete retrofit comparison with BOM
        """
        def extract_parts(raw_data) -> List[Part]:
            parts_dict = {}  # Use dict to deduplicate by part_number
            for main_group in raw_data:
                for subgroup in main_group.get('subgroups', []):
                    for diagram in subgroup.get('diagrams', []):
                        for part in diagram.get('parts', []):
                            part_number = part.get('part_number', '')
                            # Only add if we haven't seen this part_number before
                            if part_number and part_number not in parts_dict:
                                parts_dict[part_number] = Part(
                                    id=part.get('id'),
                                    position=part.get('position', ''),
                                    description=part.get('description', ''),
                                    part_number=part_number,
                                    quantity=part.get('quantity', ''),
                                    supplement=part.get('supplement', ''),
                                    from_date=part.get('from_date', ''),
                                    up_to_date=part.get('up_to_date', ''),
                                    price=part.get('price', ''),
                                    notes=part.get('notes', ''),
                                    option_requirements=part.get('option_requirements'),
                                    option_codes=part.get('option_codes')
                                )
            return list(parts_dict.values())
        # Calculate option delta
        added_options, removed_options = self.calculate_option_delta(
            current_codes, 
            target_codes
        )
        
        # Helper function to check if a part applies to given option codes
        def part_applies_to_config(part, option_codes_set):
            """
            Check if a part should be present given the option codes.
            Parts with option_codes like "S710A=No" should NOT be present when S710A is in the config.
            Parts with option_codes like "S710A=Yes" should be present when S710A is in the config.
            """
            if not part.option_codes:
                return True  # No restrictions, part always applies
            
            # Parse the option_codes field (e.g., "S710A=No S5AGA=Yes")
            requirements = part.option_codes.strip().split()
            for req in requirements:
                if '=' not in req:
                    continue
                option, value = req.split('=', 1)
                if value.upper() == 'NO' and option in option_codes_set:
                    # Part says option should be NO, but it's present
                    return False
                if value.upper() == 'YES' and option not in option_codes_set:
                    # Part says option should be YES, but it's not present
                    return False
            return True
        
        # Fetch parts for current configuration
        current_parts_raw = self._getCarParts(VID, current_codes)
        all_current_parts = extract_parts(current_parts_raw)
        
        # Fetch parts for target configuration
        target_parts_raw = self._getCarParts(VID, target_codes)
        all_target_parts = extract_parts(target_parts_raw)
        
        # Filter parts based on option_codes field
        current_codes_set = set(current_codes)
        target_codes_set = set(target_codes)
        
        current_config_parts = [p for p in all_current_parts if part_applies_to_config(p, current_codes_set)]
        target_config_parts = [p for p in all_target_parts if part_applies_to_config(p, target_codes_set)]
        
        # Compare using part numbers
        current_part_numbers = {p.part_number for p in current_config_parts}
        target_part_numbers = {p.part_number for p in target_config_parts}
        
        parts_to_add = [p for p in target_config_parts if p.part_number not in current_part_numbers]
        parts_to_remove = [p for p in current_config_parts if p.part_number not in target_part_numbers]
        
        # Create BOM
        temp_bom = type('obj', (object,), {
            'parts_to_add': parts_to_add,
            'total_parts_count': len(parts_to_add)
        })()
        complexity = self.estimate_complexity(temp_bom)
        
        bom = RetrofitBOM(
            parts_to_add=parts_to_add,
            parts_to_remove=parts_to_remove,
            total_parts_count=len(parts_to_add),
            estimated_complexity=complexity
        )
        
        return RetrofitComparisonResponse(
            added_options=added_options,
            removed_options=removed_options,
            bom=bom
        )

    


# Initialize service
retrofit_service = RetrofitService(parts_service_url="http://localhost:8000")


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "BMW Retrofit Comparison Service",
        "status": "operational",
        "version": "0.1.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "parts_service": "connected" if retrofit_service.parts_service_url else "local"
    }


@app.post("/api/v1/compare", response_model=RetrofitComparisonResponse)
async def compare_retrofit(request: RetrofitComparisonRequest):
    """
    Compare two vehicle configurations and generate retrofit BOM
    
    Args:
        request: Comparison request with current and target VO codes
        
    Returns:
        Retrofit comparison with complete BOM
        
    Raises:
        HTTPException: If comparison fails
    """
    try:
        result = await retrofit_service.compare_configurations(
            VID=request.VID,
            current_codes=request.current_vo_codes,
            target_codes=request.target_vo_codes
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Comparison failed: {str(e)}"
        )


@app.post("/api/v1/estimate-complexity")
async def estimate_complexity(request: RetrofitComparisonRequest):
    """
    Quick complexity estimation without full BOM generation
    
    Args:
        request: Comparison request
        
    Returns:
        Complexity estimation
    """
    added, removed = retrofit_service.calculate_option_delta(
        request.current_vo_codes,
        request.target_vo_codes
    )
    
    return {
        "added_options_count": len(added),
        "removed_options_count": len(removed),
        "added_options": added,
        "removed_options": removed
    }


# ============================================================================
# Run server (for development)
# ============================================================================

""" if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002, reload=True) """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="debug"
    )