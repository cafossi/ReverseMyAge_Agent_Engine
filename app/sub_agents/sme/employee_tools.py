"""
Employee Data Query Tools for Amanda SME Agent
Provides structured data queries from APEX_Dim employee dimension table
"""

from __future__ import annotations
import logging
from typing import Dict, List, Optional
from datetime import datetime

from google.cloud import bigquery
from google.adk.tools.tool_context import ToolContext

from .config import PROJECT_ID

logger = logging.getLogger("employee_tools")

# Employee dimension table
EMPLOYEE_TABLE = f"{PROJECT_ID}.APEX_Performance_DataMart.APEX_Dim"

# Cache for BigQuery client
_bq_client: bigquery.Client | None = None


def _get_bq_client() -> bigquery.Client:
    """Get or create BigQuery client."""
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client(project=PROJECT_ID)
        logger.info(f"BigQuery client initialized for employee queries")
    return _bq_client


# ---------- Employee Query Tools ----------

def get_employee_info(
    employee_id: Optional[int] = None,
    employee_name: Optional[str] = None,
    state: Optional[str] = None,
    region: Optional[str] = None,
    job_classification: Optional[str] = None,
    employee_status: Optional[str] = "Active",
    limit: int = 100,
    tool_context: Optional[ToolContext] = None
) -> dict:
    """
    Query employee information with flexible filters.
    
    Args:
        employee_id: Specific employee ID
        employee_name: Employee name (partial match supported)
        state: Filter by state (e.g., 'CA', 'TX')
        region: Filter by region
        job_classification: Filter by job classification
        employee_status: Filter by status (default: 'Active')
        limit: Maximum results to return (default: 100)
    
    Returns:
        Dict with employee data including management hierarchy
    
    Examples:
        - get_employee_info(employee_id=12345)
        - get_employee_info(state="CA", limit=50)
        - get_employee_info(employee_name="John Smith")
    """
    try:
        client = _get_bq_client()
        
        # Build WHERE conditions
        conditions = []
        params = []
        
        if employee_id:
            conditions.append("employee_id = @employee_id")
            params.append(bigquery.ScalarQueryParameter("employee_id", "INT64", employee_id))
        
        if employee_name:
            conditions.append("LOWER(employee_name) LIKE @employee_name")
            params.append(bigquery.ScalarQueryParameter("employee_name", "STRING", f"%{employee_name.lower()}%"))
        
        if state:
            conditions.append("employee_state = @state")
            params.append(bigquery.ScalarQueryParameter("state", "STRING", state.upper()))
        
        if region:
            conditions.append("employee_region = @region")
            params.append(bigquery.ScalarQueryParameter("region", "STRING", region))
        
        if job_classification:
            conditions.append("job_classification = @job_classification")
            params.append(bigquery.ScalarQueryParameter("job_classification", "STRING", job_classification))
        
        if employee_status:
            conditions.append("employee_status = @status")
            params.append(bigquery.ScalarQueryParameter("status", "STRING", employee_status))
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        sql = f"""
        SELECT 
            employee_id,
            employee_name,
            job_classification,
            pay_type,
            employee_region,
            employee_state,
            employee_city,
            employee_zip_code,
            employee_status,
            employee_date_started,
            last_day_paid,
            onboarding_manager,
            performance_manager,
            recruiter,
            regional_director,
            site_manager,
            workforce_admin
        FROM `{EMPLOYEE_TABLE}`
        WHERE {where_clause}
        ORDER BY employee_name
        LIMIT @limit
        """
        
        params.append(bigquery.ScalarQueryParameter("limit", "INT64", limit))
        
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        results = client.query(sql, job_config=job_config).result()
        
        employees = []
        for row in results:
            employees.append({
                "employee_id": row.employee_id,
                "employee_name": row.employee_name,
                "job_classification": row.job_classification,
                "pay_type": row.pay_type,
                "location": {
                    "region": row.employee_region,
                    "state": row.employee_state,
                    "city": row.employee_city,
                    "zip_code": row.employee_zip_code
                },
                "status": row.employee_status,
                "dates": {
                    "date_started": str(row.employee_date_started) if row.employee_date_started else None,
                    "last_day_paid": str(row.last_day_paid) if row.last_day_paid else None
                },
                "management": {
                    "onboarding_manager": row.onboarding_manager,
                    "performance_manager": row.performance_manager,
                    "site_manager": row.site_manager,
                    "regional_director": row.regional_director,
                    "workforce_admin": row.workforce_admin,
                    "recruiter": row.recruiter
                }
            })
        
        return {
            "status": "success",
            "employees": employees,
            "count": len(employees),
            "source": "APEX_Dim employee table"
        }
        
    except Exception as e:
        logger.error(f"Error querying employee info: {e}")
        return {
            "status": "error",
            "message": str(e),
            "employees": []
        }


