#!/usr/bin/env python3
"""
Leerdoel Extractor - Extract learning objectives from PDFs

Usage:
    ./extract.py input.pdf
    ./extract.py input.pdf --output-dir custom/path
    ./extract.py input.pdf --domain STAT
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime
import fitz  # PyMuPDF
from tqdm import tqdm

# Add core to path
sys.path.insert(0, str(Path(__file__).parent))

from core.llm import get_llm


def chunk_text(text: str, max_len: int = 800) -> list[str]:
    """Split text into chunks of approximately max_len characters."""
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0

    for word in words:
        word_length = len(word) + 1  # +1 for space
        if current_length + word_length > max_len and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_length = 0
        current_chunk.append(word)
        current_length += word_length

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from PDF."""
    doc = fitz.open(pdf_path)
    all_text = []

    print(f"📄 Lezen van PDF: {pdf_path}")
    for page_num in tqdm(range(len(doc)), desc="Pagina's verwerken"):
        page = doc[page_num]
        text = page.get_text("text").strip()
        if text:
            all_text.append(text)

    doc.close()
    return "\n\n".join(all_text)


def extract_learning_objectives(text: str, domain: str = None) -> list[dict]:
    """Extract learning objectives from text using LLM."""
    print("\n🤖 Leerdoelen extraheren met LLM...")

    # Split into chunks to handle large documents
    chunks = chunk_text(text, max_len=3000)
    print(f"   Tekst opgesplitst in {len(chunks)} chunks")

    llm = get_llm()
    all_objectives = []

    for i, chunk in enumerate(chunks[:5], 1):  # Process first 5 chunks max
        print(f"   Chunk {i}/{min(len(chunks), 5)} verwerken...")
        try:
            objectives = llm.extract_learning_objectives(chunk)

            # Handle both dict and list responses
            if isinstance(objectives, dict):
                if "error" in objectives:
                    print(f"   ⚠️  Error in chunk {i}: {objectives['error']}")
                    continue
                # If dict but not error, try to extract array
                if isinstance(objectives.get("learning_objectives"), list):
                    objectives = objectives["learning_objectives"]
                else:
                    print(f"   ⚠️  Unexpected response format in chunk {i}")
                    continue

            if isinstance(objectives, list):
                # Add domain if specified
                if domain:
                    for obj in objectives:
                        obj["domain"] = domain
                all_objectives.extend(objectives)
                print(f"   ✅ {len(objectives)} leerdoelen gevonden")
        except Exception as e:
            print(f"   ❌ Error in chunk {i}: {e}")
            continue

    return all_objectives


def save_as_json(objectives: list[dict], output_path: Path):
    """Save learning objectives as JSON."""
    data = {
        "generated_at": datetime.now().isoformat(),
        "count": len(objectives),
        "learning_objectives": objectives
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ JSON opgeslagen: {output_path}")


def save_as_markdown(objectives: list[dict], output_path: Path, source_file: str):
    """Save learning objectives as Markdown with YAML frontmatter."""
    md_lines = ["---"]
    md_lines.append(f"generated_at: {datetime.now().isoformat()}")
    md_lines.append(f"source: {source_file}")
    md_lines.append(f"count: {len(objectives)}")

    # Extract domains
    domains = set(obj.get("domain", "GENERAL") for obj in objectives)
    if domains:
        md_lines.append(f"domains: {', '.join(sorted(domains))}")

    md_lines.append("---")
    md_lines.append("")
    md_lines.append(f"# Leerdoelen: {Path(source_file).stem}")
    md_lines.append("")
    md_lines.append(f"*Gegenereerd op {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    md_lines.append("")
    md_lines.append(f"**Bron:** `{source_file}`")
    md_lines.append(f"**Aantal leerdoelen:** {len(objectives)}")
    md_lines.append("")

    # Group by domain
    by_domain = {}
    for obj in objectives:
        domain = obj.get("domain", "ALGEMEEN")
        if domain not in by_domain:
            by_domain[domain] = []
        by_domain[domain].append(obj)

    # Write objectives grouped by domain
    for domain in sorted(by_domain.keys()):
        md_lines.append(f"## {domain}")
        md_lines.append("")

        for i, obj in enumerate(by_domain[domain], 1):
            concept = obj.get("concept", "Onbekend concept")
            bloom = obj.get("bloom", "understand")
            summary = obj.get("summary", "Geen samenvatting beschikbaar")

            md_lines.append(f"### {i}. {concept}")
            md_lines.append(f"**Bloom niveau:** {bloom}")
            md_lines.append(f"**Samenvatting:** {summary}")
            md_lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"✅ Markdown opgeslagen: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Extraheer leerdoelen uit PDF bestanden",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Voorbeelden:
  ./extract.py statistiek_hoofdstuk3.pdf
  ./extract.py boek.pdf --output-dir learning-objectives/statistics
  ./extract.py artikel.pdf --domain STAT
        """
    )

    parser.add_argument("pdf_file", help="PDF bestand om te verwerken")
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory voor gegenereerde bestanden (default: output)"
    )
    parser.add_argument(
        "--domain",
        help="Domein/vak voor de leerdoelen (bijv. STAT, FIN, PHYS)"
    )

    args = parser.parse_args()

    # Check if PDF exists
    if not os.path.exists(args.pdf_file):
        print(f"❌ Bestand niet gevonden: {args.pdf_file}")
        sys.exit(1)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract filename without extension
    pdf_name = Path(args.pdf_file).stem

    print("=" * 60)
    print("🎓 Leerdoel Extractor")
    print("=" * 60)
    print(f"Input:  {args.pdf_file}")
    print(f"Output: {output_dir}/")
    if args.domain:
        print(f"Domein: {args.domain}")
    print("=" * 60)
    print()

    # Step 1: Extract text from PDF
    text = extract_text_from_pdf(args.pdf_file)

    if not text.strip():
        print("❌ Geen tekst gevonden in PDF")
        sys.exit(1)

    print(f"✅ {len(text)} karakters geëxtraheerd")

    # Step 2: Extract learning objectives
    objectives = extract_learning_objectives(text, args.domain)

    if not objectives:
        print("❌ Geen leerdoelen kunnen extraheren")
        sys.exit(1)

    print(f"\n✅ Totaal {len(objectives)} leerdoelen geëxtraheerd")

    # Step 3: Save as JSON
    json_path = output_dir / f"{pdf_name}_leerdoelen.json"
    save_as_json(objectives, json_path)

    # Step 4: Save as Markdown
    md_path = output_dir / f"{pdf_name}_leerdoelen.md"
    save_as_markdown(objectives, md_path, args.pdf_file)

    print("\n" + "=" * 60)
    print("🎉 Klaar!")
    print("=" * 60)
    print(f"\nBestanden aangemaakt:")
    print(f"  📄 {json_path}")
    print(f"  📄 {md_path}")
    print(f"\nJe kunt deze nu importeren in jomuni!")


if __name__ == "__main__":
    main()
