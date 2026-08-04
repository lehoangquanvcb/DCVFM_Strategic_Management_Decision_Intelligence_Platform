from __future__ import annotations

from analytics import advanced_fund_analytics, executive_metrics, integrated_financial_model, product_profitability, distribution_intelligence, compliance_cockpit, business_plan_kpi, decision_summary
from data_quality import quality_summary


def answer(question: str, data, regime: str) -> str:
    q=(question or "").lower().strip(); ex=executive_metrics(data); quality=quality_summary(data)
    if not q: return "Nhập câu hỏi về AUM, hiệu quả quỹ, thị trường, vĩ mô, tài chính, vận hành hoặc chất lượng dữ liệu."
    if "aum" in q or "dòng tiền" in q:
        return f"AUM hiện tại trong Master là {ex['aum']/1000:,.1f} nghìn tỷ đồng; tăng {ex['aum_growth']:.1%} so với tháng trước. Dòng tiền ròng 3 tháng là {ex['flow_3m']:,.0f} tỷ đồng. Cần đọc cùng Market regime = {regime} để tách tăng trưởng do thị trường và do huy động mới."
    if "lợi nhuận" in q or "doanh thu" in q or "fee" in q:
        m=integrated_financial_model(data).iloc[-1]; return f"Kịch bản 2029 minh họa: AUM cuối kỳ {m['Ending_AUM_VND_bn']/1000:,.1f} nghìn tỷ, doanh thu {m['Revenue_VND_bn']:,.0f} tỷ và NPAT {m['NPAT_VND_bn']:,.0f} tỷ. Drivers chính là market return, net flow, fee yield và operating leverage trong Financial_Drivers."
    if "dữ liệu" in q or "quality" in q or "giả định" in q:
        return f"Data quality score là {quality['score']:.0f}/100; {quality['verified_pct']:.0%} trường yêu cầu đã được verified và {quality['assumption_pct']:.0%} nằm trong các domain dựa trên assumption. Có {quality['overdue']} domain quá hạn cập nhật."
    if "quỹ" in q or "alpha" in q or "hiệu quả" in q:
        p=advanced_fund_analytics(data).iloc[0]; return f"Theo dữ liệu hiện có, {p['Fund_Code']} có annualized return cao nhất ({p['Annualized_Return']:.1%}), alpha 3 tháng {p['Alpha_3M']:.1%} và max drawdown {p['Max_Drawdown']:.1%}. Kết quả phụ thuộc dữ liệu NAV/benchmark đang được đánh dấu nguồn trong Master."
    if "phân phối" in q or "kênh" in q:
        d=distribution_intelligence(data); r=d.iloc[0]; return f"Kênh có AUM lớn nhất là {r['Channel']} với {r['Ending_AUM_VND_bn']:,.0f} tỷ đồng, chiếm {r['AUM_Share_Pct']:.1%}. Cần đọc cùng net sales, retention và cost/net sales trước khi phân bổ ngân sách phân phối."
    if "lợi nhuận quỹ" in q or "product profitability" in q or "điểm hòa vốn" in q:
        p=product_profitability(data); r=p.iloc[0]; return f"Theo giả định trong Master, {r['Fund_Code']} tạo contribution cao nhất {r['Contribution_VND_bn']:,.1f} tỷ đồng, margin {r['Contribution_Margin_Pct']:.1%}. Đây là product economics, không phải NAV performance."
    if "tuân thủ" in q or "compliance" in q:
        c=compliance_cockpit(data); n=int((c['Status']=='Action').sum()); return f"Compliance Cockpit có {n} control cần hành động. Cần xác minh quy định, threshold và evidence với Compliance/Legal trước khi dùng cho báo cáo chính thức."
    if "kế hoạch" in q or "kpi" in q or "forecast" in q:
        k=business_plan_kpi(data); r=k.sort_values('Forecast_vs_Plan_Pct').iloc[0]; return f"KPI lệch kế hoạch lớn nhất là {r['KPI']}: forecast so với plan {r['Forecast_vs_Plan_Pct']:.1%}, trạng thái {r['Status']}."
    if "vĩ mô" in q or "macro" in q or "lãi suất" in q or "tỷ giá" in q:
        m=data["Macro_Indicators"]; return "Macro pulse: " + "; ".join(f"{r.Indicator}: {r.Current_Value} {r.Unit} ({r.Direction})" for _,r in m.head(6).iterrows()) + ". Các dòng Assumption cần thay bằng số công bố chính thức."
    if "vận hành" in q or "sla" in q or "operations" in q:
        o=data["Operating_KPI"]; attention=o[o["Status"].astype(str).str.lower().isin(["action","off track","watch"])]
        return "Operating KPIs cần theo dõi: " + "; ".join(f"{r.KPI}: {r.Status} — {r.Management_Action}" for _,r in attention.head(5).iterrows())
    if "quyết định" in q or "decision" in q:
        d=decision_summary(data); return f"Decision Tracker đang có {d['open']} mục mở, trong đó {d['high']} mục ưu tiên cao; tiến độ bình quân {d['avg_progress']:.0%}."
    return f"Tôi chưa nhận diện rõ domain của câu hỏi. Trạng thái tổng quát: AUM {ex['aum']/1000:,.1f} nghìn tỷ, market regime {regime}, data quality {quality['score']:.0f}/100."
