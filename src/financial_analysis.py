"""Reproducible commercial-finance analysis from the existing project CSV exports.

Run from the repository root: python src/financial_analysis.py
The monthly financial export contains modeled finance assumptions; raw transactions
are used for transaction counts and an independent gross-sales cross-check only.
"""
from pathlib import Path
import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs'
OUT.mkdir(exist_ok=True)

def analyze():
    m = pd.read_csv(ROOT/'powerbi_monthly_financials.csv')
    sc = pd.read_csv(ROOT/'powerbi_scenario_financials.csv')
    vb = pd.read_csv(ROOT/'variance_bridge.csv')
    tx = pd.read_csv(ROOT/'retail_transactions_SYNTHETIC.csv')
    assert len(tx)==9000, 'Transaction count differs from documented source'
    assert len(m)==48, 'Expected 12 months × 4 categories'
    assert len(sc)==5, 'Expected five modeled promotion scenarios'
    assert tx.TransactionID.is_unique, 'Duplicate transaction IDs'
    assert not m.isna().any().any(), 'Missing monthly financial values'
    # Each component originates in the monthly model, allowing only source rounding drift.
    n = m.NetSales_GBP.sum(); cp=m.Contribution_GBP.sum(); plan=m.PlanContribution_GBP.sum()
    assert abs((m.GrossSales_GBP-m.PromoDiscounts_GBP-m.Returns_GBP-m.TradeSpend_GBP-m.NetSales_GBP).sum()) < 0.15
    assert abs((m.NetSales_GBP-m.COGS_GBP-m.VariableSelling_GBP-m.Contribution_GBP).sum()) < 0.15
    assert abs(cp-plan - m.ContributionVariance_GBP.sum()) < 0.15
    assert abs(cp - vb.iloc[-1].Amount_GBP) < 0.15
    assert abs(plan - vb.iloc[0].Amount_GBP) < 0.15
    assert abs(vb.iloc[1:-1].Amount_GBP.sum() -(cp-plan)) < 0.15
    assert abs(sc.loc[sc.Scenario=='Baseline','Contribution_GBP'].iloc[0]-cp)<0.15
    assert abs((tx.Quantity*tx.UnitPrice_GBP).sum()-m.GrossSales_GBP.sum())<0.2
    by_cat=m.groupby('Category',as_index=False)[['GrossSales_GBP','NetSales_GBP','Contribution_GBP','PlanContribution_GBP']].sum()
    by_cat['ContributionMargin']=by_cat.Contribution_GBP/by_cat.NetSales_GBP
    by_cat['Variance_GBP']=by_cat.Contribution_GBP-by_cat.PlanContribution_GBP
    by_month=m.groupby('Month',as_index=False)[['NetSales_GBP','Contribution_GBP','PlanContribution_GBP']].sum()
    by_month['ContributionMargin']=by_month.Contribution_GBP/by_month.NetSales_GBP
    by_cat.to_csv(OUT/'category_financial_analysis.csv',index=False)
    by_month.to_csv(OUT/'monthly_financial_analysis.csv',index=False)
    results={'transactions':len(tx),'monthly_category_rows':len(m),'gross_sales_gbp':round(m.GrossSales_GBP.sum(),2),'net_sales_gbp':round(n,2),'contribution_profit_gbp':round(cp,2),'contribution_margin_pct':round(100*cp/n,2),'plan_contribution_gbp':round(plan,2),'contribution_variance_gbp':round(cp-plan,2),'best_profit_scenario':sc.loc[sc.Contribution_GBP.idxmax(),'Scenario'],'best_profit_scenario_change_gbp':round(sc.Contribution_GBP.max()-cp,2)}
    (OUT/'validated_financial_results.json').write_text(json.dumps(results,indent=2))
    # Real plots generated from existing, labeled illustrative scenario data.
    fig,ax=plt.subplots(figsize=(10,4.8))
    ax.bar(sc.Scenario,sc.Contribution_GBP/1000)
    ax.axhline(cp/1000,linestyle='--',linewidth=1.2,label='Baseline')
    ax.set_ylabel('Modeled contribution profit (£000s)')
    ax.set_title('Promotion scenario profitability (synthetic model)')
    ax.tick_params(axis='x',rotation=15)
    ax.legend();fig.tight_layout();fig.savefig(OUT/'scenario_profitability.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.4))
    ax.plot(by_month.Month,by_month.ContributionMargin*100,marker='o')
    ax.set_ylabel('Contribution margin (%)');ax.set_title('Monthly contribution margin (modeled)')
    ax.tick_params(axis='x',rotation=45);fig.tight_layout();fig.savefig(OUT/'monthly_contribution_margin.png',dpi=160);plt.close(fig)
    print(json.dumps(results,indent=2))
    return results

if __name__=='__main__':analyze()
