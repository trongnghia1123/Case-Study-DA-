import pandas as pd
import requests
from functools import lru_cache
from scipy import stats
import numpy as np
from pathlib import Path

API_URL = (
    "https://raw.githubusercontent.com/phongtdt/RFID_Data-Analyst_Case-Study-Test-Jun"
    "/main/mock-api/defect_records.json"
)

# master_data.csv nằm ở thư mục cha (root repo)
MASTER_CSV = Path(__file__).parent.parent / "data" / "master_data.csv"


# ── Cache toàn bộ merged dataframe ───────────────────────────────────────────
# lru_cache giữ kết quả trong RAM, tránh gọi lại HTTP mỗi request
@lru_cache(maxsize=1)
def get_merged_df() -> pd.DataFrame:
    """Fetch defect records từ API, merge với master data. Cached sau lần đầu."""

    # 1. Fetch defect records
    resp = requests.get(API_URL, timeout=10)
    resp.raise_for_status()
    defect_df = pd.DataFrame(resp.json())

    # 2. Load master data
    master_df = pd.read_csv(MASTER_CSV)

    # 3. Parse dates & engineer features
    defect_df["defect_date"] = pd.to_datetime(defect_df["defect_date"], format="mixed", dayfirst=False)
    defect_df["month"] = defect_df["defect_date"].dt.month
    defect_df["month_name"] = defect_df["defect_date"].dt.strftime("%b")
    defect_df["year"] = defect_df["defect_date"].dt.year

    # 4. Merge
    df = defect_df.merge(master_df, on="product_id", how="left")

    #Chỉ lấy Jan–Jun 2024
    df = df[
        (df["defect_date"].dt.year == 2024) &
        (df["defect_date"].dt.month <= 6)
    ].copy()

    # 5. Defect count per product + defect rate
    counts = df.groupby("product_id").size().reset_index(name="defect_count")
    df = df.merge(counts, on="product_id", how="left")
    df["defect_rate"] = df["defect_count"] / df["monthly_output"]

    return df


def clear_cache():
    """Gọi endpoint /refresh để force reload data mới."""
    get_merged_df.cache_clear()


# ── Helper functions (mỗi hàm phục vụ 1 endpoint) ────────────────────────────

def compute_summary() -> dict:
    df = get_merged_df()
    monthly = df.groupby("month").size().reset_index(name="count")
    mean, std = monthly["count"].mean(), monthly["count"].std()

    return {
        "total_defects": len(df),
        "total_repair_cost": round(df["repair_cost"].sum(), 2),
        "avg_repair_cost": round(df["repair_cost"].mean(), 2),
        "defect_rate_pct": round(
            len(df) / df["monthly_output"].sum() * 100, 4
        ),
        "most_defective_line": df["production_line"].value_counts().idxmax(),
        "most_common_severity": df["severity"].value_counts().idxmax(),
        "most_common_location": df["defect_location"].value_counts().idxmax(),
        "date_range_start": str(df["defect_date"].min().date()),
        "date_range_end": str(df["defect_date"].max().date()),
    }


def compute_trend() -> dict:
    df = get_merged_df()

    monthly = (
        df.groupby(["month", "month_name"])
        .size()
        .reset_index(name="defect_count")
        .sort_values("month")
    )

    # Month-over-month % change
    monthly["mom_change_pct"] = monthly["defect_count"].pct_change() * 100

    # Anomaly: |z-score| > 1.5
    mean = monthly["defect_count"].mean()
    std = monthly["defect_count"].std()
    monthly["z_score"] = (monthly["defect_count"] - mean) / std
    monthly["is_anomaly"] = monthly["z_score"].abs() > 1.5

    # Overall trend bằng linear regression slope
    slope, _, _, _, _ = stats.linregress(
        monthly["month"], monthly["defect_count"]
    )
    if slope > 5:
        overall_trend = "increasing"
    elif slope < -5:
        overall_trend = "decreasing"
    else:
        overall_trend = "stable"

    records = []
    for _, row in monthly.iterrows():
        records.append({
            "month": int(row["month"]),
            "month_name": row["month_name"],
            "defect_count": int(row["defect_count"]),
            "mom_change_pct": round(row["mom_change_pct"], 2)
                              if pd.notna(row["mom_change_pct"]) else None,
            "is_anomaly": bool(row["is_anomaly"]),
        })

    return {"data": records, "overall_trend": overall_trend}


