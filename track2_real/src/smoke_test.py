"""Phase 1 smoke test: 5 SPOC 2-minute TPFs, TIC candidate stars, one injected dip, difference images.

Run from the repo root:  python track2_real/src/smoke_test.py
Raw files are cached in data/raw (git-ignored). Figures and the summary CSV go to track2_real/outputs.
Candidate stars come from the TIC (Gaia-derived). Proper motion is ignored.
The injection here is for the smoke test only (fixed depth, box transit, Gaussian PSF).
"""
import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import astropy.units as u
import lightkurve as lk
from astropy.coordinates import SkyCoord
from astroquery.mast import Catalogs

sys.path.insert(0, str(Path(__file__).parent))
from pixels import difference_images, inject_transit, star_flux_e_per_s  # noqa: E402

warnings.filterwarnings("ignore", message=".*tpfmodel.*")

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "track2_real" / "outputs"

PIX_ARCSEC = 21.0       # TESS pixel scale, about 21 arcsec
MAX_PIX = 3.0           # candidate radius in pixels
MAX_STARS = 20          # SPEC: N
SIGMA_PIX = 1.0         # Gaussian PSF for the injection (approximation)
SMOKE_DEPTH = 0.01      # fractional depth, smoke test only
SMOKE_DURATION_D = 3.0 / 24.0

# (label, search centre, search radius in degrees, number of targets)
FIELDS = [
    ("crowded", SkyCoord(l=300 * u.deg, b=-1 * u.deg, frame="galactic").icrs, 0.2, 3),
    ("sparse", SkyCoord(ra=192.86 * u.deg, dec=27.13 * u.deg), 0.5, 2),
]


def pick_targets():
    """First unique TIC IDs by distance from each field centre, latest sector per target."""
    picks = []
    for label, centre, radius, n in FIELDS:
        res = lk.search_targetpixelfile(centre, radius=radius * u.deg, author="SPOC", exptime=120, mission="TESS")
        tab = res.table.to_pandas()
        tab["row"] = np.arange(len(tab))
        tab = tab.sort_values(["distance", "sequence_number"], ascending=[True, False])
        first = tab.drop_duplicates("target_name").head(n)
        picks += [(label, res[int(r)]) for r in first["row"]]
    return picks


def candidate_stars(tpf):
    """TIC stars within MAX_PIX of the target, with zero-based pixel positions from the TPF WCS."""
    centre = SkyCoord(tpf.ra * u.deg, tpf.dec * u.deg)
    cat = Catalogs.query_region(centre, radius=(MAX_PIX + 1.0) * PIX_ARCSEC * u.arcsec, catalog="Tic").to_pandas()
    n_query = len(cat)
    cat["ID"] = cat["ID"].astype(str)
    x, y = tpf.wcs.all_world2pix(cat["ra"].to_numpy(), cat["dec"].to_numpy(), 0)
    cat["x"], cat["y"] = x, y
    me = cat[cat["ID"] == str(tpf.targetid)].iloc[0]
    cat["d"] = np.hypot(cat["x"] - me["x"], cat["y"] - me["y"])
    keep = (cat["objType"] == "STAR") & (cat["disposition"] != "DUPLICATE") & cat["Tmag"].notna()
    cat = cat[keep & (cat["d"] <= MAX_PIX)]
    h, w = tpf.flux.shape[1:]
    cat = cat[(cat["x"] >= -0.5) & (cat["x"] <= w - 0.5) & (cat["y"] >= -0.5) & (cat["y"] <= h - 0.5)]
    return cat.sort_values("Tmag").reset_index(drop=True), me, n_query


