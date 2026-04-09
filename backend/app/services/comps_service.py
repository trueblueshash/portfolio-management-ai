from datetime import datetime
from uuid import UUID

import yfinance as yf
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.portfolio_metrics import MetricsCatalog, PortfolioMetrics
from app.models.public_comp import PublicComp


def _to_python(val):
    """Convert numpy types to native Python types for DB storage."""
    if val is None:
        return None
    try:
        import numpy as np
        if isinstance(val, (np.floating, np.float64)):
            return float(val)
        if isinstance(val, (np.integer, np.int64)):
            return int(val)
    except ImportError:
        pass
    return val


def refresh_comps(company_id: UUID, db: Session) -> list:
    """Pull latest financial data for all comps of a portfolio company."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise ValueError(f"Company {company_id} not found")

    comp_tickers = company.comp_tickers or {}
    if not comp_tickers:
        raise ValueError(f"No comp tickers configured for {company.name}")

    db.query(PublicComp).filter(
        PublicComp.company_id == company_id,
        PublicComp.is_latest == True,
    ).update({"is_latest": False})

    results = []

    portfolio_row = _build_portfolio_company_row(company, company_id, db)
    if portfolio_row:
        db.add(portfolio_row)
        results.append(portfolio_row)

    for comp_name, ticker in comp_tickers.items():
        if ticker:
            comp_row = _fetch_public_comp(company_id, comp_name, ticker)
        else:
            comp_row = PublicComp(
                company_id=company_id,
                comp_name=comp_name,
                ticker=None,
                is_portfolio_company=False,
                data_source="private_placeholder",
                is_latest=True,
                fetched_at=datetime.utcnow(),
            )

        if comp_row:
            db.add(comp_row)
            results.append(comp_row)

    db.commit()
    return [_serialize_comp(r) for r in results]


def _fetch_public_comp(company_id: UUID, comp_name: str, ticker: str) -> PublicComp:
    """Fetch financial data for a single public company using yfinance."""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        income_stmt = stock.income_stmt

        revenue_ttm = info.get("totalRevenue") or info.get("revenue")
        revenue_ttm_millions = revenue_ttm / 1_000_000 if revenue_ttm else None

        revenue_growth = None
        if income_stmt is not None and len(income_stmt.columns) >= 2:
            try:
                rev_current = income_stmt.loc["Total Revenue"].iloc[0] if "Total Revenue" in income_stmt.index else None
                rev_previous = income_stmt.loc["Total Revenue"].iloc[1] if "Total Revenue" in income_stmt.index else None
                if rev_current and rev_previous and rev_previous > 0:
                    revenue_growth = ((rev_current - rev_previous) / rev_previous) * 100
            except (KeyError, IndexError):
                pass

        gross_margin = info.get("grossMargins")
        gross_margin_pct = gross_margin * 100 if gross_margin else None

        operating_margin = info.get("operatingMargins")
        operating_margin_pct = operating_margin * 100 if operating_margin else None

        fcf = info.get("freeCashflow")
        fcf_margin_pct = None
        if fcf and revenue_ttm and revenue_ttm > 0:
            fcf_margin_pct = (fcf / revenue_ttm) * 100

        sm_pct = None
        rd_pct = None
        if income_stmt is not None and len(income_stmt.columns) >= 1:
            try:
                latest_rev = income_stmt.loc["Total Revenue"].iloc[0] if "Total Revenue" in income_stmt.index else None

                for sm_key in ["Selling General And Administration", "Selling And Marketing Expense"]:
                    if sm_key in income_stmt.index:
                        sm_val = income_stmt.loc[sm_key].iloc[0]
                        if sm_val and latest_rev and latest_rev > 0:
                            sm_pct = (sm_val / latest_rev) * 100
                        break

                for rd_key in ["Research And Development", "Research Development"]:
                    if rd_key in income_stmt.index:
                        rd_val = income_stmt.loc[rd_key].iloc[0]
                        if rd_val and latest_rev and latest_rev > 0:
                            rd_pct = (rd_val / latest_rev) * 100
                        break
            except (KeyError, IndexError):
                pass

        rule_of_40 = None
        if revenue_growth is not None and fcf_margin_pct is not None:
            rule_of_40 = revenue_growth + fcf_margin_pct

        employees = info.get("fullTimeEmployees")
        rev_per_employee = None
        if revenue_ttm and employees and employees > 0:
            rev_per_employee = (revenue_ttm / employees) / 1000

        currency = "USD"
        if ticker.endswith(".NS") or ticker.endswith(".BO"):
            currency = "INR"
            if revenue_ttm:
                revenue_ttm_millions = revenue_ttm / 10_000_000

        fiscal_year = info.get("mostRecentQuarter", "")

        return PublicComp(
            company_id=company_id,
            comp_name=comp_name,
            ticker=ticker,
            is_portfolio_company=False,
            revenue_ttm_millions=_to_python(round(revenue_ttm_millions, 1)) if revenue_ttm_millions else None,
            revenue_currency=currency,
            revenue_growth_pct=_to_python(round(revenue_growth, 1)) if revenue_growth else None,
            gross_margin_pct=_to_python(round(gross_margin_pct, 1)) if gross_margin_pct else None,
            operating_margin_pct=_to_python(round(operating_margin_pct, 1)) if operating_margin_pct else None,
            fcf_margin_pct=_to_python(round(fcf_margin_pct, 1)) if fcf_margin_pct else None,
            sm_pct_of_revenue=_to_python(round(sm_pct, 1)) if sm_pct else None,
            rd_pct_of_revenue=_to_python(round(rd_pct, 1)) if rd_pct else None,
            rule_of_40=_to_python(round(rule_of_40, 1)) if rule_of_40 else None,
            employees=_to_python(employees),
            revenue_per_employee_k=_to_python(round(rev_per_employee, 0)) if rev_per_employee else None,
            data_source="yfinance",
            fiscal_period=str(fiscal_year)[:10] if fiscal_year else None,
            fetched_at=datetime.utcnow(),
            is_latest=True,
            raw_data={"info_keys": list(info.keys())[:20]},
        )
    except Exception as e:
        return PublicComp(
            company_id=company_id,
            comp_name=comp_name,
            ticker=ticker,
            is_portfolio_company=False,
            data_source=f"yfinance_error: {str(e)[:100]}",
            fetched_at=datetime.utcnow(),
            is_latest=True,
        )


def _build_portfolio_company_row(company: Company, company_id: UUID, db: Session) -> PublicComp:
    """Build a comps row from the portfolio company's own MIS data."""
    latest = db.query(PortfolioMetrics).filter(
        PortfolioMetrics.company_id == company_id,
        PortfolioMetrics.is_projected == False,
    ).order_by(PortfolioMetrics.period.desc()).first()

    if not latest or not latest.metrics:
        return PublicComp(
            company_id=company_id,
            comp_name=company.name,
            is_portfolio_company=True,
            data_source="portfolio_metrics",
            fetched_at=datetime.utcnow(),
            is_latest=True,
        )

    metrics = latest.metrics
    revenue = None
    revenue_growth = None
    gross_margin = None
    currency = "USD"

    catalog = db.query(MetricsCatalog).filter(
        MetricsCatalog.company_id == company_id
    ).all()
    catalog_map = {c.raw_name: c for c in catalog}

    for raw_name, value in metrics.items():
        cat = catalog_map.get(raw_name)
        if not cat:
            continue
        display = (cat.display_name or "").lower()
        unit = (cat.unit or "").lower()
        try:
            num_val = float(str(value).replace(",", "").replace("₹", "").replace("$", ""))
        except (ValueError, TypeError):
            continue

        if "arr" in display or "revenue" in display or "exit arr" in display:
            revenue = num_val
            # Convert based on catalog unit (e.g. USD Thousands -> millions)
            if "thousand" in unit or "$k" in unit or "k" in unit:
                revenue = num_val / 1000
                currency = "USD"
            elif "mn" in unit or "million" in unit:
                currency = "USD"
            elif "cr" in unit or "inr" in unit or "₹" in unit:
                currency = "INR"
            elif "$" in unit or "usd" in unit:
                currency = "USD"
        elif "growth" in display:
            revenue_growth = num_val
        elif "gross margin" in display:
            gross_margin = num_val

    return PublicComp(
        company_id=company_id,
        comp_name=company.name,
        is_portfolio_company=True,
        revenue_ttm_millions=_to_python(revenue),
        revenue_currency=currency,
        revenue_growth_pct=_to_python(revenue_growth),
        gross_margin_pct=_to_python(gross_margin),
        data_source="portfolio_metrics",
        fiscal_period=latest.period_label,
        fetched_at=datetime.utcnow(),
        is_latest=True,
    )


