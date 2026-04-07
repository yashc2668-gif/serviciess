"""
Data Filtering Utilities for RBAC
Filters query results based on user permissions and ownership
"""

from typing import Any, Dict, List, Optional, Type, Union
from sqlalchemy.orm import Query, Session
from sqlalchemy import and_, or_, func

from app.models.user import User
from app.models.project import Project
from app.models.company import Company
from app.models.material import Material
from app.models.material_requisition import MaterialRequisition
from app.models.labour_attendance import LabourAttendance
from app.models.ra_bill import RABill
from app.models.payment import Payment
from app.core.rbac_middleware import AccessLevel, normalize_role


class DataFilterEngine:
    """
    Enterprise Data Filter Engine
    
    Automatically filters database queries based on user role and ownership.
    Ensures users can only see data they're authorized to access.
    """
    
    def __init__(self, db: Session, current_user: User):
        self.db = db
        self.user = current_user
        self.role = normalize_role(current_user.role)
        self.access_level = self._determine_user_access_level()
    
    def _determine_user_access_level(self) -> AccessLevel:
        """Determine the user's data access level"""
        if self.role == "admin":
            return AccessLevel.ALL
        elif self.role == "accountant":
            return AccessLevel.COMPANY
        elif self.role == "project_manager":
            return AccessLevel.COMPANY
        elif self.role == "engineer":
            return AccessLevel.TEAM
        elif self.role == "contractor":
            return AccessLevel.OWN
        else:  # viewer
            return AccessLevel.ALL  # Viewers can see all but read-only
    
    def filter_projects(self, query: Query) -> Query:
        """Filter projects based on user access"""
        if self.access_level == AccessLevel.ALL:
            return query
        
        if self.access_level == AccessLevel.COMPANY:
            # Company-level access
            if self.user.company_id:
                return query.filter(Project.company_id == self.user.company_id)
        
        elif self.access_level == AccessLevel.TEAM:
            # Team/assigned projects only
            # TODO: Implement project team assignment check
            # For now, filter by company
            if self.user.company_id:
                return query.filter(Project.company_id == self.user.company_id)
        
        elif self.access_level == AccessLevel.OWN:
            # Contractor - only see projects they have contracts for
            # This would need contract association
            return query.filter(Project.created_by == self.user.id)
        
        return query
    
    def filter_companies(self, query: Query) -> Query:
        """Filter companies based on user access"""
        if self.access_level == AccessLevel.ALL:
            return query
        
        # Most users can only see their own company
        if self.user.company_id:
            return query.filter(Company.id == self.user.company_id)
        
        return query
    
    def filter_materials(self, query: Query) -> Query:
        """Filter materials based on user access"""
        if self.access_level == AccessLevel.ALL:
            return query
        
        if self.access_level == AccessLevel.COMPANY:
            if self.user.company_id:
                return query.filter(
                    or_(
                        Material.company_id == self.user.company_id,
                        Material.company_id.is_(None)
                    )
                )
        
        elif self.access_level == AccessLevel.TEAM:
            # Engineers see materials for their assigned projects
            # TODO: Add project assignment filter
            if self.user.company_id:
                return query.filter(
                    or_(
                        Material.company_id == self.user.company_id,
                        Material.company_id.is_(None)
                    )
                )
        
        elif self.access_level == AccessLevel.OWN:
            return query.filter(Material.created_by == self.user.id)
        
        return query
    
    def filter_requisitions(self, query: Query) -> Query:
        """Filter material requisitions based on user access"""
        if self.access_level == AccessLevel.ALL:
            return query
        
        if self.access_level == AccessLevel.COMPANY:
            # PMs and Accountants see all company requisitions
            return query.join(Project).filter(
                Project.company_id == self.user.company_id
            )
        
        elif self.access_level == AccessLevel.TEAM:
            # Engineers see requisitions for their projects
            return query.join(Project).filter(
                Project.company_id == self.user.company_id
            )
        
        elif self.access_level == AccessLevel.OWN:
            # Contractors see only their own requisitions
            return query.filter(MaterialRequisition.requested_by == self.user.id)
        
        return query
    
    def filter_labour_attendance(self, query: Query) -> Query:
        """Filter labour attendance based on user access"""
        if self.access_level == AccessLevel.ALL:
            return query
        
        if self.access_level == AccessLevel.COMPANY:
            return query.join(Project).filter(
                Project.company_id == self.user.company_id
            )
        
        elif self.access_level == AccessLevel.TEAM:
            # Engineers see attendance for their sites/projects
            return query.join(Project).filter(
                Project.company_id == self.user.company_id
            )
        
        elif self.access_level == AccessLevel.OWN:
            # Contractors see only their team's attendance
            # TODO: Filter by contractor association
            return query.filter(LabourAttendance.marked_by == self.user.id)
        
        return query
    
    def filter_ra_bills(self, query: Query) -> Query:
        """Filter RA bills based on user access"""
        if self.access_level == AccessLevel.ALL:
            return query
        
        if self.access_level == AccessLevel.COMPANY:
            # Accountants and PMs see all company RA bills
            return query.join(Project).filter(
                Project.company_id == self.user.company_id
            )
        
        elif self.access_level == AccessLevel.OWN:
            # Contractors see only their RA bills
            # TODO: Filter by contractor association through contract
            return query.filter(RABill.created_by == self.user.id)
        
        return query
    
    def filter_payments(self, query: Query) -> Query:
        """Filter payments based on user access"""
        if self.access_level == AccessLevel.ALL:
            return query
        
        if self.access_level == AccessLevel.COMPANY:
            # Accountants see all company payments
            return query.join(Project).filter(
                Project.company_id == self.user.company_id
            )
        
        elif self.role == "contractor":
            # Contractors see only payments related to their bills
            # TODO: Implement through RA bill association
            return query.filter(Payment.created_by == self.user.id)
        
        # Engineers don't see payments
        elif self.role == "engineer":
            return query.filter(False)  # Empty result
        
        return query
    
    def apply_filter(self, model_class: Type, query: Query) -> Query:
        """Apply appropriate filter based on model class"""
        filter_map = {
            "Project": self.filter_projects,
            "Company": self.filter_companies,
            "Material": self.filter_materials,
            "MaterialRequisition": self.filter_requisitions,
            "LabourAttendance": self.filter_labour_attendance,
            "RABill": self.filter_ra_bills,
            "Payment": self.filter_payments,
        }
        
        model_name = model_class.__name__
        filter_func = filter_map.get(model_name)
        
        if filter_func:
            return filter_func(query)
        
        return query


