"""Phase 2 build: per-target processing, then merge into train/val/cal/test npz plus meta.json.

Run from the repo root:
  python track2_real/src/build_dataset.py [--limit N] [--merge-only]
Needs data/interim/selected_targets.csv from pool.py. Raw TPFs are cached in data/raw (git-ignored),
per-target shards in data/processed/shards, merged files in data/processed. Reruns skip finished targets.
Candidate stars come from the TIC (Gaia-derived). Proper motion is ignored.
"""
import argparse
import datetime
import itertools
import json
import shutil
import sys
import threading
import time
import traceback
import warnings
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", message=".*tpfmodel.*")
import astropy  # noqa: E402
import lightkurve as lk  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
import config  # noqa: E402
from conformal import assign_crowd_bins, crowd_bin_edges  # noqa: E402
from dataset import generate_samples, null_kappa, pack_target, pixel_noise, prepare_cube  # noqa: E402
from tic import cone_radius_arcsec, query_tic_cone, select_candidates, with_retries  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
SHARDS = PROCESSED / "shards"
OUT = ROOT / "track2_real" / "outputs"
ARRAY_KEYS = ["X", "star_xy", "star_tmag", "star_mask", "y", "crowd", "snr", "depth_ppm", "tic_id", "injected",
              "sector", "star_tic", "period_d", "duration_h"]


class DiskLow(RuntimeError):
    pass


_counter = itertools.count(1)
_log_lock = threading.Lock()


def log(msg):
    """Progress goes to a file, not sys.stdout: some library code swaps sys.stdout from worker threads and can
    leave it closed, which killed the previous runs' prints."""
    with _log_lock, open(INTERIM / "build_progress.log", "a") as f:
        f.write(msg + "\n")


def fetch_tpf(hit, tic, tries=3):
    """Download one TPF. MAST sometimes returns a truncated file that Lightkurve then caches and reuses,
    so on a read failure the cached file is deleted and the download is tried again."""
    last = None
    for attempt in range(tries):
        try:
            tpf = hit.download(download_dir=str(RAW))
            if tpf is None:
                raise LookupError("download returned None")
            return tpf
        except DiskLow:
            raise
        except Exception as e:
            last = e
            for f in RAW.glob(f"**/*{tic:016d}*_tp.fits"):
                f.unlink()
            time.sleep(5 * (attempt + 1))
    raise last


def free_gb():
    return shutil.disk_usage(ROOT).free / 1e9


def process_target(row):
    """Download one TPF, build candidates and samples, write a shard. Returns an info dict."""
    tic, sector = int(row["tic_id"]), int(row["sector"])
    tag = f"{tic}_{sector}"
    done = SHARDS / f"{tag}.json"
    if done.exists():
        old = json.loads(done.read_text())
        if old["status"] != "error":
            return old
    info = dict(tic_id=tic, sector=sector, field=row["field"], status="error", n_samples=0)
    try:
        if free_gb() < config.MIN_FREE_GB:
            raise DiskLow(f"only {free_gb():.1f} GB free")
        res = with_retries(lambda: lk.search_targetpixelfile(
            f"TIC {tic}", mission="TESS", author="SPOC", exptime=120, sector=sector))
        if len(res) == 0:
            raise LookupError("no SPOC 2-minute TPF found")
        tpf = fetch_tpf(res[0], tic)
        flux_raw, time_ = tpf.flux.value, tpf.time.value
        h, w = flux_raw.shape[1:]
        info.update(tpf_shape=f"{h}x{w}", n_cadences=int(flux_raw.shape[0]), camera=int(tpf.camera), ccd=int(tpf.ccd),
                    ra=float(tpf.ra), dec=float(tpf.dec))

        cat = query_tic_cone(tpf.ra, tpf.dec, cone_radius_arcsec())
        x, y = tpf.wcs.all_world2pix(cat["ra"].to_numpy(), cat["dec"].to_numpy(), 0)
        cat["x"], cat["y"] = x, y
        me = cat[cat["ID"] == str(tic)]
        if me.empty:
            raise KeyError("target not in TIC cone rows")
        tx, ty = float(me["x"].iloc[0]), float(me["y"].iloc[0])
        cat["d"] = np.hypot(cat["x"] - tx, cat["y"] - ty)
        inside = (cat["x"] >= -0.5) & (cat["x"] <= w - 0.5) & (cat["y"] >= -0.5) & (cat["y"] <= h - 0.5)
        kept, cinfo = select_candidates(cat[inside | (cat["ID"] == str(tic))], tic)
        info.update(target_x=tx, target_y=ty, **{k: cinfo[k] for k in ("n_candidates", "n_kept", "crowd", "flux_lost",
                                                                          "target_tmag")})

        flux, fin, valid = prepare_cube(flux_raw)
        info.update(n_finite_cadences=int(fin.sum()), n_bad_pixels=int((~valid).sum()))
        if fin.sum() < 1000:
            raise ValueError("fewer than 1000 finite cadences")
        sigma = pixel_noise(flux, fin)
        rng = np.random.default_rng(tic)
        kappa = null_kappa(flux, time_, (tx, ty), rng)
        info["kappa"] = kappa
        if not np.isfinite(kappa):
            raise ValueError("null kappa not measurable (too few usable transit windows)")
        samples, n_failed = generate_samples(flux, time_, fin, sigma, kappa, kept[["x", "y"]].to_numpy(),
                                             kept["Tmag"].to_numpy(), rng, config.SAMPLES_PER_TARGET)
        info.update(n_samples=len(samples), n_draw_failed=n_failed, status="ok" if samples else "no_samples")
        if samples:
            packed = pack_target(samples, kept, (tx, ty), tic, sector, cinfo["crowd"])
            SHARDS.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(SHARDS / f"{tag}.npz", **packed)
    except DiskLow:
        raise
    except Exception as e:
        info["error"] = f"{type(e).__name__}: {e}"[:200]
        info["status"] = "error"
    SHARDS.mkdir(parents=True, exist_ok=True)
    done.write_text(json.dumps(info))
    log(f"[{next(_counter)}] TIC {tic} {info['status']} n={info['n_samples']} crowd={info.get('crowd', float('nan')):.3f} "
          f"kappa={info.get('kappa', float('nan')):.2f} {info.get('error', '')[:90]} (free {free_gb():.0f} GB)")
    return info