def get_latest_comps(company_id: UUID, db: Session) -> list:
    """Get the latest cached comps for a company."""
    comps = db.query(PublicComp).filter(
        PublicComp.company_id == company_id,
        PublicComp.is_latest == True,
    ).order_by(PublicComp.is_portfolio_company.desc()).all()

    return [_serialize_comp(c) for c in comps]


def _serialize_comp(c: PublicComp) -> dict:
    return {
        "id": str(c.id),
        "company_id": str(c.company_id),
        "comp_name": c.comp_name,
        "ticker": c.ticker,
        "is_portfolio_company": c.is_portfolio_company,
        "revenue_ttm_millions": c.revenue_ttm_millions,
        "revenue_currency": c.revenue_currency or "USD",
        "revenue_growth_pct": c.revenue_growth_pct,
        "gross_margin_pct": c.gross_margin_pct,
        "operating_margin_pct": c.operating_margin_pct,
        "fcf_margin_pct": c.fcf_margin_pct,
        "sm_pct_of_revenue": c.sm_pct_of_revenue,
        "rd_pct_of_revenue": c.rd_pct_of_revenue,
        "rule_of_40": c.rule_of_40,
        "nrr_pct": c.nrr_pct,
        "employees": c.employees,
        "revenue_per_employee_k": c.revenue_per_employee_k,
        "data_source": c.data_source,
        "fiscal_period": c.fiscal_period,
        "fetched_at": c.fetched_at.isoformat() if c.fetched_at else None,
    }
