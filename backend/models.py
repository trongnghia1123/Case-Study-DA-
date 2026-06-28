from pydantic import BaseModel
from typing import Optional

# ── KPI Summary ──────────────────────────────────────────
class SummaryResponse(BaseModel):
    total_defects: int
    total_repair_cost: float
    avg_repair_cost: float
    defect_rate_pct: float          # defects / tổng monthly_output * 100
    most_defective_line: str
    most_common_severity: str
    most_common_location: str
    date_range_start: str
    date_range_end: str

# ── Trend ─────────────────────────────────────────────────
class MonthlyTrend(BaseModel):
    month: int
    month_name: str
    defect_count: int
    mom_change_pct: Optional[float]  # month-over-month % change
    is_anomaly: bool

class TrendResponse(BaseModel):
    data: list[MonthlyTrend]
    overall_trend: str               # "increasing" | "decreasing" | "stable"

# ── Defects by Line ───────────────────────────────────────
class LineStats(BaseModel):
    production_line: str
    defect_count: int
    total_repair_cost: float
    avg_repair_cost: float
    defect_rate_pct: float
    top_defect_type: str

# ── Defects by Product ────────────────────────────────────
class ProductStats(BaseModel):
    product_id: int
    product_name: str
    category: str
    production_line: str
    defect_count: int
    total_repair_cost: float
    avg_repair_cost: float

# ── Location × Severity ───────────────────────────────────
class LocationSeverityCell(BaseModel):
    defect_location: str
    severity: str
    count: int

class LocationSeverityResponse(BaseModel):
    data: list[LocationSeverityCell]
    chi2: float
    p_value: float
    is_significant: bool             # p < 0.05

# ── Repair Cost ───────────────────────────────────────────
class CostBreakdown(BaseModel):
    group: str                       # tên line / category / severity
    total_cost: float
    avg_cost: float
    defect_count: int

# ── Anomaly ───────────────────────────────────────────────
class AnomalyMonth(BaseModel):
    month: int
    month_name: str
    defect_count: int
    z_score: float
    is_anomaly: bool