def run(limit):
    sel = pd.read_csv(INTERIM / "selected_targets.csv")
    if limit:
        sel = sel.sample(n=limit, random_state=0) if limit < len(sel) else sel
    rows = sel.to_dict("records")
    n_ok = 0
    with ThreadPoolExecutor(config.WORKERS) as ex:
        futs = [ex.submit(process_target, r) for r in rows]
        for fut in futs:
            try:
                n_ok += fut.result()["status"] == "ok"
            except DiskLow as e:
                log(f"STOP: {e}")
                for f in futs:
                    f.cancel()
                break
    log(f"finished: {n_ok} ok of {len(rows)}")


def clusters_by_separation(ra, dec, arcmin):
    """Connected components of targets closer than `arcmin`, so overlapping cutouts never straddle splits."""
    r, d = np.radians(ra), np.radians(dec)
    cosine = np.sin(d)[:, None] * np.sin(d) + np.cos(d)[:, None] * np.cos(d) * np.cos(r[:, None] - r)
    close = np.degrees(np.arccos(np.clip(cosine, -1, 1))) * 60.0 <= arcmin
    label = np.arange(len(ra))
    for i in range(len(ra)):
        for j in np.flatnonzero(close[i]):
            a, b = label[i], label[j]
            if a != b:
                label[label == b] = a
    return label


def assign_splits(cluster, seed=config.SPLIT_SEED):
    """Cluster-level split: shuffle clusters, give each to the split furthest below its target share."""
    rng = np.random.default_rng(seed)
    ids, sizes = np.unique(cluster, return_counts=True)
    order = rng.permutation(len(ids))
    total, count, out = sizes.sum(), {k: 0 for k in config.SPLIT_FRACTIONS}, {}
    for k in order:
        deficit = {s: f * total - count[s] for s, f in config.SPLIT_FRACTIONS.items()}
        pick = max(deficit, key=deficit.get)
        out[ids[k]] = pick
        count[pick] += sizes[k]
    return out


