#!/usr/bin/env python3
"""
固定リグレッション: Path D SEISF デコード (vkg.1 ↔ vkg.47)

PASS 条件（データが ../utig/ にあるとき）:
  1. 金フレーム f0: GCSC=125078, science 2048/2048, VUS 450B 完全一致
  2. Path D 定数: Q=matv, bit_offset=15
  3. レコード0の VUS ヘッダ一致フレーム: すべて 2048/2048（先読み込み）
  4. VUS 単独: vkg.47 先頭が NORMAL / n=83

実行:
  cd src/
  python3 test_regression.py
  python3 -m unittest test_regression -v

終了コード 0 = すべて OK、1 = 失敗またはデータ欠落。
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from seisf_decode import (  # noqa: E402
    _PAIR36_BIT_OFFSET,
    _PAIR36_DROP,
    decode_seisf_file,
    estimate_q_from_matv,
    extend_halfwords_across_records,
    find_seisf_frame_bases,
    halfwords_span_for_frame,
    map_unscramble_data_bits,
    seisf_frame_header_bytes,
    seisf_frame_to_vus_bytes,
)
from vkg_format import body_to_halfwords, open_vkg  # noqa: E402
from vus_decode import (  # noqa: E402
    decode_vus_file,
    decode_vus_frame,
    get_int_from_bit_stream,
    make_bit_stream,
)

VKG1 = ROOT / "utig" / "vkg.1"
VKG47 = ROOT / "utig" / "vkg.47"

GOLD_GCSC = 125078
GOLD_MATV = 423
GOLD_FRAME_BASE = 170
GOLD_YEAR, GOLD_DOY = 1976, 249
GOLD_X0 = [0, 119, 38, 14, 6, 3]
GOLD_Y0 = [-1, 79, 25, 9, 4, 2]
GOLD_Z0 = [-84, 54, 18, 6, 3, 2]


def _data_available() -> bool:
    return VKG1.is_file() and VKG47.is_file()


@unittest.skipUnless(_data_available(), f"missing {VKG1.name} and/or {VKG47.name} under utig/")
class TestPathDRegression(unittest.TestCase):
    """Path D の固定アサート一式。"""

    @classmethod
    def setUpClass(cls) -> None:
        _, sgs1 = open_vkg(str(VKG1))
        h0, body0 = sgs1[0]
        rlen = h0.record_length
        cls.records: list[list[int]] = []
        pos = 0
        while pos + rlen <= len(body0):
            cls.records.append(body_to_halfwords(body0[pos : pos + rlen]))
            pos += rlen
        assert cls.records, "vkg.1 subgroup0 has no records"

        # VUS index: first 108 bytes of each 450B frame
        cls.vus: dict[bytes, bytes] = {}
        _, sgs47 = open_vkg(str(VKG47))
        for h, body in sgs47:
            rlen = h.record_length
            p = 0
            while p + rlen <= len(body):
                rec = body[p : p + rlen]
                p += rlen
                for j in range(0, rlen, 450):
                    if j + 450 > len(rec):
                        break
                    fr = bytes(rec[j : j + 450])
                    cls.vus[fr[:108]] = fr

        cls.v_frame0 = open_vkg(str(VKG47))[1][0][1][:450]
        cls.v_bits0 = make_bit_stream(cls.v_frame0)[648 : 648 + 2048]
        cls.v_dec0 = decode_vus_frame(cls.v_frame0, 0)
        assert cls.v_dec0 and cls.v_dec0.blocks

    def _hs_for(self, record_index: int, frame_base: int) -> list[int]:
        need = halfwords_span_for_frame(frame_base)
        hs0 = self.records[record_index]
        if len(hs0) >= need:
            return list(hs0)
        return extend_halfwords_across_records(self.records, record_index, need)

    # ----- constants -----

    def test_path_d_constants(self) -> None:
        self.assertEqual(_PAIR36_BIT_OFFSET, 15)
        self.assertEqual(_PAIR36_DROP, (0, 1, 2, 3))

    # ----- gold frame -----

    def test_gold_frame_base_and_matv(self) -> None:
        hs = self._hs_for(0, GOLD_FRAME_BASE)
        bases = find_seisf_frame_bases(self.records[0])
        self.assertEqual(bases[0], GOLD_FRAME_BASE)
        q, matv = estimate_q_from_matv(hs, GOLD_FRAME_BASE)
        self.assertEqual(matv, GOLD_MATV)
        self.assertEqual(q, GOLD_MATV)  # Q = matv

    def test_gold_science_bits_perfect(self) -> None:
        hs = self._hs_for(0, GOLD_FRAME_BASE)
        bits = map_unscramble_data_bits(hs, GOLD_FRAME_BASE)
        self.assertEqual(len(bits), 2048)
        mism = sum(1 for a, b in zip(bits, self.v_bits0) if a != b)
        self.assertEqual(mism, 0, f"science residual bits: {mism}")
        gcsc = get_int_from_bit_stream(bits, 0, 23) << 1
        self.assertEqual(gcsc, GOLD_GCSC)

    def test_gold_frame_bytes_equal_vus(self) -> None:
        hs = self._hs_for(0, GOLD_FRAME_BASE)
        frame = seisf_frame_to_vus_bytes(hs, GOLD_FRAME_BASE)
        self.assertEqual(frame, self.v_frame0)
        dec = decode_vus_frame(frame, 0)
        self.assertIsNotNone(dec)
        assert dec and dec.blocks
        bl = dec.blocks[0]
        self.assertEqual(bl.gcsc, GOLD_GCSC)
        self.assertEqual(bl.cs.mode_name, "NORMAL")
        self.assertEqual(bl.ndata, 83)
        self.assertEqual(list(bl.amp[0][:6]), GOLD_X0)
        self.assertEqual(list(bl.amp[1][:6]), GOLD_Y0)
        self.assertEqual(list(bl.amp[2][:6]), GOLD_Z0)
        self.assertEqual(dec.year, GOLD_YEAR)
        self.assertEqual(dec.doy, GOLD_DOY)

    def test_decode_seisf_file_first_frame(self) -> None:
        it = decode_seisf_file(str(VKG1), max_frames=1)
        dec = next(it)
        self.assertEqual(dec.year, GOLD_YEAR)
        self.assertEqual(dec.doy, GOLD_DOY)
        self.assertTrue(dec.blocks)
        self.assertEqual(dec.blocks[0].gcsc, GOLD_GCSC)
        self.assertEqual(list(dec.blocks[0].amp[0][:6]), GOLD_X0)

    # ----- multi-frame record 0 -----

    def test_record0_header_matched_frames_bit_perfect(self) -> None:
        """vkg.1 レコード0 と vkg.47 で 108B ヘッダ一致する全フレーム。"""
        matched = 0
        imperfect: list[tuple[int, int, int]] = []
        for base in find_seisf_frame_bases(self.records[0]):
            hs = self._hs_for(0, base)
            hdr = bytes(seisf_frame_header_bytes(hs, base))
            if hdr not in self.vus:
                continue
            fr = self.vus[hdr]
            q, matv = estimate_q_from_matv(hs, base)
            if not (0 < matv < 503):
                continue  # Path D 対象外（偽フレーム / QEQ503）
            bits = map_unscramble_data_bits(hs, base)
            vb = make_bit_stream(fr)[648 : 648 + 2048]
            mism = sum(1 for a, b in zip(bits, vb) if a != b)
            matched += 1
            if mism != 0:
                imperfect.append((base, mism, matv))
            frame = seisf_frame_to_vus_bytes(hs, base)
            self.assertEqual(
                frame,
                fr,
                f"frame_eq failed base={base} mism_bits={mism}",
            )
        self.assertGreaterEqual(
            matched, 12, f"expected ≥12 header-matched Path-D frames, got {matched}"
        )
        self.assertEqual(
            imperfect,
            [],
            f"non-perfect frames (base, mism, matv): {imperfect}",
        )

    def test_record_boundary_frame_3530(self) -> None:
        """レコード末尾 base=3530 は先読みで 2048 一致すること。"""
        base = 3530
        self.assertIn(base, find_seisf_frame_bases(self.records[0]))
        # without extend: too few science halfwords
        short = self.records[0]
        self.assertLess(len(short), halfwords_span_for_frame(base))
        hs = self._hs_for(0, base)
        self.assertGreaterEqual(len(hs), halfwords_span_for_frame(base))
        hdr = bytes(seisf_frame_header_bytes(hs, base))
        self.assertIn(hdr, self.vus)
        fr = self.vus[hdr]
        bits = map_unscramble_data_bits(hs, base)
        vb = make_bit_stream(fr)[648 : 648 + 2048]
        mism = sum(1 for a, b in zip(bits, vb) if a != b)
        self.assertEqual(mism, 0)
        self.assertEqual(seisf_frame_to_vus_bytes(hs, base), fr)

    # ----- matv == 503 and matv > 503 (PD7400072 Q==503 identity / Q>503) -----

    def test_matv_gt_503_bit_perfect(self) -> None:
        """PD7400072 "Q > 503" 読み出し式: レコード1 base=1962 は matv=508。"""
        ri, base = 1, 1962
        hs = self._hs_for(ri, base)
        hdr = bytes(seisf_frame_header_bytes(hs, base))
        self.assertIn(hdr, self.vus, "expected header-matched fixture pair")
        fr = self.vus[hdr]
        q, matv = estimate_q_from_matv(hs, base)
        self.assertEqual(matv, 508)
        self.assertEqual(q, 508)  # Q == matv, no more clamp-to-502
        bits = map_unscramble_data_bits(hs, base)
        vb = make_bit_stream(fr)[648 : 648 + 2048]
        mism = sum(1 for a, b in zip(bits, vb) if a != b)
        self.assertEqual(mism, 0, f"Q>503 science residual bits: {mism}")
        self.assertEqual(seisf_frame_to_vus_bytes(hs, base), fr)

    def test_matv_eq_503_identity_bit_perfect(self) -> None:
        """PD7400072 "Q == 503" 恒等読み出し: レコード6 base=1514 は matv=503。"""
        ri, base = 6, 1514
        hs = self._hs_for(ri, base)
        hdr = bytes(seisf_frame_header_bytes(hs, base))
        self.assertIn(hdr, self.vus, "expected header-matched fixture pair")
        fr = self.vus[hdr]
        q, matv = estimate_q_from_matv(hs, base)
        self.assertEqual(matv, 503)
        self.assertEqual(q, 503)
        bits = map_unscramble_data_bits(hs, base)
        vb = make_bit_stream(fr)[648 : 648 + 2048]
        mism = sum(1 for a, b in zip(bits, vb) if a != b)
        self.assertEqual(mism, 0, f"Q==503 science residual bits: {mism}")
        self.assertEqual(seisf_frame_to_vus_bytes(hs, base), fr)

    # ----- VUS smoke -----

    def test_long_run_no_crash(self) -> None:
        """Regression: decode past former IndexError around frame ~1500."""
        n = 0
        for dec in decode_seisf_file(str(VKG1), max_frames=1600):
            n += 1
            self.assertIsInstance(dec.year, int)
            self.assertIsInstance(dec.blocks, list)
            for bl in dec.blocks:
                # amp channels same length; no past-end samples
                self.assertEqual(len(bl.amp[0]), len(bl.amp[1]))
                self.assertEqual(len(bl.amp[0]), len(bl.amp[2]))
        self.assertEqual(n, 1600)


def main() -> int:
    if not _data_available():
        print(f"FAIL: need {VKG1} and {VKG47}", file=sys.stderr)
        return 1
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPathDRegression)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        print("\nALL REGRESSION CHECKS PASSED")
        return 0
    print("\nREGRESSION FAILED", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
