import numpy as np
import json
import matplotlib.pyplot as plt
import tarfile
import os
from dataclasses import dataclass, asdict, field
from typing import List, Tuple, Dict, Any, Optional

# ───────────────────────────────────────────────
# Configuration dataclasses (minimal version)
# ───────────────────────────────────────────────

@dataclass
class LineConfig:
    label: str
    color: str
    visible: bool
    data_key: str

@dataclass
class AnnotationConfig:
    text: str
    xy: Tuple[float, float]
    xytext: Tuple[float, float]
    arrowprops: Dict = field(default_factory=dict)
    color: str = 'black'

@dataclass
class LegendConfig:
    loc: str = 'best'
    bbox_to_anchor: Optional[Tuple] = None
    draggable: bool = True

@dataclass
class SubplotConfig:
    title: str = ''
    lines: List[LineConfig] = field(default_factory=list)
    annotations: List[AnnotationConfig] = field(default_factory=list)
    legend: Optional[LegendConfig] = None
    grid: bool = True
    xlim: Tuple = (-np.inf, np.inf)
    ylim: Tuple = (-np.inf, np.inf)
    xscale: str = 'linear'
    yscale: str = 'linear'
    xlabel: str = ''

@dataclass
class FigureMetadata:
    figsize: Tuple[float, float]
    nrows: int
    ncols: int
    sharex: bool = True
    sharey: bool = False
    suptitle: str = ''
    shared_ylabel: str = 'Value'
    subplot_configs: List[SubplotConfig] = field(default_factory=list)

# ───────────────────────────────────────────────
# Helper functions
# ───────────────────────────────────────────────

def extract_metadata(fig, axs) -> FigureMetadata:
    axs = np.atleast_1d(axs)
    md = FigureMetadata(
        figsize=tuple(fig.get_size_inches()),
        nrows=len(axs) if axs.ndim == 1 else axs.shape[0],
        ncols=1 if axs.ndim == 1 else axs.shape[1],
        suptitle=fig._suptitle.get_text() if fig._suptitle else ''
    )

    for i, ax in enumerate(axs):
        sub = SubplotConfig(
            title=ax.get_title(),
            grid=ax.xaxis._gridOnMajor,
            xlim=tuple(ax.get_xlim()),
            ylim=tuple(ax.get_ylim()),
            xscale=ax.get_xscale(),
            yscale=ax.get_yscale(),
            xlabel=ax.get_xlabel() if i == len(axs)-1 else ''
        )

        leg = ax.get_legend()
        if leg:
            sub.legend = LegendConfig(
                loc=leg._loc,
                bbox_to_anchor=leg.get_bbox_to_anchor()._bbox.bounds if leg.get_bbox_to_anchor() else None,
                draggable=True
            )

        for j, line in enumerate(ax.lines):
            sub.lines.append(LineConfig(
                label=line.get_label(),
                color=line.get_color(),
                visible=line.get_visible(),
                data_key=f'subplot{i}_y{j}'
            ))

        for text in ax.texts:
            if hasattr(text, 'arrow_patch'):
                sub.annotations.append(AnnotationConfig(
                    text=text.get_text(),
                    xy=tuple(text.xy),
                    xytext=tuple(text.get_position()),
                    arrowprops=text.arrowprops or {},
                    color=text.get_color()
                ))

        md.subplot_configs.append(sub)

    return md

def get_fallback_dict(md: FigureMetadata) -> Dict:
    d = asdict(md)
    for sub in d['subplot_configs']:
        sub.pop('annotations', None)
    return d

def collect_line_data(axs) -> Dict[str, np.ndarray]:
    data = {}
    axs = np.atleast_1d(axs)
    for i, ax in enumerate(axs):
        for j, line in enumerate(ax.lines):
            data[f'subplot{i}_y{j}'] = line.get_ydata()
    return data

# ───────────────────────────────────────────────
# Main save function — creates .tgz with .npz + .mplmeta
# ───────────────────────────────────────────────

def save_figure_to_tgz(fig, axs, base_name="my-figure", tgz_path=None):
    if tgz_path is None:
        tgz_path = f"{base_name}.tgz"

    md = extract_metadata(fig, axs)

    # 1. Collect data arrays
    data_dict = collect_line_data(axs)

    # 2. Embed fallback metadata (no annotations)
    fallback_dict = get_fallback_dict(md)
    data_dict['metadata_fallback'] = np.array([json.dumps(fallback_dict)], dtype=object)

    # 3. Save npz
    npz_path = f"{base_name}_data.npz"
    np.savez_compressed(npz_path, **data_dict)

    # 4. Save full metadata as .mplmeta
    mplmeta_path = f"{base_name}.mplmeta"
    with open(mplmeta_path, 'w', encoding='utf-8') as f:
        json.dump(asdict(md), f, indent=2)

    # 5. Create tar.gz archive
    with tarfile.open(tgz_path, 'w:gz') as tar:
        tar.add(npz_path, arcname=os.path.basename(npz_path))
        tar.add(mplmeta_path, arcname=os.path.basename(mplmeta_path))

    # Cleanup temporary files
    for path in [npz_path, mplmeta_path]:
        if os.path.exists(path):
            os.remove(path)

    print(f"Figure saved to: {tgz_path}")
    print(f"   ├── {os.path.basename(npz_path)}")
    print(f"   └── {os.path.basename(mplmeta_path)}")

# ───────────────────────────────────────────────
# Example usage
# ───────────────────────────────────────────────

if __name__ == '__main__':
    # Create a small test figure
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True)

    x = np.linspace(0, 10, 300)
    ax1.plot(x, np.sin(x), label='sin')
    ax1.plot(x, np.cos(x), label='cos')
    ax1.lines[1].set_visible(False)
    leg1 = ax1.legend()
    leg1.set_draggable(True)
    ax1.set_title('Sine & Cosine')

    ax2.plot(x, x**2, label='x²')
    ax2.plot(x, np.exp(x/5), label='exp')
    leg2 = ax2.legend()
    leg2.set_draggable(True)
    ax2.set_yscale('log')
    ax2.set_title('Power & Exponential')

    fig.suptitle('Test Figure')
    plt.tight_layout()
    plt.show(block=False)

    # Save everything in one .tgz
    save_figure_to_tgz(fig, [ax1, ax2], base_name="test-figure-2026")