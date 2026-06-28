from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io

from models import (
    SummaryResponse, TrendResponse, LineStats,
    ProductStats, LocationSeverityResponse,
    CostBreakdown, AnomalyMonth,
)
import data as dl

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="RFID Defect Analytics API",
    description="Backend API cho Production Quality Dashboard",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # production: thay bằng domain Streamlit cụ thể
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "RFID Defect Analytics API is running"}


# ── Refresh cache ─────────────────────────────────────────────────────────────
@app.post("/refresh", tags=["Admin"])
def refresh_data():
    """Force reload data từ API và master CSV."""
    dl.clear_cache()
    return {"status": "cache cleared", "message": "Data will reload on next request"}


# ── KPI Summary ───────────────────────────────────────────────────────────────
@app.get("/api/summary", response_model=SummaryResponse, tags=["Analytics"])
def get_summary():
    """Tổng quan KPIs: tổng defects, repair cost, defect rate, v.v."""
    try:
        return dl.compute_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Trend Jan–Jun ─────────────────────────────────────────────────────────────
@app.get("/api/trends", response_model=TrendResponse, tags=["Analytics"])
def get_trends():
    """Defect count theo tháng + MoM change + anomaly flag + overall trend."""
    try:
        return dl.compute_trend()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── By Production Line ────────────────────────────────────────────────────────
@app.get("/api/by-line", response_model=list[LineStats], tags=["Analytics"])
def get_by_line():
    """Defect count, repair cost, defect rate theo từng production line."""
    try:
        return dl.compute_by_line()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── By Product ────────────────────────────────────────────────────────────────
@app.get("/api/by-product", response_model=list[ProductStats], tags=["Analytics"])
def get_by_product(
    top_n: int = Query(default=20, ge=1, le=100, description="Số sản phẩm trả về")
):
    """Top N sản phẩm có nhiều defects nhất."""
    try:
        return dl.compute_by_product(top_n=top_n)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Location × Severity ───────────────────────────────────────────────────────
@app.get(
    "/api/location-severity",
    response_model=LocationSeverityResponse,
    tags=["Analytics"],
)
def get_location_severity():
    """Crosstab defect_location × severity + chi-square test."""
    try:
        return dl.compute_location_severity()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Repair Cost Breakdown ─────────────────────────────────────────────────────
@app.get("/api/repair-cost", response_model=list[CostBreakdown], tags=["Analytics"])
def get_repair_cost(
    group_by: str = Query(
        default="production_line",
        description="Group by: production_line | category | severity | defect_type",
    )
):
    """Repair cost breakdown theo dimension tùy chọn."""
    try:
        return dl.compute_cost_breakdown(group_by=group_by)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Anomaly Detection ─────────────────────────────────────────────────────────
@app.get("/api/anomalies", response_model=list[AnomalyMonth], tags=["Analytics"])
def get_anomalies():
    """Tháng nào có defect count bất thường (|z-score| > 1.5)."""
    try:
        return dl.compute_anomalies()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Export CSV ────────────────────────────────────────────────────────────────
@app.get("/api/export/csv", tags=["Export"])
def export_csv():
    """Download toàn bộ merged dataset dưới dạng CSV."""
    try:
        df = dl.get_merged_df()
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        stream.seek(0)
        return StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=defect_data.csv"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))