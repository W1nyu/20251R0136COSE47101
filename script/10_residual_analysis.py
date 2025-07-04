import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
from pandas.api.types import is_numeric_dtype

# ---------------------------------------------------------------------------
# 1. CLI 설정.
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Residual time series analysis for hedonic model")
parser.add_argument("--panel_feat", default="output/panel_feat.parquet", help="panel feature data path")
parser.add_argument("--coef", default="output/coef_mean.csv", help="CSV of mean regression coefficients")
parser.add_argument("--output_dir", default="output", help="Directory to save residual results and plots")
parser.add_argument("--rolling_window", type=int, default=12, help="Rolling window size in months for trend")
args = parser.parse_args()

PANEL_PATH = Path(args.panel_feat)
COEF_PATH = Path(args.coef)
OUT_DIR = Path(args.output_dir)
OUT_DIR.mkdir(exist_ok=True, parents=True)

# 2. 데이터 로드.
print(f"▶ Loading panel features from {PANEL_PATH}")
df = pd.read_parquet(PANEL_PATH)
print(f"   Loaded: {df.shape[0]} rows × {df.shape[1]} cols")

# 3. 회귀계수 로드.
coef_df = pd.read_csv(COEF_PATH)
coef_series = coef_df.set_index('feature')['coef']

# 4. 피처 행렬 준비.
target = 'ln_price'
# 모델에 사용된 숫자형 피처 컬럼 선택.
feature_cols = [f for f in coef_series.index if f != 'const' and f in df.columns]
X = df[feature_cols]
# 상수항 추가.
X_sm = sm.add_constant(X)

# 5. 실제값 및 예측값.
y_true = df[target]
# X_sm 컬럼을 coef_series 인덱스에 맞추기(누락 컬럼은 0으로 채움).
X_sm = X_sm.reindex(columns=coef_series.index, fill_value=0)
y_pred = X_sm.dot(coef_series)

# 6. 잔차(로그 공간).
df_res = pd.DataFrame({
    'year_month': pd.to_datetime(df['year_month']),
    'residual': y_true - y_pred
})

# 7. 잔차 시계열 저장.
# 월별 평균 잔차 계산.
res_ts = df_res.groupby('year_month')['residual'].mean().reset_index()
# 이동 평균 계산.
res_ts['residual_roll_mean'] = res_ts['residual'].rolling(window=args.rolling_window, min_periods=1).mean()
res_ts.to_csv(OUT_DIR / 'residual_timeseries.csv', index=False)
print(f"▶ Residual time series saved → {OUT_DIR/'residual_timeseries.csv'}")

# 8. 잔차 히스토그램.
plt.figure(figsize=(6,4))
plt.hist(df_res['residual'].dropna(), bins=50, color='skyblue', edgecolor='k')
plt.title('Histogram of Residuals')
plt.xlabel('Residual (log price)')
plt.ylabel('Count')
plt.tight_layout()
plt.savefig(OUT_DIR / 'fig_residual_hist.png', dpi=150)
print(f"▶ Residual histogram saved → {OUT_DIR/'fig_residual_hist.png'}")
plt.close()

# 9. QQ-플롯.
gg = sm.qqplot(df_res['residual'].dropna(), line='45', fit=True)
gg.figure.set_size_inches(6,6)
gg.figure.tight_layout()
gg.figure.savefig(OUT_DIR / 'fig_residual_qq.png', dpi=150)
print(f"▶ QQ-plot of residuals saved → {OUT_DIR/'fig_residual_qq.png'}")
plt.close()

# 10. 잔차 추세 플롯.
plt.figure(figsize=(8,4))
plt.plot(res_ts['year_month'], res_ts['residual'], label='Mean Residual', alpha=0.6)
plt.plot(res_ts['year_month'], res_ts['residual_roll_mean'], label=f'{args.rolling_window}-month Rolling Mean', color='red')
plt.xlabel('Year-Month')
plt.ylabel('Mean Residual (log price)')
plt.title('Residual Trend Over Time')
plt.legend()
plt.tight_layout()
plt.savefig(OUT_DIR / 'fig_residual_trend.png', dpi=150)
print(f"▶ Residual trend plot saved → {OUT_DIR/'fig_residual_trend.png'}")
plt.close() 