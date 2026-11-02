"""TIC cone queries and candidate-star selection (TIC, Gaia-derived). Proper motion is ignored."""
import time

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord
from astroquery.mast import Catalogs

from config import MAX_PIX, N_STARS, PIX_ARCSEC, TMAG_CUT
from pixels import star_flux_e_per_s


def with_retries(fn, tries=4, base=3.0):
    """Call fn(), retrying with exponential backoff. The last error is re-raised."""
    for i in range(tries):
        try:
            return fn()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(base * 2**i)


def query_tic_cone(ra_deg, dec_deg, radius_arcsec):
    """TIC rows around a position. The ID column is returned as str (astroquery gives a string column)."""
    centre = SkyCoord(ra_deg * u.deg, dec_deg * u.deg)
    cat = with_retries(lambda: Catalogs.query_region(centre, radius=radius_arcsec * u.arcsec, catalog="Tic"))
    cat = cat.to_pandas()
    cat["ID"] = cat["ID"].astype(str)
    return cat


def cone_radius_arcsec():
    return (MAX_PIX + 1.0) * PIX_ARCSEC


def select_candidates(cat, target_id, n_stars=N_STARS, tmag_cut=TMAG_CUT, max_pix=MAX_PIX):
    """Kept candidate stars for one target (D12), plus crowding and truncation numbers.

    `cat` needs columns ID, objType, disposition, Tmag, x, y and d, where d is the distance
    to the target in pixels. Rules: real stars only, DUPLICATE rows dropped, within max_pix,
    Tmag <= tmag_cut, brightest n_stars - 1 of those, and the target is always kept.
    The kept set is sorted by Tmag (ties by ID).
    crowding = target flux / sum of kept fluxes (label-free, so it can define Mondrian bins).
    flux_lost = fraction of the flux of all candidates within max_pix that the kept set leaves out.
    Raises KeyError if the target row is missing, ValueError if its Tmag is not finite.
    """
    target_id = str(target_id)
    me = cat[cat["ID"] == target_id]
    if me.empty:
        raise KeyError(f"target {target_id} not in catalog rows")
    if not np.isfinite(me["Tmag"].iloc[0]):
        raise ValueError(f"target {target_id} has no Tmag")
    is_target = cat["ID"] == target_id
    real = (cat["objType"] == "STAR") & (cat["disposition"] != "DUPLICATE") & cat["Tmag"].notna()
    base = cat[(real | is_target) & (cat["d"] <= max_pix)]
    others = base[(base["ID"] != target_id) & (base["Tmag"] <= tmag_cut)].sort_values(["Tmag", "ID"]).head(n_stars - 1)
    kept = pd.concat([base[base["ID"] == target_id], others]).sort_values(["Tmag", "ID"]).reset_index(drop=True)
    flux = star_flux_e_per_s(kept["Tmag"].to_numpy())
    target_flux = float(star_flux_e_per_s(me["Tmag"].iloc[0]))
    all_flux = float(star_flux_e_per_s(base["Tmag"].to_numpy()).sum())
    info = dict(
        n_candidates=len(base), n_kept=len(kept), crowd=target_flux / float(flux.sum()),
        flux_lost=1.0 - float(flux.sum()) / all_flux, target_tmag=float(me["Tmag"].iloc[0]),
    )
    return kept, info
