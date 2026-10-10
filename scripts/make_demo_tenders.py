"""Writes the sample tender PDFs in data/tenders/ (fictional buyers, clearly marked as samples).

Run from the project folder:  backend/.venv/bin/python scripts/make_demo_tenders.py
"""
import json
import textwrap
from pathlib import Path

import pymupdf

OUT = Path(__file__).resolve().parents[1] / "data" / "tenders"
BANNER = "SAMPLE TENDER - written for the TenderSathi demo. The buyer is fictional. Not a real tender."

COMMON_TERMS = [
    "9. General conditions",
    "Bids must be submitted online on the e-procurement portal before the deadline. Late, emailed or "
    "physical bids will not be accepted. The buyer may accept or reject any bid without giving reasons.",
    "10. Integrity",
    "The bidder shall not offer any gift or inducement to any officer of the buyer. Bids found to be "
    "submitted by related firms acting together will be rejected.",
]

TENDERS = {
    "school_desks.pdf": {
        "title": "Supply of 200 dual school desks",
        "lines": [
            "PERIYAR DISTRICT SCHOOLS BOARD (fictional)",
            "Notice Inviting Tender No. PDSB/FUR/2026/14",
            "1. Scope of work",
            "Supply of 200 dual-seater wooden school desks with attached benches for government primary "
            "schools in Periyar district, as per the specification in clause 2.",
            "2. Specification",
            "Each desk shall be made of seasoned hardwood (teak or rosewood) with a top of 1200 mm x 450 mm, "
            "height 700 mm, finished with two coats of polyurethane varnish. Edges shall be rounded. "
            "Steel fittings shall be powder coated.",
            "3. Important dates",
            "Last date and time for bid submission: 30 October 2026, 3:00 PM. Technical bids will be opened on "
            "31 October 2026 at 11:00 AM.",
            "4. Eligibility criteria",
            "4.1 Average annual turnover of the bidder in the last three financial years shall be at least "
            "Rs. 60 lakh. Mandatory. Audited balance sheets must be enclosed.",
            "4.2 The bidder shall have completed at least one order for supply of school or office furniture "
            "of value not less than Rs. 6 lakh in the last three years. Mandatory. Copy of purchase order and "
            "completion certificate to be enclosed.",
            "4.3 The bidder shall hold a valid GST registration. Mandatory.",
            "4.4 ISO 9001 quality management certification. Desirable, not mandatory.",
            "5. Documents to be submitted",
            "GST registration certificate; PAN card; Udyam registration certificate (for MSE benefits); audited "
            "balance sheets for the last three financial years; purchase order and completion certificate of a "
            "similar supply; ISO 9001 certificate (if held).",
            "6. Earnest money deposit (EMD)",
            "EMD of Rs. 50,000 shall be paid online. Micro and small enterprises registered under Udyam are "
            "exempt from paying EMD on submission of a valid Udyam certificate.",
            "7. Payment terms",
            "100% payment within 30 days of delivery and acceptance of the full quantity by the inspection "
            "committee. No advance payment will be made.",
            "8. Delivery",
            "Delivery to the schools listed in Annexure A within 60 days from the date of the supply order. "
            "Late delivery attracts liquidated damages of 0.5% per week, up to 10% of the order value.",
            *COMMON_TERMS,
        ],
    },
    "hospital_beds.pdf": {
        "title": "Supply of 150 semi-fowler hospital beds",
        "lines": [
            "VEMBANAD HEALTH SERVICES SOCIETY (fictional)",
            "Notice Inviting Tender No. VHSS/EQP/2026/08",
            "1. Scope of work",
            "Supply of 150 semi-fowler hospital beds with mattresses and side rails for the society's "
            "district hospitals.",
            "2. Specification",
            "Mild steel frame with epoxy powder coating, mechanically adjustable backrest, ABS head and foot "
            "panels, four castor wheels with brakes, and a 100 mm foam mattress with a washable cover.",
            "3. Important dates",
            "Last date and time for bid submission: 12 November 2026, 5:00 PM.",
            "4. Eligibility criteria",
            "4.1 Average annual turnover of the bidder in the last three financial years shall be at least "
            "Rs. 5 crore. Mandatory.",
            "4.2 The bidder shall have supplied hospital furniture in at least three orders of value not less "
            "than Rs. 50 lakh each in the last five years. Mandatory.",
            "4.3 The product shall carry BIS certification under IS 16900. Mandatory.",
            "5. Documents to be submitted",
            "GST registration certificate; PAN card; audited balance sheets for three years; purchase orders "
            "for hospital furniture; BIS licence.",
            "6. Earnest money deposit (EMD)",
            "EMD of Rs. 3,00,000 by bank guarantee valid for 180 days.",
            "7. Payment terms",
            "90% payment within 45 days of delivery and installation; balance 10% after the warranty period "
            "of 12 months.",
            "8. Delivery",
            "Delivery and installation within 45 days of the supply order.",
            *COMMON_TERMS,
        ],
    },
    "office_workstations.pdf": {
        "title": "Supply and installation of 40 office workstations",
        "lines": [
            "THEKKADY RURAL DEVELOPMENT AGENCY (fictional)",
            "Notice Inviting Tender No. TRDA/ADM/2026/21",
            "1. Scope of work",
            "Supply and installation of 40 modular office workstations with storage pedestals at the "
            "agency's new block office.",
            "2. Specification",
            "Workstation tops of 25 mm prelaminated particle board with PVC edge banding, 1200 mm x 600 mm, "
            "with a fabric-covered partition of 1050 mm height and a three-drawer mobile pedestal.",
            "3. Important dates",
            "Last date and time for bid submission: 6 November 2026, 2:00 PM.",
            "4. Eligibility criteria",
            "4.1 Average annual turnover of the bidder in the last three financial years shall be at least "
            "Rs. 1 crore. Mandatory.",
            "4.2 The bidder shall have completed at least one order for office workstations or modular "
            "furniture of value not less than Rs. 10 lakh in the last three years. Mandatory.",
            "4.3 The bidder shall be registered as a micro or small enterprise under Udyam. Mandatory "
            "(this tender is reserved for MSEs).",
            "5. Documents to be submitted",
            "GST registration certificate; PAN card; Udyam registration certificate; audited balance sheets "
            "for three years; purchase order and completion certificate of a similar work.",
            "6. Earnest money deposit (EMD)",
            "Exempt, as this tender is reserved for micro and small enterprises.",
            "7. Payment terms",
            "30% advance against a bank guarantee of equal value; 60% on delivery; balance 10% after "
            "installation and acceptance.",
            "8. Delivery",
            "Delivery and installation within 45 days of the work order.",
            *COMMON_TERMS,
        ],
    },
    "classroom_furniture.pdf": {
        "title": "Supply of 80 classroom benches and 10 teacher tables",
        "lines": [
            "KUTTANAD BLOCK PANCHAYAT (fictional)",
            "Notice Inviting Tender No. KBP/EDU/2026/31",
            "1. Scope of work",
            "Supply of 80 two-seater wooden classroom benches and 10 teacher tables for anganwadis and lower "
            "primary schools in Kuttanad block. Estimated value of the order: Rs. 9 lakh.",
            "2. Specification",
            "Benches and tables shall be of Godrej make or equivalent. Only products of the brand named above "
            "will be considered.",
            "3. Important dates",
            "Tender published on 8 October 2026. Last date and time for bid submission: 20 October 2026, 1:00 PM.",
            "4. Eligibility criteria",
            "4.1 Average annual turnover of the bidder in the last three financial years shall be at least "
            "Rs. 2 crore. Mandatory.",
            "4.2 The bidder shall have at least five years of experience supplying furniture to Central "
            "Government departments. Mandatory. Experience with State Government, local bodies or private "
            "buyers will not be counted.",
            "4.3 The bidder shall hold a valid GST registration. Mandatory.",
            "5. Documents to be submitted",
            "GST registration certificate; PAN card; audited balance sheets for three years; work orders from "
            "Central Government departments for each of the last five years.",
            "6. Earnest money deposit (EMD) and tender fee",
            "EMD of Rs. 1,00,000 by demand draft. No bidder is exempt from EMD. A non-refundable tender fee of "
            "Rs. 5,000 is payable by all bidders.",
            "7. Payment terms",
            "Payment after the full quantity is delivered and accepted, subject to availability of funds.",
            "8. Delivery",
            "Delivery within 20 days of the supply order.",
            *COMMON_TERMS,
        ],
    },
    "steel_almirahs.pdf": {
        "title": "Supply of 120 steel almirahs",
        "lines": [
            "MALABAR WATER AUTHORITY (fictional)",
            "Notice Inviting Tender No. MWA/STR/2026/05",
            "1. Scope of work",
            "Supply of 120 full-height steel almirahs with four shelves and a locker for the authority's "
            "field stations.",
            "2. Specification",
            "Cold-rolled steel sheet of 0.8 mm, powder coated, 1980 mm x 915 mm x 480 mm, with a three-way "
            "locking handle.",
            "3. Important dates",
            "Last date and time for bid submission: 18 November 2026, 3:00 PM.",
            "4. Eligibility criteria",
            "4.1 Average annual turnover of the bidder in the last three financial years shall be at least "
            "Rs. 40 lakh. Mandatory.",
            "4.2 The bidder shall have supplied steel almirahs or steel cupboards worth at least Rs. 5 lakh "
            "in one order in the last three years. Mandatory.",
            "4.3 The bidder shall hold a valid GST registration. Mandatory.",
            "5. Documents to be submitted",
            "GST registration certificate; PAN card; Udyam registration certificate (for MSE benefits); audited "
            "balance sheets for three years; purchase order of a similar supply.",
            "6. Earnest money deposit (EMD)",
            "EMD of Rs. 30,000. Micro and small enterprises registered under Udyam are exempt from EMD.",
            "7. Payment terms",
            "100% payment within 30 days of delivery and acceptance.",
            "8. Delivery",
            "Delivery within 45 days of the supply order.",
            *COMMON_TERMS,
        ],
    },
}

