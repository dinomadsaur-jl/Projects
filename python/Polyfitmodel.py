import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.offline as pyo

# ---------- Polynomial regression class with ALL metrics methods ----------
class PolynomialRegression:
    def __init__(self, degree=2):
        self.degree = degree
        self.coeffs = None
        self.x_train = None
        self.y_train = None
        self.residuals = None
        self.fitted_values = None

    def _build_design(self, x):
        x = np.asarray(x)
        X = np.zeros((len(x), self.degree + 1))
        for j in range(self.degree + 1):
            X[:, j] = x ** j
        return X

    def fit(self, x, y):
        """Fit polynomial model and store training data"""
        self.x_train = np.asarray(x)
        self.y_train = np.asarray(y)
        X = self._build_design(self.x_train)
        self.coeffs, _, _, _ = np.linalg.lstsq(X, self.y_train, rcond=None)
        
        # Calculate fitted values and residuals
        self.fitted_values = self.predict(self.x_train)
        self.residuals = self.y_train - self.fitted_values
        return self

    def predict(self, x):
        """Predict y values for given x"""
        if self.coeffs is None:
            raise RuntimeError("Fit the model first")
        return self._build_design(x) @ self.coeffs

    # ============= RESIDUAL METRICS METHODS =============
    
    def get_residuals(self):
        """Return all residuals (errors)"""
        if self.residuals is None:
            raise RuntimeError("Fit the model first")
        return self.residuals
    
    def get_residual_variance(self, ddof=1):
        """Variance of residuals (spread of errors)"""
        if self.residuals is None:
            raise RuntimeError("Fit the model first")
        return np.var(self.residuals, ddof=ddof)
    
    def get_residual_std(self):
        """Standard deviation of residuals"""
        return np.sqrt(self.get_residual_variance())
    
    def get_mean_residual(self):
        """Mean of residuals (should be near 0 for good fit)"""
        if self.residuals is None:
            raise RuntimeError("Fit the model first")
        return np.mean(self.residuals)
    
    def get_mean_absolute_residual(self):
        """Mean absolute error - average magnitude of errors"""
        if self.residuals is None:
            raise RuntimeError("Fit the model first")
        return np.mean(np.abs(self.residuals))
    
    def get_median_absolute_residual(self):
        """Median absolute error - robust to outliers"""
        if self.residuals is None:
            raise RuntimeError("Fit the model first")
        return np.median(np.abs(self.residuals))
    
    def get_max_absolute_residual(self):
        """Maximum absolute error - worst outlier magnitude"""
        if self.residuals is None:
            raise RuntimeError("Fit the model first")
        return np.max(np.abs(self.residuals))
    
    def get_min_residual(self):
        """Most negative residual"""
        if self.residuals is None:
            raise RuntimeError("Fit the model first")
        return np.min(self.residuals)
    
    def get_max_residual(self):
        """Most positive residual"""
        if self.residuals is None:
            raise RuntimeError("Fit the model first")
        return np.max(self.residuals)
    
    def get_residual_range(self):
        """Range of residuals (max - min)"""
        return self.get_max_residual() - self.get_min_residual()
    
    def get_residual_skewness(self):
        """Skewness of residuals - asymmetry of error distribution"""
        if self.residuals is None:
            raise RuntimeError("Fit the model first")
        n = len(self.residuals)
        mean = np.mean(self.residuals)
        std = np.std(self.residuals, ddof=1)
        if std == 0:
            return 0
        return (np.sum((self.residuals - mean)**3) / n) / (std**3)
    
    def get_residual_kurtosis(self):
        """Kurtosis of residuals - tail heaviness"""
        if self.residuals is None:
            raise RuntimeError("Fit the model first")
        n = len(self.residuals)
        mean = np.mean(self.residuals)
        std = np.std(self.residuals, ddof=1)
        if std == 0:
            return 0
        return (np.sum((self.residuals - mean)**4) / n) / (std**4) - 3
    
    def get_percentile_residual(self, percentile):
        """Get specific percentile of absolute residuals"""
        if self.residuals is None:
            raise RuntimeError("Fit the model first")
        return np.percentile(np.abs(self.residuals), percentile)
    
    def get_worst_outliers(self, n=5):
        """Get the n worst outliers"""
        if self.residuals is None:
            raise RuntimeError("Fit the model first")
        abs_resid = np.abs(self.residuals)
        indices = np.argsort(abs_resid)[-n:][::-1]  # Top n in descending order
        
        outliers = []
        for idx in indices:
            outliers.append({
                'rank': len(outliers) + 1,
                'x': self.x_train[idx],
                'y': self.y_train[idx],
                'fitted': self.fitted_values[idx],
                'residual': self.residuals[idx],
                'abs_residual': abs_resid[idx]
            })
        return outliers
    
    def get_good_fits(self, threshold=1.0):
        """Get points with absolute residual below threshold"""
        if self.residuals is None:
            raise RuntimeError("Fit the model first")
        abs_resid = np.abs(self.residuals)
        indices = np.where(abs_resid < threshold)[0]
        
        good_points = []
        for idx in indices:
            good_points.append({
                'x': self.x_train[idx],
                'y': self.y_train[idx],
                'fitted': self.fitted_values[idx],
                'residual': self.residuals[idx],
                'abs_residual': abs_resid[idx]
            })
        return good_points
    
    def count_outliers(self, sigma_threshold=2.0):
        """Count points with |residual| > sigma_threshold * std(residuals)"""
        if self.residuals is None:
            raise RuntimeError("Fit the model first")
        std = self.get_residual_std()
        threshold = sigma_threshold * std
        abs_resid = np.abs(self.residuals)
        return np.sum(abs_resid > threshold)
    
    def get_residual_histogram(self, bins=10):
        """Get histogram data of residuals"""
        if self.residuals is None:
            raise RuntimeError("Fit the model first")
        counts, bin_edges = np.histogram(self.residuals, bins=bins)
        return {
            'counts': counts,
            'bin_edges': bin_edges,
            'bin_centers': (bin_edges[:-1] + bin_edges[1:]) / 2
        }
    
    def get_residual_summary(self):
        """Get ALL residual metrics in one dictionary"""
        if self.residuals is None:
            raise RuntimeError("Fit the model first")
        
        abs_resid = np.abs(self.residuals)
        
        return {
            'basic': {
                'count': len(self.residuals),
                'sum': np.sum(self.residuals),
                'mean': np.mean(self.residuals),
                'median': np.median(self.residuals),
            },
            'spread': {
                'variance': self.get_residual_variance(),
                'std_dev': self.get_residual_std(),
                'range': self.get_residual_range(),
                'iqr': np.percentile(self.residuals, 75) - np.percentile(self.residuals, 25),
            },
            'absolute_errors': {
                'mean_abs': self.get_mean_absolute_residual(),
                'median_abs': self.get_median_absolute_residual(),
                'max_abs': self.get_max_absolute_residual(),
                'min_abs': np.min(abs_resid),
                'p90_abs': np.percentile(abs_resid, 90),
                'p95_abs': np.percentile(abs_resid, 95),
                'p99_abs': np.percentile(abs_resid, 99),
            },
            'shape': {
                'skewness': self.get_residual_skewness(),
                'kurtosis': self.get_residual_kurtosis(),
                'min': self.get_min_residual(),
                'max': self.get_max_residual(),
            },
            'outliers': {
                'count_2sigma': self.count_outliers(2.0),
                'count_3sigma': self.count_outliers(3.0),
                'worst_3': self.get_worst_outliers(3),
            }
        }
    
    def print_residual_summary(self):
        """Print a formatted residual summary"""
        summary = self.get_residual_summary()
        
        print("\n" + "=" * 60)
        print(f"RESIDUAL ANALYSIS - Polynomial Degree {self.degree}")
        print("=" * 60)
        
        print("\n📊 BASIC STATISTICS:")
        print(f"  Number of points: {summary['basic']['count']}")
        print(f"  Mean residual: {summary['basic']['mean']:.6f} (should be near 0)")
        print(f"  Median residual: {summary['basic']['median']:.6f}")
        
        print("\n📈 SPREAD METRICS:")
        print(f"  Variance: {summary['spread']['variance']:.6f}")
        print(f"  Standard deviation: {summary['spread']['std_dev']:.6f}")
        print(f"  Range: {summary['spread']['range']:.6f}")
        print(f"  IQR: {summary['spread']['iqr']:.6f}")
        
        print("\n🎯 ABSOLUTE ERRORS:")
        print(f"  Mean absolute error: {summary['absolute_errors']['mean_abs']:.6f}")
        print(f"  Median absolute error: {summary['absolute_errors']['median_abs']:.6f}")
        print(f"  Max absolute error: {summary['absolute_errors']['max_abs']:.6f}")
        print(f"  Min absolute error: {summary['absolute_errors']['min_abs']:.6f}")
        print(f"  90th percentile: {summary['absolute_errors']['p90_abs']:.6f}")
        print(f"  95th percentile: {summary['absolute_errors']['p95_abs']:.6f}")
        print(f"  99th percentile: {summary['absolute_errors']['p99_abs']:.6f}")
        
        print("\n📐 DISTRIBUTION SHAPE:")
        print(f"  Skewness: {summary['shape']['skewness']:.6f} (0 = symmetric)")
        print(f"  Kurtosis: {summary['shape']['kurtosis']:.6f} (0 = normal)")
        print(f"  Min residual: {summary['shape']['min']:.6f}")
        print(f"  Max residual: {summary['shape']['max']:.6f}")
        
        print("\n⚠️ OUTLIERS:")
        print(f"  Points > 2σ: {summary['outliers']['count_2sigma']}")
        print(f"  Points > 3σ: {summary['outliers']['count_3sigma']}")
        
        print("\n🔍 TOP 3 WORST OUTLIERS:")
        for i, outlier in enumerate(summary['outliers']['worst_3']):
            print(f"  #{outlier['rank']}: x={outlier['x']:.3f}, y={outlier['y']:.3f}, "
                  f"fitted={outlier['fitted']:.3f}, residual={outlier['residual']:.3f}")
    
    def plot_residual_analysis(self, filename=None):
        """Create comprehensive residual diagnostic plots"""
        if self.residuals is None:
            raise RuntimeError("Fit the model first")
        
        fig = make_subplots(
            rows=2, cols=3,
            subplot_titles=("Residuals vs Fitted", "Q-Q Plot", "Residual Histogram",
                           "Residuals vs x", "Absolute Residuals", "Residual Distribution"),
            specs=[[{"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}, {"secondary_y": True}]]
        )
        
        # Plot 1: Residuals vs Fitted Values
        fig.add_trace(go.Scatter(x=self.fitted_values, y=self.residuals, mode='markers',
                                 marker=dict(color='blue', size=6), name='Residuals'), row=1, col=1)
        fig.add_hline(y=0, line_dash="dash", line_color="red", row=1, col=1)
        
        # Plot 2: Q-Q Plot (quantile-quantile)
        sorted_resid = np.sort(self.residuals)
        theoretical_quantiles = np.random.normal(0, self.get_residual_std(), len(sorted_resid))
        theoretical_quantiles.sort()
        fig.add_trace(go.Scatter(x=theoretical_quantiles, y=sorted_resid, mode='markers',
                                 marker=dict(color='green', size=4), name='Q-Q'), row=1, col=2)
        # Add diagonal line
        min_val = min(theoretical_quantiles.min(), sorted_resid.min())
        max_val = max(theoretical_quantiles.max(), sorted_resid.max())
        fig.add_trace(go.Scatter(x=[min_val, max_val], y=[min_val, max_val], mode='lines',
                                 line=dict(color='red', dash='dash'), name='Normal line'), row=1, col=2)
        
        # Plot 3: Histogram of residuals
        hist_data = self.get_residual_histogram(bins=20)
        fig.add_trace(go.Bar(x=hist_data['bin_centers'], y=hist_data['counts'],
                             marker_color='purple', name='Histogram'), row=1, col=3)
        
        # Plot 4: Residuals vs x
        fig.add_trace(go.Scatter(x=self.x_train, y=self.residuals, mode='markers',
                                 marker=dict(color='orange', size=6), name='Residuals'), row=2, col=1)
        fig.add_hline(y=0, line_dash="dash", line_color="red", row=2, col=1)
        
        # Plot 5: Absolute residuals
        fig.add_trace(go.Bar(x=self.x_train, y=np.abs(self.residuals),
                            marker_color='red', name='|Residual|'), row=2, col=2)
        
        # Plot 6: Box plot of residuals
        fig.add_trace(go.Box(y=self.residuals, name='Residuals',
                            marker_color='cyan', boxmean='sd'), row=2, col=3)
        
        # Update axes
        fig.update_xaxes(title_text="Fitted values", row=1, col=1)
        fig.update_yaxes(title_text="Residuals", row=1, col=1)
        fig.update_xaxes(title_text="Theoretical quantiles", row=1, col=2)
        fig.update_yaxes(title_text="Sample quantiles", row=1, col=2)
        fig.update_xaxes(title_text="Residual value", row=1, col=3)
        fig.update_yaxes(title_text="Frequency", row=1, col=3)
        fig.update_xaxes(title_text="x", row=2, col=1)
        fig.update_yaxes(title_text="Residuals", row=2, col=1)
        fig.update_xaxes(title_text="x", row=2, col=2)
        fig.update_yaxes(title_text="|Residual|", row=2, col=2)
        fig.update_xaxes(title_text="", row=2, col=3)
        fig.update_yaxes(title_text="Residual", row=2, col=3)
        
        fig.update_layout(title=f"Residual Analysis - Polynomial Degree {self.degree}",
                         height=800, width=1400, template='plotly_white',
                         showlegend=False)
        
        if filename:
            pyo.plot(fig, filename=filename, auto_open=False)
            print(f"Residual plot saved as '{filename}'")
        else:
            pyo.plot(fig, filename=f"residual_analysis_deg{self.degree}.html", auto_open=False)
        
        return fig

    # ============= CLOSENESS METRICS METHODS =============
    
    def calculate_closeness(self, other_model, num_points=100):
        """Calculate how close this polynomial fit is to another polynomial fit"""
        if self.coeffs is None or other_model.coeffs is None:
            raise RuntimeError("Both models must be fitted first")
        
        # Find overlapping x range
        x_min = max(np.min(self.x_train), np.min(other_model.x_train))
        x_max = min(np.max(self.x_train), np.max(other_model.x_train))
        
        if x_min >= x_max:
            return {'error': 'No overlapping x range'}
        
        # Generate points in overlapping region
        x_common = np.linspace(x_min, x_max, num_points)
        
        # Get predictions from both models
        y_self = self.predict(x_common)
        y_other = other_model.predict(x_common)
        
        # Calculate differences
        differences = y_self - y_other
        abs_differences = np.abs(differences)
        
        # Find point of maximum difference
        max_diff_idx = np.argmax(abs_differences)
        
        # Closeness metrics
        metrics = {
            'mean_abs_difference': np.mean(abs_differences),
            'median_abs_difference': np.median(abs_differences),
            'max_abs_difference': np.max(abs_differences),
            'min_difference': np.min(differences),
            'max_difference': np.max(differences),
            'std_difference': np.std(differences, ddof=1),
            'rmse_difference': np.sqrt(np.mean(differences**2)),
            'x_range': [x_min, x_max],
            'x_max_difference': x_common[max_diff_idx],
            'value_at_max_difference': {
                'self': y_self[max_diff_idx],
                'other': y_other[max_diff_idx],
                'difference': differences[max_diff_idx]
            }
        }
        
        # Coefficient comparison
        min_len = min(len(self.coeffs), len(other_model.coeffs))
        coeff_diff = self.coeffs[:min_len] - other_model.coeffs[:min_len]
        
        metrics['coefficient_differences'] = coeff_diff
        metrics['coefficient_distance'] = np.linalg.norm(coeff_diff)
        metrics['coefficient_max_diff'] = np.max(np.abs(coeff_diff))
        metrics['coefficient_mean_abs_diff'] = np.mean(np.abs(coeff_diff))
        
        return metrics
    
    def print_closeness_summary(self, other_model):
        """Print formatted closeness summary"""
        metrics = self.calculate_closeness(other_model)
        
        if 'error' in metrics:
            print(f"Error: {metrics['error']}")
            return
        
        print("\n" + "=" * 60)
        print("CLOSENESS METRICS BETWEEN TWO POLYNOMIAL FITS")
        print("=" * 60)
        print(f"Overlapping x range: [{metrics['x_range'][0]:.3f}, {metrics['x_range'][1]:.3f}]")
        
        print("\n📏 DIFFERENCE METRICS:")
        print(f"  Mean absolute difference: {metrics['mean_abs_difference']:.6f}")
        print(f"  Median absolute difference: {metrics['median_abs_difference']:.6f}")
        print(f"  Max absolute difference: {metrics['max_abs_difference']:.6f} at x = {metrics['x_max_difference']:.3f}")
        print(f"  Std deviation of differences: {metrics['std_difference']:.6f}")
        print(f"  RMSE between fits: {metrics['rmse_difference']:.6f}")
        print(f"  Range of differences: [{metrics['min_difference']:.6f}, {metrics['max_difference']:.6f}]")
        
        print("\n🔢 COEFFICIENT COMPARISON:")
        for i, diff in enumerate(metrics['coefficient_differences']):
            print(f"  β_{i} difference: {diff:.6f}")
        print(f"  Euclidean distance: {metrics['coefficient_distance']:.6f}")
        print(f"  Max coefficient difference: {metrics['coefficient_max_diff']:.6f}")
        print(f"  Mean absolute coefficient diff: {metrics['coefficient_mean_abs_diff']:.6f}")
    
    def plot_comparison(self, other_model, title="Polynomial Fit Comparison", 
                        filename="poly_comparison.html"):
        """Create visualization comparing this model with another"""
        metrics = self.calculate_closeness(other_model)
        
        if 'error' in metrics:
            print(f"Error: {metrics['error']}")
            return
        
        # Generate smooth curves for both models
        x_min_total = min(np.min(self.x_train), np.min(other_model.x_train)) - 0.2
        x_max_total = max(np.max(self.x_train), np.max(other_model.x_train)) + 0.2
        x_total = np.linspace(x_min_total, x_max_total, 300)
        
        x_overlap = np.linspace(metrics['x_range'][0], metrics['x_range'][1], 300)
        y_self_overlap = self.predict(x_overlap)
        y_other_overlap = other_model.predict(x_overlap)
        
        # Create figure
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=("Data and Fits", 
                           "Fits in Overlapping Region",
                           "Difference Between Fits",
                           "Absolute Difference Distribution"),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": True}]]
        )
        
        # Plot 1: Data and fits
        fig.add_trace(go.Scatter(x=self.x_train, y=self.y_train, mode='markers',
                                 name=f'Data 1 (deg{self.degree})', 
                                 marker=dict(color='blue', size=5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=other_model.x_train, y=other_model.y_train, mode='markers',
                                 name=f'Data 2 (deg{other_model.degree})', 
                                 marker=dict(color='red', size=5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=x_total, y=self.predict(x_total), mode='lines',
                                 name=f'Fit {self.degree}', line=dict(color='blue', width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=x_total, y=other_model.predict(x_total), mode='lines',
                                 name=f'Fit {other_model.degree}', line=dict(color='red', width=2)), row=1, col=1)
        
        # Plot 2: Fits in overlapping region
        fig.add_trace(go.Scatter(x=x_overlap, y=y_self_overlap, mode='lines',
                                 name=f'Fit {self.degree} (overlap)', 
                                 line=dict(color='blue', width=3)), row=1, col=2)
        fig.add_trace(go.Scatter(x=x_overlap, y=y_other_overlap, mode='lines',
                                 name=f'Fit {other_model.degree} (overlap)', 
                                 line=dict(color='red', width=3)), row=1, col=2)
        
        # Fill between to show difference area
        fig.add_trace(go.Scatter(x=x_overlap, y=y_self_overlap, mode='lines',
                                 line=dict(color='blue', width=1), showlegend=False), row=1, col=2)
        fig.add_trace(go.Scatter(x=x_overlap, y=y_other_overlap, mode='lines',
                                 fill='tonexty', fillcolor='rgba(128,128,128,0.3)',
                                 line=dict(color='red', width=1), name='Difference area'), row=1, col=2)
        
        # Plot 3: Difference between fits
        differences = y_self_overlap - y_other_overlap
        colors = ['red' if d < 0 else 'blue' for d in differences]
        fig.add_trace(go.Bar(x=x_overlap, y=differences, marker_color=colors,
                            name='Difference (Fit1 - Fit2)'), row=2, col=1)
        fig.add_hline(y=0, line_dash="dash", line_color="black", row=2, col=1)
        
        # Plot 4: Histogram of absolute differences
        abs_diffs = np.abs(differences)
        fig.add_trace(go.Histogram(x=abs_diffs, nbinsx=20, marker_color='green',
                                   name='|Difference|'), row=2, col=2)
        fig.add_vline(x=metrics['mean_abs_difference'], line_dash="dash", 
                     line_color="red", annotation_text=f"Mean={metrics['mean_abs_difference']:.3f}", 
                     row=2, col=2)
        
        # Update axes
        fig.update_xaxes(title_text="x", row=1, col=1)
        fig.update_yaxes(title_text="y", row=1, col=1)
        fig.update_xaxes(title_text="x (overlap)", row=1, col=2)
        fig.update_yaxes(title_text="y", row=1, col=2)
        fig.update_xaxes(title_text="x (overlap)", row=2, col=1)
        fig.update_yaxes(title_text="Difference", row=2, col=1)
        fig.update_xaxes(title_text="|Difference|", row=2, col=2)
        fig.update_yaxes(title_text="Frequency", row=2, col=2)
        
        # Add metrics annotation
        fig.add_annotation(x=0.02, y=0.98, xref="paper", yref="paper",
                          text=f"Mean |Diff| = {metrics['mean_abs_difference']:.4f}<br>"
                               f"Max |Diff| = {metrics['max_abs_difference']:.4f}<br>"
                               f"Coef Distance = {metrics['coefficient_distance']:.4f}",
                          showarrow=False, font=dict(size=10),
                          bordercolor="black", borderwidth=1, bgcolor="white")
        
        fig.update_layout(title=title, height=800, width=1200, template='plotly_white')
        pyo.plot(fig, filename=filename, auto_open=False)
        print(f"Comparison plot saved as '{filename}'")


# ---------- Example usage ----------
if __name__ == "__main__":
    # Generate first dataset
    np.random.seed(42)
    x1 = np.linspace(-3, 3, 30)
    y_true1 = 2 - 1.5*x1 + 0.8*x1**2 - 0.1*x1**3
    y1 = y_true1 + np.random.normal(0, 1.2, size=x1.shape)
    y1[5] += 4.0   # Add big outlier
    y1[20] -= 3.5  # Add another outlier
    
    # Generate second dataset
    np.random.seed(99)
    x2 = np.linspace(-2.8, 3.1, 25)
    y_true2 = 2 - 1.5*x2 + 0.8*x2**2 - 0.1*x2**3
    y2 = y_true2 + np.random.normal(0, 0.9, size=x2.shape)
    y2[8] += 3.0   # Add outlier
    y2[18] -= 2.8  # Add another outlier
    
    # Create and fit models
    print("\n🔷 FITTING POLYNOMIAL MODELS")
    print("=" * 60)
    
    model1 = PolynomialRegression(degree=3).fit(x1, y1)
    model2 = PolynomialRegression(degree=3).fit(x2, y2)
    
    # ===== RESIDUAL METRICS for Model 1 =====
    print("\n" + "🔷" * 30)
    print("MODEL 1 - RESIDUAL ANALYSIS")
    print("🔷" * 30)
    
    # Print full summary
    model1.print_residual_summary()
    
    # Individual metric examples
    print("\n📌 INDIVIDUAL METRIC EXAMPLES:")
    print(f"  Residual variance: {model1.get_residual_variance():.6f}")
    print(f"  Mean absolute error: {model1.get_mean_absolute_residual():.6f}")
    print(f"  95th percentile error: {model1.get_percentile_residual(95):.6f}")
    print(f"  Skewness: {model1.get_residual_skewness():.6f}")
    
    # Get worst outliers
    worst_3 = model1.get_worst_outliers(3)
    print("\n🔍 TOP 3 WORST OUTLIERS (detailed):")
    for out in worst_3:
        print(f"  #{out['rank']}: x={out['x']:.3f}, y={out['y']:.3f}, "
              f"fitted={out['fitted']:.3f}, residual={out['residual']:.3f}")
    
    # Get good fits (within 1.0)
    good_fits = model1.get_good_fits(threshold=1.0)
    print(f"\n✅ Points with |residual| < 1.0: {len(good_fits)} out of {len(x1)}")
    
    # Create residual plot
    model1.plot_residual_analysis(filename="model1_residuals.html")
    
    # ===== RESIDUAL METRICS for Model 2 =====
    print("\n" + "🔶" * 30)
    print("MODEL 2 - RESIDUAL ANALYSIS")
    print("🔶" * 30)
    
    model2.print_residual_summary()
    model2.plot_residual_analysis(filename="model2_residuals.html")
    
    # ===== CLOSENESS METRICS between models =====
    print("\n" + "=" * 60)
    print("COMPARING MODEL 1 AND MODEL 2")
    print("=" * 60)
    
    model1.print_closeness_summary(model2)
    model1.plot_comparison(model2, filename="model_comparison.html")
    
    # ===== COMPARE RESIDUAL METRICS SIDE BY SIDE =====
    print("\n" + "=" * 60)
    print("RESIDUAL METRICS COMPARISON")
    print("=" * 60)
    
    r1 = model1.get_residual_summary()
    r2 = model2.get_residual_summary()
    
    print(f"\n{'Metric':<25} {'Model 1':<15} {'Model 2':<15} {'Better':<10}")
    print("-" * 65)
    
    # Compare variance (lower is better)
    better = "Model 1" if r1['spread']['variance'] < r2['spread']['variance'] else "Model 2"
    print(f"{'Variance':<25} {r1['spread']['variance']:<15.6f} {r2['spread']['variance']:<15.6f} {better:<10}")
    
    # Compare mean absolute error (lower is better)
    better = "Model 1" if r1['absolute_errors']['mean_abs'] < r2['absolute_errors']['mean_abs'] else "Model 2"
    print(f"{'Mean Absolute Error':<25} {r1['absolute_errors']['mean_abs']:<15.6f} {r2['absolute_errors']['mean_abs']:<15.6f} {better:<10}")
    
    # Compare max absolute error (lower is better)
    better = "Model 1" if r1['absolute_errors']['max_abs'] < r2['absolute_errors']['max_abs'] else "Model 2"
    print(f"{'Max Absolute Error':<25} {r1['absolute_errors']['max_abs']:<15.6f} {r2['absolute_errors']['max_abs']:<15.6f} {better:<10}")
    
    # Compare outlier counts (lower is better)
    better = "Model 1" if r1['outliers']['count_2sigma'] < r2['outliers']['count_2sigma'] else "Model 2"
    print(f"{'Outliers (>2σ)':<25} {r1['outliers']['count_2sigma']:<15} {r2['outliers']['count_2sigma']:<15} {better:<10}")