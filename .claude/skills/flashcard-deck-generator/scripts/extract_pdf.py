#!/usr/bin/env python3
"""Extract PDF text per page; render scanned (textless) pages to images.

Part of the flashcard-deck-generator skill. Uses pypdf when installed, else
poppler's pdftotext; pages with (almost) no text layer are rendered with
pdftoppm so Claude can Read the page images natively.
Exit codes: 0 ok | 1 unexpected error | 2 bad input | 3 missing dependency.
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile

EXTRA_PATHS = ("/opt/homebrew/bin", "/usr/local/bin")
SCANNED_THRESHOLD = 40  # stripped chars below this → treat page as scanned


def fail(msg, code=2):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def find_tool(name):
    path = shutil.which(name)
    if path:
        return path
    for d in EXTRA_PATHS:
        candidate = os.path.join(d, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def pages_via_pypdf(pdf_path):
    import pypdf

    try:
        reader = pypdf.PdfReader(pdf_path)
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                fail("PDF is password-protected")
        out = []
        for page in reader.pages:
            try:
                out.append(page.extract_text() or "")
            except Exception:
                out.append("")
        return out
    except Exception as e:
        fail(f"could not read PDF: {e}")


def pages_via_pdftotext(pdf_path, tool):
    try:
        proc = subprocess.run(
            [tool, "-layout", "-enc", "UTF-8", pdf_path, "-"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        fail("pdftotext timed out")
    if proc.returncode != 0:
        fail(f"pdftotext failed: {proc.stderr.strip() or 'unknown error'}")
    pages = proc.stdout.split("\f")
    if pages and pages[-1] == "":
        pages.pop()
    return pages


def parse_pages(spec, total):
    if not spec:
        return 1, total
    m = spec.split("-")
    try:
        if len(m) == 1:
            a = b = int(m[0])
        elif len(m) == 2:
            a, b = int(m[0]), int(m[1])
        else:
            raise ValueError
    except ValueError:
        fail(f"--pages must be N or A-B, got '{spec}'")
    if a < 1 or b < a:
        fail(f"--pages range '{spec}' is not valid")
    if a > total:
        fail(f"--pages {spec}: the PDF has only {total} page(s)")
    return a, min(b, total)


def render_page(pdf_path, page_no, images_dir, dpi):
    tool = find_tool("pdftoppm")
    if not tool:
        return None
    prefix = os.path.join(images_dir, f"page-{page_no}")
    proc = subprocess.run(
        [
            tool,
            "-jpeg",
            "-r",
            str(dpi),
            "-f",
            str(page_no),
            "-l",
            str(page_no),
            pdf_path,
            prefix,
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        return None
    matches = sorted(glob.glob(f"{prefix}-*.jpg")) or sorted(
        glob.glob(f"{prefix}*.jpg")
    )
    return matches[0] if matches else None


def main():
    ap = argparse.ArgumentParser(
        description="PDF -> per-page text on stdout; scanned pages -> jpg images"
    )
    ap.add_argument("pdf", help="path to the PDF")
    ap.add_argument("--pages", help="page or range to extract, e.g. 3 or 2-5 (1-based)")
    ap.add_argument(
        "--images-dir",
        help="where to write scanned-page images (default: a fresh temp dir)",
    )
    ap.add_argument("--dpi", type=int, default=150, help="render DPI (default 150)")
    args = ap.parse_args()

    if not os.path.isfile(args.pdf):
        fail(f"no such file: {args.pdf}")

    try:
        import pypdf  # noqa: F401

        backend = "pypdf"
    except ImportError:
        backend = None
    if backend is None:
        tool = find_tool("pdftotext")
        if tool:
            backend = ("pdftotext", tool)
        else:
            print("error: no PDF text extractor available.", file=sys.stderr)
            print("install one of:", file=sys.stderr)
            print("  python3 -m pip install pypdf", file=sys.stderr)
            print("  brew install poppler", file=sys.stderr)
            sys.exit(3)

    if backend == "pypdf":
        pages = pages_via_pypdf(args.pdf)
    else:
        pages = pages_via_pdftotext(args.pdf, backend[1])
    if not pages:
        fail("PDF has no pages")

    first, last = parse_pages(args.pages, len(pages))

    scanned = []
    for n in range(first, last + 1):
        text = pages[n - 1]
        print(f"=== PAGE {n} ===")
        print(text.rstrip())
        if len(text.strip()) < SCANNED_THRESHOLD:
            scanned.append(n)

    if scanned:
        images_dir = args.images_dir or tempfile.mkdtemp(prefix="flashcard-pdf-")
        os.makedirs(images_dir, exist_ok=True)
        print()
        missing_tool = find_tool("pdftoppm") is None
        if missing_tool:
            print(
                f"pages with no text layer (likely scanned): {scanned} — "
                "cannot render images (pdftoppm missing).",
            )
            print("install: brew install poppler", file=sys.stderr)
        else:
            for n in scanned:
                img = render_page(args.pdf, n, images_dir, args.dpi)
                if img:
                    print(f"SCANNED PAGE {n} — Read this image: {os.path.abspath(img)}")
                else:
                    print(f"SCANNED PAGE {n} — rendering failed; view the PDF directly")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:  # never a traceback
        print(f"error: unexpected: {e}", file=sys.stderr)
        sys.exit(1)
