"""v2: ingesting team-collected real Hindi/Hinglish messages."""
import pandas as pd

from ml_training.datasets.scamguard_in_2026 import add_real_indic as ari


def test_ingest_masks_dedups_protects_frozen_test_and_splits_by_group(tmp_path, monkeypatch):
    out = tmp_path / "collected.csv"
    monkeypatch.setattr(ari, "OUT", str(out))
    frozen = pd.read_csv(ari.FROZEN).text.iloc[0]
    rows = [
        {"text": "Aapka bijli connection aaj raat kat jayega, turant 9876543210 pe call karein", "label": "Scam"},
        {"text": "Aapka bijli connection aaj raat kat jayega, turant 9123456780 pe call karein", "label": "scam"},   # differs only in numbers: duplicate
        {"text": "Aapka bijli connection aaj raat 10 baje kat jayega, abhi 9123456780 pe call karein", "label": "scam"},  # near-duplicate: same group
        {"text": "Aapka bijli connection aaj raat kat jayega, turant 9876543210 pe call karein", "label": "scam"},   # exact dup
        {"text": "बैंक से आपके खाते XX1234 में 5000 रुपये जमा हुए", "label": "genuine"},
        {"text": "Mummy main 7 baje tak ghar aa jaunga, khana bana ke rakhna", "label": "ham"},
        {"text": "KBC lottery me aapka number select hua, 25 lakh jeete, GST 5000 bhejo", "label": "1"},
        {"text": frozen, "label": "scam"},                                                    # in the frozen test set
        {"text": "short", "label": "scam"},                                                    # too short
        {"text": "Kal milte hain college me, notes le aana please", "label": "maybe"},          # no usable label
    ]
    src = tmp_path / "in.csv"
    pd.DataFrame(rows).to_csv(src, index=False)
    assert ari.main([str(src)]) == 0
    d = pd.read_csv(out)
    assert len(d) == 5, d.text.tolist()
    assert not d.text.str.contains("9876543210").any()            # phone number replaced
    assert frozen not in set(d.text)
    assert set(d.label) == {"scam", "legitimate"}
    assert d.groupby("group").split.nunique().max() == 1          # a group never straddles train and test
    assert (d.text.str.contains("bijli")).sum() == 2 and d[d.text.str.contains("bijli")].group.nunique() == 1
    # running again with the same file adds nothing
    assert ari.main([str(src)]) == 0
    assert len(pd.read_csv(out)) == 5