class FieldMaskEngine:
    """
    Field-level Data Masking Engine
    
    Masks sensitive fields based on user role before returning data.
    """
    
    # Field masking rules: role -> resource -> fields to mask
    MASK_RULES = {
        "contractor": {
            "company": ["gst_number", "pan_number", "phone", "email", "address"],
            "vendor": ["gst_number", "pan_number", "bank_details"],
            "payment": ["bank_account", "ifsc_code", "payment_notes", "internal_remarks"],
            "contract": ["profit_margin", "cost_breakdown"],
        },
        "viewer": {
            "company": ["gst_number", "pan_number", "phone", "email"],
            "vendor": ["gst_number", "pan_number", "bank_details"],
            "payment": ["bank_account", "ifsc_code", "payment_notes"],
            "user": ["email", "phone"],
        },
        "engineer": {
            "payment": ["bank_account", "ifsc_code", "payment_notes"],
            "contract": ["profit_margin", "vendor_rate"],
        },
    }
    
    MASK_VALUE = "***MASKED***"
    
    def __init__(self, user_role: str):
        self.role = normalize_role(user_role)
    
    def mask_fields(
        self, 
        data: Dict[str, Any], 
        resource_type: str
    ) -> Dict[str, Any]:
        """Apply field masking to data dictionary"""
        role_rules = self.MASK_RULES.get(self.role, {})
        fields_to_mask = role_rules.get(resource_type, [])
        
        if not fields_to_mask:
            return data
        
        masked_data = data.copy()
        for field in fields_to_mask:
            if field in masked_data:
                masked_data[field] = self.MASK_VALUE
        
        return masked_data
    
    def mask_fields_in_list(
        self,
        items: List[Dict[str, Any]],
        resource_type: str
    ) -> List[Dict[str, Any]]:
        """Apply field masking to a list of items"""
        return [self.mask_fields(item, resource_type) for item in items]
    
    def get_visible_fields(self, resource_type: str) -> List[str]:
        """Get list of fields that should be visible for this role"""
        # This would typically come from a schema definition
        # For now, return all except masked
        role_rules = self.MASK_RULES.get(self.role, {})
        return role_rules.get(resource_type, [])


class QueryOptimizer:
    """
    Query Optimization for RBAC
    
    Adds efficient filtering at the database level
    """
    
    @staticmethod
    def add_company_filter(query: Query, user: User, model_class: Type) -> Query:
        """Add company filter to query if applicable"""
        if user.company_id and hasattr(model_class, 'company_id'):
            return query.filter(
                or_(
                    model_class.company_id == user.company_id,
                    model_class.company_id.is_(None)
                )
            )
        return query
    
    @staticmethod
    def add_created_by_filter(query: Query, user: User, model_class: Type) -> Query:
        """Add created_by filter for ownership-based access"""
        if hasattr(model_class, 'created_by'):
            return query.filter(model_class.created_by == user.id)
        return query
    
    @staticmethod
    def optimize_for_role(
        query: Query, 
        user: User, 
        model_class: Type
    ) -> Query:
        """Apply all relevant optimizations based on role"""
        role = normalize_role(user.role)
        
        if role == "admin":
            return query
        
        if role in ["project_manager", "accountant"]:
            return QueryOptimizer.add_company_filter(query, user, model_class)
        
        if role == "contractor":
            return QueryOptimizer.add_created_by_filter(query, user, model_class)
        
        if role == "engineer":
            # Engineers see company data plus team assignments
            return QueryOptimizer.add_company_filter(query, user, model_class)
        
        return query


def get_filtered_query(
    db: Session,
    user: User,
    model_class: Type,
    base_query: Optional[Query] = None
) -> Query:
    """
    Convenience function to get filtered query
    
    Usage:
        query = get_filtered_query(db, current_user, Project)
        projects = query.all()
    """
    if base_query is None:
        base_query = db.query(model_class)
    
    filter_engine = DataFilterEngine(db, user)
    return filter_engine.apply_filter(model_class, base_query)


def mask_sensitive_data(
    user_role: str,
    data: Union[Dict, List[Dict]],
    resource_type: str
) -> Union[Dict, List[Dict]]:
    """
    Convenience function to mask sensitive fields
    
    Usage:
        safe_data = mask_sensitive_data(
            current_user.role,
            company_data,
            "company"
        )
    """
    mask_engine = FieldMaskEngine(user_role)
    
    if isinstance(data, list):
        return mask_engine.mask_fields_in_list(data, resource_type)
    else:
        return mask_engine.mask_fields(data, resource_type)