def compute_by_line() -> list[dict]:
    df = get_merged_df()

    # Total monthly_output per line (unique per product)
    output_per_line = (
        df[["production_line", "product_id", "monthly_output"]]
        .drop_duplicates()
        .groupby("production_line")["monthly_output"]
        .sum()
    )

    agg = (
        df.groupby("production_line")
        .agg(
            defect_count=("defect_id", "count"),
            total_repair_cost=("repair_cost", "sum"),
            avg_repair_cost=("repair_cost", "mean"),
        )
        .reset_index()
    )

    # Top defect type per line
    top_type = (
        df.groupby(["production_line", "defect_type"])
        .size()
        .reset_index(name="cnt")
        .sort_values("cnt", ascending=False)
        .groupby("production_line")
        .first()["defect_type"]
    )

    agg["defect_rate_pct"] = (
        agg["defect_count"] / agg["production_line"].map(output_per_line) * 100
    ).round(4)
    agg["top_defect_type"] = agg["production_line"].map(top_type)
    agg["total_repair_cost"] = agg["total_repair_cost"].round(2)
    agg["avg_repair_cost"] = agg["avg_repair_cost"].round(2)

    return agg.to_dict(orient="records")


def compute_by_product(top_n: int = 20) -> list[dict]:
    df = get_merged_df()

    agg = (
        df.groupby(["product_id", "product_name", "category", "production_line"])
        .agg(
            defect_count=("defect_id", "count"),
            total_repair_cost=("repair_cost", "sum"),
            avg_repair_cost=("repair_cost", "mean"),
        )
        .reset_index()
        .sort_values("defect_count", ascending=False)
        .head(top_n)
    )

    agg["total_repair_cost"] = agg["total_repair_cost"].round(2)
    agg["avg_repair_cost"] = agg["avg_repair_cost"].round(2)

    return agg.to_dict(orient="records")


def compute_location_severity() -> dict:
    df = get_merged_df()

    # Crosstab → chi-square test
    ct = pd.crosstab(df["defect_location"], df["severity"])
    chi2, p_value, _, _ = stats.chi2_contingency(ct)

    # Flatten cho frontend
    records = []
    for location in ct.index:
        for severity in ct.columns:
            records.append({
                "defect_location": location,
                "severity": severity,
                "count": int(ct.loc[location, severity]),
            })

    return {
        "data": records,
        "chi2": round(chi2, 4),
        "p_value": round(p_value, 6),
        "is_significant": bool(p_value < 0.05),
    }


def compute_cost_breakdown(group_by: str = "production_line") -> list[dict]:
    """group_by: 'production_line' | 'category' | 'severity' | 'defect_type'"""
    df = get_merged_df()

    valid_cols = {"production_line", "category", "severity", "defect_type"}
    if group_by not in valid_cols:
        group_by = "production_line"

    agg = (
        df.groupby(group_by)
        .agg(
            total_cost=("repair_cost", "sum"),
            avg_cost=("repair_cost", "mean"),
            defect_count=("defect_id", "count"),
        )
        .reset_index()
        .rename(columns={group_by: "group"})
        .sort_values("total_cost", ascending=False)
    )

    agg["total_cost"] = agg["total_cost"].round(2)
    agg["avg_cost"] = agg["avg_cost"].round(2)

    return agg.to_dict(orient="records")


def compute_anomalies() -> list[dict]:
    df = get_merged_df()

    monthly = (
        df.groupby(["month", "month_name"])
        .size()
        .reset_index(name="defect_count")
        .sort_values("month")
    )

    mean = monthly["defect_count"].mean()
    std = monthly["defect_count"].std()
    monthly["z_score"] = (monthly["defect_count"] - mean) / std
    monthly["is_anomaly"] = monthly["z_score"].abs() > 1.5

    return monthly.to_dict(orient="records")