def _corrigendum(lines):
    """The school desks tender after a corrigendum: deadline extended, EMD raised, one new rule."""
    out = []
    for line in lines:
        line = line.replace("30 October 2026, 3:00 PM", "6 November 2026, 3:00 PM")
        line = line.replace("31 October 2026", "7 November 2026")
        line = line.replace("EMD of Rs. 50,000", "EMD of Rs. 75,000")
        out.append(line)
        if line.startswith("4.4 "):
            out.append("4.5 The bidder shall have a manufacturing unit registered in Kerala. Mandatory. "
                       "(Added by Corrigendum No. 1.)")
    out.insert(1, "CORRIGENDUM No. 1 - supersedes the earlier version of this tender.")
    return out


CORRIGENDA = {"school_desks_corrigendum.pdf": lambda: _corrigendum(TENDERS["school_desks.pdf"]["lines"])}

PAGE_W, PAGE_H, MARGIN, LINE_H, WRAP = 595, 842, 56, 15, 92


def wrap(lines):
    out = []
    for line in lines:
        out += textwrap.wrap(line, WRAP) or [""]
        out.append("")
    return out


def write_pdf(path, lines):
    doc = pymupdf.open()
    per_page = int((PAGE_H - 2 * MARGIN) / LINE_H) - 2
    body = wrap(lines)
    # Short pages on purpose so clauses run across page breaks, as in real tenders.
    per_page = min(per_page, 34)
    for start in range(0, len(body), per_page):
        page = doc.new_page(width=PAGE_W, height=PAGE_H)
        page.insert_text((MARGIN, MARGIN - 20), BANNER, fontsize=8, color=(0.6, 0, 0))
        y = MARGIN
        for text in body[start:start + per_page]:
            page.insert_text((MARGIN, y), text, fontsize=10)
            y += LINE_H
        page.insert_text((PAGE_W / 2 - 20, PAGE_H - 30), f"Page {page.number + 1}", fontsize=8)
    doc.save(path)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, tender in TENDERS.items():
        write_pdf(OUT / name, tender["lines"])
        print("wrote", OUT / name)
    (OUT / "corrigenda").mkdir(exist_ok=True)
    for name, lines in CORRIGENDA.items():
        write_pdf(OUT / "corrigenda" / name, lines())
        print("wrote", OUT / "corrigenda" / name)
    titles = {name: t["title"] for name, t in TENDERS.items()}
    (OUT / "titles.json").write_text(json.dumps(titles, indent=2) + "\n")


if __name__ == "__main__":
    main()