def get_employee_count(
    state: Optional[str] = None,
    region: Optional[str] = None,
    city: Optional[str] = None,
    job_classification: Optional[str] = None,
    employee_status: Optional[str] = "Active",
    group_by: Optional[str] = None,
    tool_context: Optional[ToolContext] = None
) -> dict:
    """
    Get employee counts with optional grouping.
    
    Args:
        state: Filter by state
        region: Filter by region
        city: Filter by city
        job_classification: Filter by job classification
        employee_status: Filter by status (default: 'Active')
        group_by: Group results by field ('state', 'region', 'city', 'job_classification')
    
    Returns:
        Dict with count data
    
    Examples:
        - get_employee_count(state="CA")
        - get_employee_count(group_by="state")
        - get_employee_count(region="West", group_by="city")
    """
    try:
        client = _get_bq_client()
        
        # Build WHERE conditions
        conditions = []
        params = []
        
        if state:
            conditions.append("employee_state = @state")
            params.append(bigquery.ScalarQueryParameter("state", "STRING", state.upper()))
        
        if region:
            conditions.append("employee_region = @region")
            params.append(bigquery.ScalarQueryParameter("region", "STRING", region))
        
        if city:
            conditions.append("employee_city = @city")
            params.append(bigquery.ScalarQueryParameter("city", "STRING", city))
        
        if job_classification:
            conditions.append("job_classification = @job_classification")
            params.append(bigquery.ScalarQueryParameter("job_classification", "STRING", job_classification))
        
        if employee_status:
            conditions.append("employee_status = @status")
            params.append(bigquery.ScalarQueryParameter("status", "STRING", employee_status))
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Build GROUP BY clause
        if group_by:
            group_by_field = {
                'state': 'employee_state',
                'region': 'employee_region',
                'city': 'employee_city',
                'job_classification': 'job_classification',
                'pay_type': 'pay_type'
            }.get(group_by.lower(), 'employee_state')
            
            sql = f"""
            SELECT 
                {group_by_field} as category,
                COUNT(*) as employee_count
            FROM `{EMPLOYEE_TABLE}`
            WHERE {where_clause}
            GROUP BY {group_by_field}
            ORDER BY employee_count DESC
            """
        else:
            sql = f"""
            SELECT COUNT(*) as employee_count
            FROM `{EMPLOYEE_TABLE}`
            WHERE {where_clause}
            """
        
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        results = client.query(sql, job_config=job_config).result()
        
        if group_by:
            data = [{"category": row.category, "count": row.employee_count} for row in results]
            return {
                "status": "success",
                "grouped_by": group_by,
                "data": data,
                "total_categories": len(data)
            }
        else:
            count = list(results)[0].employee_count
            return {
                "status": "success",
                "employee_count": count,
                "filters_applied": {
                    "state": state,
                    "region": region,
                    "city": city,
                    "job_classification": job_classification,
                    "employee_status": employee_status
                }
            }
        
    except Exception as e:
        logger.error(f"Error getting employee count: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


def get_management_hierarchy(
    manager_name: Optional[str] = None,
    manager_type: str = "performance_manager",
    tool_context: Optional[ToolContext] = None
) -> dict:
    """
    Get employees under a specific manager or list all managers.
    
    Args:
        manager_name: Name of the manager (partial match supported)
        manager_type: Type of manager relationship to query:
            - 'performance_manager' (default)
            - 'site_manager'
            - 'regional_director'
            - 'onboarding_manager'
            - 'workforce_admin'
    
    Returns:
        Dict with manager and their direct reports
    
    Examples:
        - get_management_hierarchy(manager_name="Jane Doe")
        - get_management_hierarchy(manager_type="site_manager")
    """
    try:
        client = _get_bq_client()
        
        # Validate manager_type
        valid_types = [
            'performance_manager', 'site_manager', 'regional_director',
            'onboarding_manager', 'workforce_admin', 'recruiter'
        ]
        if manager_type not in valid_types:
            return {
                "status": "error",
                "message": f"Invalid manager_type. Must be one of: {', '.join(valid_types)}"
            }
        
        if manager_name:
            # Get specific manager's reports
            sql = f"""
            SELECT 
                {manager_type} as manager_name,
                COUNT(*) as report_count,
                STRING_AGG(employee_name, ', ' ORDER BY employee_name) as direct_reports
            FROM `{EMPLOYEE_TABLE}`
            WHERE LOWER({manager_type}) LIKE @manager_name
                AND employee_status = 'Active'
            GROUP BY {manager_type}
            """
            
            params = [bigquery.ScalarQueryParameter("manager_name", "STRING", f"%{manager_name.lower()}%")]
            
        else:
            # List all managers with their report counts
            sql = f"""
            SELECT 
                {manager_type} as manager_name,
                COUNT(*) as report_count
            FROM `{EMPLOYEE_TABLE}`
            WHERE {manager_type} IS NOT NULL
                AND employee_status = 'Active'
            GROUP BY {manager_type}
            ORDER BY report_count DESC
            """
            params = []
        
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        results = client.query(sql, job_config=job_config).result()
        
        managers = []
        for row in results:
            manager_data = {
                "manager_name": row.manager_name,
                "report_count": row.report_count
            }
            if manager_name and hasattr(row, 'direct_reports'):
                manager_data["direct_reports"] = row.direct_reports.split(', ') if row.direct_reports else []
            
            managers.append(manager_data)
        
        return {
            "status": "success",
            "manager_type": manager_type,
            "managers": managers,
            "count": len(managers)
        }
        
    except Exception as e:
        logger.error(f"Error getting management hierarchy: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


def list_unique_values(
    field: str,
    employee_status: str = "Active",
    tool_context: Optional[ToolContext] = None
) -> dict:
    """
    List unique values for a specific field (useful for exploring data).
    
    Args:
        field: Field to get unique values for:
            - 'state' / 'employee_state'
            - 'region' / 'employee_region'
            - 'city' / 'employee_city'
            - 'job_classification'
            - 'pay_type'
        employee_status: Filter by status (default: 'Active')
    
    Returns:
        Dict with list of unique values
    
    Examples:
        - list_unique_values("state")
        - list_unique_values("job_classification")
    """
    try:
        client = _get_bq_client()
        
        # Map friendly names to actual column names
        field_mapping = {
            'state': 'employee_state',
            'region': 'employee_region',
            'city': 'employee_city',
            'job_classification': 'job_classification',
            'pay_type': 'pay_type',
            'status': 'employee_status'
        }
        
        db_field = field_mapping.get(field.lower(), field)
        
        sql = f"""
        SELECT DISTINCT {db_field} as value, COUNT(*) as count
        FROM `{EMPLOYEE_TABLE}`
        WHERE employee_status = @status
            AND {db_field} IS NOT NULL
        GROUP BY {db_field}
        ORDER BY count DESC
        """
        
        params = [bigquery.ScalarQueryParameter("status", "STRING", employee_status)]
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        results = client.query(sql, job_config=job_config).result()
        
        values = [{"value": row.value, "count": row.count} for row in results]
        
        return {
            "status": "success",
            "field": field,
            "values": values,
            "total_unique": len(values)
        }
        
    except Exception as e:
        logger.error(f"Error listing unique values: {e}")
        return {
            "status": "error",
            "message": str(e)
        }