import pytest

import build_dataset


class FlakyHit:
    """download() fails the first `fails` times, like Lightkurve reading a truncated cached file."""

    def __init__(self, raw, tic, fails):
        self.raw, self.tic, self.fails, self.calls = raw, tic, fails, 0

    def download(self, download_dir):
        self.calls += 1
        path = self.raw / "mastDownload" / "TESS" / f"obs_{self.tic}" / f"tess-{self.tic:016d}-s_tp.fits"
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.calls <= self.fails:
            path.write_bytes(b"x" * 65536)  # truncated file left in the cache
            raise RuntimeError("buffer is too small for requested array")
        assert not path.exists() or path.stat().st_size != 65536, "corrupt file was not removed before retry"
        return "tpf"


@pytest.fixture
def raw(tmp_path, monkeypatch):
    monkeypatch.setattr(build_dataset, "RAW", tmp_path)
    monkeypatch.setattr(build_dataset.time, "sleep", lambda s: None)
    return tmp_path


def test_fetch_tpf_deletes_corrupt_cache_and_retries(raw):
    hit = FlakyHit(raw, 123, fails=2)
    assert build_dataset.fetch_tpf(hit, 123) == "tpf"
    assert hit.calls == 3
    assert not list(raw.glob("**/*_tp.fits"))


def test_fetch_tpf_gives_up_after_three_tries(raw):
    hit = FlakyHit(raw, 123, fails=10)
    with pytest.raises(RuntimeError):
        build_dataset.fetch_tpf(hit, 123)
    assert hit.calls == 3