def one_target(i, label, hit):
    tpf = hit.download(download_dir=str(RAW))
    flux = tpf.flux.value
    time = tpf.time.value
    cat, me, n_query = candidate_stars(tpf)
    kept = cat.head(MAX_STARS)

    med = np.nanmedian(flux, axis=0)
    expected = float(star_flux_e_per_s(me["Tmag"]))
    measured = float(med[tpf.pipeline_mask].sum())

    row = dict(
        field=label, tic_id=int(tpf.targetid), sector=tpf.sector, camera=tpf.camera, ccd=tpf.ccd,
        tpf_shape="x".join(map(str, flux.shape)), n_finite_cadences=int(np.isfinite(flux).all(axis=(1, 2)).sum()),
        target_tmag=float(me["Tmag"]), target_x=float(me["x"]), target_y=float(me["y"]),
        n_tic_query=n_query, n_candidates_3px=len(cat), n_kept=len(kept),
        n_tmag_le_16=int((cat["Tmag"] <= 16).sum()), n_tmag_le_13=int((cat["Tmag"] <= 13).sum()),
        flux_ratio_measured_over_expected=measured / expected,
    )

    # smoke injection: random brightish candidate, random period and epoch, fixed depth and duration
    rng = np.random.default_rng(i)
    pool = kept[kept["Tmag"] <= 15].reset_index(drop=True)
    if pool.empty:
        row.update(note="no candidate with Tmag <= 15, injection skipped")
        return row, None
    true = pool.iloc[rng.integers(len(pool))]
    period = rng.uniform(1.5, 5.0)
    epoch = time[0] + rng.uniform(0.0, period)
    injected = inject_transit(flux, time, true["x"], true["y"], true["Tmag"], SIGMA_PIX,
                              period, epoch, SMOKE_DURATION_D, SMOKE_DEPTH)
    diff, ref, noise, n_in, n_out = difference_images(injected, time, period, epoch, SMOKE_DURATION_D)
    py, px = np.unravel_index(np.argmax(diff), diff.shape)
    near_peak = kept.iloc[int(np.argmin(np.hypot(kept["x"] - px, kept["y"] - py)))]
    row.update(
        true_tic=true["ID"], true_tmag=float(true["Tmag"]), period_d=period, n_in=n_in, n_out=n_out,
        peak_z=float(diff[py, px] / noise[py, px]), nearest_to_peak_is_true=bool(near_peak["ID"] == true["ID"]),
    )

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    panels = [("difference (out - in), e-/s", diff, None), ("reference, log10 e-/s", np.log10(np.clip(ref, 1, None)), None),
              ("noise (std error), e-/s", noise, None)]
    for ax, (title, img, _) in zip(axes, panels):
        im = ax.imshow(img, origin="lower", cmap="viridis")
        ax.set_title(title, fontsize=9)
        fig.colorbar(im, ax=ax, fraction=0.046)
        ax.scatter(kept["x"], kept["y"], s=np.clip(60 - 3 * kept["Tmag"], 4, 50), facecolors="none", edgecolors="w", lw=0.7)
        ax.scatter([me["x"]], [me["y"]], marker="x", c="r", s=40, label="TIC target")
        ax.scatter([true["x"]], [true["y"]], marker="o", s=140, facecolors="none", edgecolors="m", lw=1.5, label="injected source")
        ax.set_xlim(-0.5, flux.shape[2] - 0.5)
        ax.set_ylim(-0.5, flux.shape[1] - 0.5)
    axes[0].legend(fontsize=7, loc="upper right")
    fig.suptitle(f"TIC {int(tpf.targetid)} ({label}), sector {tpf.sector}, smoke injection depth {SMOKE_DEPTH:.0%}; "
                 f"{len(kept)} candidates shown (white circles)", fontsize=9)
    fig.tight_layout()
    path = OUT / f"phase1_diff_tic{int(tpf.targetid)}.png"
    fig.savefig(path, dpi=110)
    plt.close(fig)
    row["figure"] = path.name
    return row, tpf


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, (label, hit) in enumerate(pick_targets()):
        row, _ = one_target(i, label, hit)
        rows.append(row)
        print(f"done TIC {row['tic_id']} ({label})", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "phase1_summary.csv", index=False)
    pd.set_option("display.width", 250, "display.max_columns", 50)
    print(df.T.to_string())


if __name__ == "__main__":
    main()