def merge():
    infos = pd.DataFrame([json.loads(p.read_text()) for p in sorted(SHARDS.glob("*.json"))])
    chosen = pd.read_csv(INTERIM / "selected_targets.csv")  # shards from other runs (dry runs) are left out
    infos = infos[infos["tic_id"].isin(chosen["tic_id"])].reset_index(drop=True)
    ok = infos[infos["n_samples"] > 0].reset_index(drop=True)
    ok["cluster"] = clusters_by_separation(ok["ra"].to_numpy(), ok["dec"].to_numpy(), config.CLUSTER_ARCMIN)
    split_of_cluster = assign_splits(ok["cluster"].to_numpy())
    ok["split"] = ok["cluster"].map(split_of_cluster)

    parts = {k: [] for k in ARRAY_KEYS}
    for _, r in ok.iterrows():
        with np.load(SHARDS / f"{r['tic_id']}_{r['sector']}.npz") as z:
            for k in ARRAY_KEYS:
                parts[k].append(z[k])
    arr = {k: np.concatenate(v) for k, v in parts.items()}
    split_sample = pd.Series(arr["tic_id"]).map(dict(zip(ok["tic_id"], ok["split"]))).to_numpy()

    PROCESSED.mkdir(parents=True, exist_ok=True)
    for s in config.SPLIT_FRACTIONS:
        sel = split_sample == s
        np.savez_compressed(PROCESSED / f"{s}.npz", **{k: v[sel] for k, v in arr.items()})
    edges = crowd_bin_edges(arr["crowd"][split_sample == "cal"])
    bins = assign_crowd_bins(arr["crowd"], edges)

    table = pd.DataFrame({"split": split_sample, "bin": bins, "tic": arr["tic_id"]})
    counts = {s: {"samples": int((split_sample == s).sum()),
                  "targets": int(ok[ok["split"] == s].shape[0]),
                  "samples_per_bin": [int(((split_sample == s) & (bins == b)).sum()) for b in range(3)],
                  "targets_per_bin": [int(table[(table["split"] == s) & (table["bin"] == b)]["tic"].nunique())
                                      for b in range(3)]} for s in config.SPLIT_FRACTIONS}
    meta = dict(
        schema_version=1, created=datetime.date.today().isoformat(),
        params={k: getattr(config, k) for k in dir(config) if k.isupper()},
        n_targets_attempted=int(len(infos)), n_targets_with_samples=int(len(ok)),
        n_targets_no_samples=int((infos["status"] == "no_samples").sum()),
        n_targets_error=int((infos["status"] == "error").sum()),
        errors=Counter(infos[infos["status"] == "error"].get("error", pd.Series(dtype=str)).astype(str).str[:60]),
        tpf_shapes=Counter(infos["tpf_shape"].dropna()), n_samples=int(len(arr["y"])),
        crowd_edges_cal=[float(e) for e in edges], crowd_bin_note="bin 0 = lowest crowding value = most crowded",
        counts=counts, split_tic_ids={s: sorted(map(int, ok[ok["split"] == s]["tic_id"])) for s in config.SPLIT_FRACTIONS},
        versions=dict(numpy=np.__version__, astropy=astropy.__version__, lightkurve=lk.__version__),
        approximations=["Gaussian PSF sigma=%.1f px for injection (not the real TESS PSF)" % config.SIGMA_PIX,
                        "box transit, no ingress or egress",
                        "flux zero point 15000 e-/s at Tmag 10",
                        "proper motion ignored when placing TIC stars on the TPF",
                        "SNR is white-noise matched-filter SNR divided by kappa (null z spread)"],
    )
    (PROCESSED / "meta.json").write_text(json.dumps(meta, indent=2, default=str))

    OUT.mkdir(parents=True, exist_ok=True)
    infos = infos.merge(ok[["tic_id", "cluster", "split"]], on="tic_id", how="left")
    cols = ["tic_id", "sector", "field", "tpf_shape", "n_cadences", "target_tmag", "target_x", "target_y", "n_candidates",
            "n_kept", "crowd", "flux_lost", "kappa", "n_samples", "n_draw_failed", "cluster", "split", "status", "error"]
    infos.reindex(columns=cols).round(5).to_csv(OUT / "targets_phase2.csv", index=False)
    figure(ok, arr, bins, edges, split_sample)
    return meta, infos


def figure(ok, arr, bins, edges, split_sample):
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    order = list(config.SPLIT_FRACTIONS)
    ax[0].hist([ok[ok["split"] == s]["crowd"] for s in order], bins=np.linspace(0, 1, 26), stacked=True, label=order)
    for e in edges:
        ax[0].axvline(e, c="k", ls="--", lw=0.8)
    ax[0].set(xlabel="crowding (target flux / kept flux), lower is more crowded", ylabel="targets",
              title="Per-target crowding; dashed = tercile cuts from cal set")
    ax[0].legend(fontsize=8)
    for b, name in enumerate(["bin 0 (most crowded)", "bin 1", "bin 2 (least crowded)"]):
        ax[1].hist(arr["snr"][bins == b], bins=np.geomspace(5, 40, 20), alpha=0.5, label=name)
    ax[1].set(xscale="log", xlabel="injected SNR (kappa-corrected)", ylabel="samples", title="Injected SNR by crowding bin")
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "phase2_crowding_hist.png", dpi=110)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--merge-only", action="store_true")
    args = ap.parse_args()
    if not args.merge_only:
        run(args.limit)
    try:
        meta, _ = merge()
    except Exception:
        traceback.print_exc()
        return
    print(json.dumps({k: meta[k] for k in ("n_targets_attempted", "n_targets_with_samples", "n_targets_no_samples",
                                           "n_targets_error", "n_samples", "crowd_edges_cal", "counts")}, indent=1), file=sys.__stdout__)


if __name__ == "__main__":
    main()
